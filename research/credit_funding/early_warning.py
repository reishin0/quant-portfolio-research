"""Offline evaluation for the declared study early_warning_20261018.

Compares price-only, broad-credit, issuer-credit and funding signals as advance warnings of
nonoverlapping equity stress episodes, on identical eligible issuer-sessions. Everything here is
retrospective research; nothing connects to allocations, the paper journal or trading.
"""
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from research.credit_funding.issuer_replay import inside, bond_diagnostics, issuer_timeline
from research.credit_funding.issuer_comparison import prepare_bonds

PROTOCOL_PATH = 'research/credit_funding/early_warning_protocol_20261018.json'
DATA_DIR = 'data/early_warning_20261018'
TENORS = {'DGS1': 1, 'DGS2': 2, 'DGS3': 3, 'DGS5': 5, 'DGS7': 7, 'DGS10': 10, 'DGS20': 20, 'DGS30': 30}
WARN = 'YIELD_WARNING_DIAGNOSTIC'
NY = ZoneInfo('America/New_York')
SIGNALS = ['P1', 'P2', 'B1', 'B2', 'I0', 'I1', 'I2', 'F1', 'F2', 'E1', 'E2']


# ---------------------------------------------------------------- loading and integrity

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root, expected_manifest_sha=None):
    root = Path(root)
    data = inside(root, DATA_DIR)
    raw = (data / 'manifest.json').read_bytes()
    if expected_manifest_sha and hashlib.sha256(raw).hexdigest() != expected_manifest_sha:
        raise ValueError('Early-warning manifest changed')
    manifest = json.loads(raw)
    if manifest['protocol_sha256'] != sha(inside(root, PROTOCOL_PATH)):
        raise ValueError('Protocol changed after the evidence was pinned')
    for name, digest in manifest['file_sha256'].items():
        if sha(inside(data, name)) != digest:
            raise ValueError('Evidence changed: ' + name)
    for name, digest in manifest.get('local_raw_sha256', {}).items():
        if inside(data, name).exists() and sha(inside(data, name)) != digest:
            raise ValueError('Local raw evidence changed: ' + name)
    protocol = json.loads(inside(root, PROTOCOL_PATH).read_text(encoding='utf-8'))
    selection = json.loads((data / 'selection.json').read_text(encoding='utf-8'))
    if selection['protocol_sha256'] != manifest['protocol_sha256']:
        raise ValueError('Selection was made under a different protocol')
    if set(selection['selection']) != set(protocol['universe']['candidates']):
        raise ValueError('Selection must keep the declared universe')
    quality = json.loads((data / 'equity_quality.json').read_text(encoding='utf-8'))
    prices = pd.read_csv(data / 'equity_adjusted.csv', index_col=0, parse_dates=True).sort_index()
    excluded = set(quality['excluded_equity'])
    prices = prices[[c for c in prices if c not in excluded]]
    fred = {s: pd.read_csv(data / 'raw' / f'fred_{s}.csv', index_col=0, parse_dates=True).iloc[:, 0]
            .pipe(pd.to_numeric, errors='coerce') for s in list(TENORS) + ['BAMLH0A0HYM2', 'BAA10Y']}
    bonds, meta = {}, {}
    for symbol, choice in selection['selection'].items():
        m = pd.DataFrame(json.loads((data / f'{symbol}_instruments.json').read_text(encoding='utf-8')))
        meta[symbol] = m.loc[m.cusip.isin(choice['bonds'])] if len(m) else m
        path = data / f'{symbol}_bonds.csv'
        if choice['status'] == 'ELIGIBLE_ISSUER_CREDIT' and path.exists():
            bonds[symbol] = pd.read_csv(path, dtype={'cusip': str})
    filings = None
    if (data / 'filings.json').exists():
        filings = pd.DataFrame(json.loads((data / 'filings.json').read_text(encoding='utf-8'))['records'])
    return dict(protocol=protocol, selection=selection['selection'], manifest=manifest, quality=quality,
                prices=prices, fred=fred, bonds=bonds, meta=meta, filings=filings)


def sessions_for(prices, symbol):
    """Observed sessions for one symbol; missing whole sessions are never filled."""
    s = prices[symbol].dropna()
    if (s <= 0).any() or not np.isfinite(s).all():
        raise ValueError('Invalid equity price: ' + symbol)
    return s


# ---------------------------------------------------------------- spreads and states

def treasury_curve(fred):
    return pd.concat({TENORS[k]: fred[k] for k in TENORS}, axis=1).sort_index()


def gspread_panel(bonds, meta, curve):
    """G-spread in percent: last-sale yield minus CMT yield interpolated at remaining maturity.

    Missing curve dates, missing yields or maturities outside 1-30 years give NaN (unknown).
    """
    frame, _ = prepare_bonds(bonds)
    frame['tradeDate'] = pd.to_datetime(frame.tradeDate)
    maturity = meta.set_index('cusip').maturityDate.map(pd.Timestamp)
    years = (frame.cusip.map(maturity) - frame.tradeDate).dt.days / 365.25
    tenors = np.array(list(curve.columns), dtype=float)
    out = np.full(len(frame), np.nan)
    rows = curve.reindex(frame.tradeDate)
    for i, (y, row) in enumerate(zip(years.to_numpy(), rows.to_numpy())):
        if np.isfinite(y) and tenors[0] <= y <= tenors[-1] and np.isfinite(row).all():
            out[i] = np.interp(y, tenors, row)
    g = frame.copy()
    g['treasury_pct'] = out
    g['lastSaleYield'] = frame.lastSaleYield - out
    g.loc[~np.isfinite(out), ['lastSaleYield']] = np.nan
    return frame, g


def issuer_states(frame, symbol, choice, sessions, rules):
    """Run the frozen per-bond diagnostic and same-day quorum on trade dates."""
    spec = dict(rules, issuer=symbol, bonds=choice['bonds'],
                bond_window=[str(frame.tradeDate.min().date()), str(frame.tradeDate.max().date())])
    f = frame.loc[frame.cusip.isin(choice['bonds']), ['cusip', 'tradeDate', 'lastSalePrice', 'lastSaleYield']].copy()
    f['tradeDate'] = f.tradeDate.dt.strftime('%Y-%m-%d')
    diag = bond_diagnostics(f, spec)
    timeline = issuer_timeline(diag, sessions, spec)
    return diag, timeline


def series_state(series, history=20, persistence=3, widening_bp=100, max_gap_days=4, scale=100):
    """Same rule as the bond diagnostic for a single index series (values in percent)."""
    s = series.dropna().sort_index()
    state = pd.Series('UNKNOWN', index=s.index)
    widen = pd.Series(np.nan, index=s.index)
    vals, dates = s.to_numpy(), s.index
    n = history + persistence
    for i in range(n - 1, len(s)):
        window_dates = dates[i + 1 - n:i + 1]
        if (np.diff(window_dates.values).astype('timedelta64[D]').astype(int) > max_gap_days).any():
            continue
        base = np.median(vals[i + 1 - n:i + 1 - persistence])
        w = (vals[i + 1 - persistence:i + 1] - base) * scale
        widen.iloc[i] = w.min()
        state.iloc[i] = WARN if (w >= widening_bp).all() else 'NO_FLAG'
    return state, widen


def published_next_session(state, sessions, max_age_days=4):
    """Map an end-of-day observation on date t to the first session strictly after t."""
    s = state.sort_index()
    pos = s.index.searchsorted(sessions, side='left') - 1
    out = pd.Series('UNKNOWN', index=sessions)
    ok = pos >= 0
    obs = pd.DatetimeIndex(s.index[np.clip(pos, 0, None)])
    fresh = ok & ((sessions - obs).days <= max_age_days)
    out[fresh] = s.to_numpy()[np.clip(pos, 0, None)][fresh]
    return out


# ---------------------------------------------------------------- funding states

def funding_states(filings, symbol, sessions, max_age_days=200):
    """Latest filing state known by each session close; stale or absent filings are UNKNOWN."""
    out = pd.DataFrame(index=sessions, data=dict(F1='UNKNOWN', F2='UNKNOWN', F1_alarm=False, F2_alarm=False))
    if filings is None or filings.empty:
        return out
    f = filings.loc[filings.issuer.eq(symbol)].copy()
    if f.empty:
        return out
    f['alarm_session'] = pd.to_datetime(f.alarm_session)
    f = f.sort_values(['alarm_session', 'period_end'])
    for _, r in f.iterrows():
        live = (sessions >= r.alarm_session) & ((sessions - r.alarm_session).days <= max_age_days)
        out.loc[live, 'F1'] = r.F1
        out.loc[live, 'F2'] = r.F2
        if r.alarm_session in out.index:
            out.loc[r.alarm_session, 'F1_alarm'] |= r.F1 == 'FUNDING_WATCH'
            out.loc[r.alarm_session, 'F2_alarm'] |= r.F2 == 'FUNDING_GAP'
    return out


# ---------------------------------------------------------------- targets and price signals

def episodes(close, lookback=60, threshold=0.20, recover=0.90, max_len=60):
    """Nonoverlapping drawdown episodes: (onset, end, reference peak)."""
    peak = close.rolling(lookback, min_periods=lookback).max()
    rows, i, values = [], 0, close.to_numpy()
    dates, peaks = close.index, peak.to_numpy()
    while i < len(close):
        if np.isfinite(peaks[i]) and values[i] <= (1 - threshold) * peaks[i]:
            ref, end = peaks[i], min(i + max_len, len(close) - 1)
            for j in range(i + 1, min(i + max_len, len(close) - 1) + 1):
                if values[j] >= recover * ref:
                    end = j
                    break
            rows.append(dict(onset=dates[i], end=dates[end], peak=ref, onset_pos=i, end_pos=end))
            i = end + 1
        else:
            i += 1
    return pd.DataFrame(rows, columns=['onset', 'end', 'peak', 'onset_pos', 'end_pos'])


def price_signals(close, lookback=60):
    ret = close.pct_change(fill_method=None)
    p1 = ret.le(-0.05)
    dd = close / close.rolling(lookback, min_periods=lookback).max() - 1
    p2 = pd.Series(False, index=close.index)
    armed = True
    for d, v in dd.items():
        if not np.isfinite(v):
            continue
        if armed and v <= -0.10:
            p2[d], armed = True, False
        elif v > -0.05:
            armed = True
    known = dd.notna()
    return p1 & known, p2, known


# ---------------------------------------------------------------- evaluation

def dedup(alarm, cooldown=20):
    """Alarm onsets: first alarm after >= cooldown sessions without one (positions in index)."""
    pos = np.flatnonzero(np.asarray(alarm, dtype=bool))
    keep, last = [], -10 ** 9
    for p in pos:
        if p - last > cooldown:
            keep.append(p)
        last = p
    return keep


def persistence(alarm):
    runs, n = [], 0
    for v in alarm.to_numpy():
        if v:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    if n:
        runs.append(n)
    return float(np.mean(runs)) if runs else np.nan


def classify(onset_positions, eps, sample, horizon=20):
    """Each alarm onset: SAME_DAY, IN_EPISODE, HIT, FALSE or CENSORED."""
    sample = np.asarray(sample, dtype=bool)
    n = len(sample)
    starts = eps.onset_pos.to_numpy() if len(eps) else np.array([], int)
    ends = eps.end_pos.to_numpy() if len(eps) else np.array([], int)
    out = []
    for p in onset_positions:
        if not sample[p]:
            continue
        if (starts == p).any():
            out.append((p, 'SAME_DAY', 0))
        elif ((starts < p) & (ends >= p)).any():
            out.append((p, 'IN_EPISODE', np.nan))
        else:
            ahead = starts[(starts > p) & (starts <= p + horizon)]
            if len(ahead):
                out.append((p, 'HIT', int(ahead[0] - p)))
            elif p + horizon >= n:
                out.append((p, 'CENSORED', np.nan))
            else:
                out.append((p, 'FALSE', np.nan))
    return out


def recall(alarm, eps, sample, horizon=20):
    rows = []
    for e in eps.itertuples():
        o = e.onset_pos
        if o - horizon < 0 or not sample.iloc[o - horizon:o].all():
            continue
        window = np.flatnonzero(alarm.iloc[o - horizon:o].to_numpy())
        rows.append(dict(onset=e.onset, warned=bool(len(window)),
                         lead=int(horizon - window[0]) if len(window) else np.nan))
    return rows


def evaluate(panel, signal, mask_col, period, horizon=20, cooldown=20):
    """Aggregate one signal over issuers on the rows where mask_col is True and in period."""
    lo, hi = map(pd.Timestamp, period)
    alarms, eps_rows, sessions = [], [], 0
    persist = []
    for symbol, g in panel.items():
        sample = g[mask_col] & (g.index >= lo) & (g.index <= hi)
        sessions += int(sample.sum())
        alarm = g[signal + '_alarm'] & g[mask_col]
        persist.append(persistence(g[signal + '_state'] & g[mask_col]) if signal + '_state' in g else np.nan)
        for p, kind, lead in classify(dedup(alarm, cooldown), g.attrs['episodes'], sample, horizon):
            alarms.append(dict(issuer=symbol, date=g.index[p], kind=kind, lead=lead))
        for r in recall(alarm, g.attrs['episodes'], sample, horizon):
            if lo <= r['onset'] <= hi:
                eps_rows.append(dict(issuer=symbol, **r))
    a = pd.DataFrame(alarms, columns=['issuer', 'date', 'kind', 'lead'])
    e = pd.DataFrame(eps_rows, columns=['issuer', 'onset', 'warned', 'lead'])
    hits, false = int(a.kind.eq('HIT').sum()), int(a.kind.eq('FALSE').sum())
    return dict(signal=signal, sample=mask_col, issuer_sessions=sessions, alarm_onsets=len(a), hits=hits,
                false_alarms=false, same_day=int(a.kind.eq('SAME_DAY').sum()),
                in_episode=int(a.kind.eq('IN_EPISODE').sum()), censored=int(a.kind.eq('CENSORED').sum()),
                precision_pct=100 * hits / (hits + false) if hits + false else np.nan,
                episodes=len(e), warned=int(e.warned.sum()) if len(e) else 0,
                recall_pct=100 * e.warned.mean() if len(e) else np.nan,
                median_lead_sessions=float(e.lead.median()) if e.warned.any() else np.nan,
                false_per_250=250 * false / sessions if sessions else np.nan,
                persistence_sessions=float(np.nanmean(persist)) if np.isfinite(persist).any() else np.nan), a, e


def base_rate(panel, mask_col, period, horizon=20):
    lo, hi = map(pd.Timestamp, period)
    yes = tot = 0
    for g in panel.values():
        eps = g.attrs['episodes']
        starts = eps.onset_pos.to_numpy() if len(eps) else np.array([], int)
        ends = eps.end_pos.to_numpy() if len(eps) else np.array([], int)
        sample = (g[mask_col] & (g.index >= lo) & (g.index <= hi)).to_numpy()
        for p in np.flatnonzero(sample):
            if p + horizon >= len(g) or ((starts <= p) & (ends >= p)).any():
                continue
            tot += 1
            yes += bool(((starts > p) & (starts <= p + horizon)).any())
    return 100 * yes / tot if tot else np.nan, tot


def permutation_p(panel, signal, mask_col, period, draws=2000, seed=20261018, horizon=20, cooldown=20):
    """Circular shift of each issuer's alarm series within its eligible sessions."""
    rng = np.random.default_rng(seed)
    lo, hi = map(pd.Timestamp, period)
    prepared = []
    for g in panel.values():
        sample = (g[mask_col] & (g.index >= lo) & (g.index <= hi)).to_numpy()
        idx = np.flatnonzero(sample)
        if len(idx) < 2 * 40 + 1:
            continue
        alarm = (g[signal + '_alarm'] & g[mask_col]).to_numpy()[idx]
        prepared.append((g, idx, alarm))
    if not prepared:
        return np.nan, np.nan

    samples = []
    for g, idx, _ in prepared:
        sample = np.zeros(len(g), bool)
        sample[idx] = True
        samples.append(sample)

    def precision(shifts):
        h = f = 0
        for (g, idx, alarm), sample, k in zip(prepared, samples, shifts):
            full = np.zeros(len(g), bool)
            full[idx] = np.roll(alarm, k)
            for _, kind, _ in classify(dedup(full, cooldown), g.attrs['episodes'], sample, horizon):
                h += kind == 'HIT'
                f += kind == 'FALSE'
        return h / (h + f) if h + f else np.nan

    observed = precision([0] * len(prepared))
    null = np.array([precision([rng.integers(40, len(idx) - 40) for _, idx, _ in prepared]) for _ in range(draws)])
    null = null[np.isfinite(null)]
    if not np.isfinite(observed) or not len(null):
        return observed, np.nan
    return observed, float((1 + (null >= observed).sum()) / (1 + len(null)))


def bootstrap_difference(alarms_a, alarms_b, issuers, draws=2000, seed=20261018):
    """Issuer-cluster bootstrap of precision(a) - precision(b), percentage points; 90% interval."""
    rng = np.random.default_rng(seed)
    def counts(a):
        k = a.loc[a.kind.isin(['HIT', 'FALSE'])]
        return k.groupby('issuer').kind.apply(lambda s: (s.eq('HIT').sum(), len(s)))
    ca, cb = counts(alarms_a), counts(alarms_b)
    issuers = list(issuers)
    diffs = []
    for _ in range(draws):
        pick = rng.choice(issuers, len(issuers), replace=True)
        ha = sum(ca.get(i, (0, 0))[0] for i in pick); na = sum(ca.get(i, (0, 0))[1] for i in pick)
        hb = sum(cb.get(i, (0, 0))[0] for i in pick); nb = sum(cb.get(i, (0, 0))[1] for i in pick)
        if na and nb:
            diffs.append(100 * (ha / na - hb / nb))
    if not diffs:
        return np.nan, np.nan, 0
    return float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95)), len(diffs)


# ---------------------------------------------------------------- panel construction

def build_panel(inputs):
    p = inputs['protocol']
    rules = dict(history=20, persistence=3, widening_bp=100, max_gap_calendar_days=4, min_warning_bonds=2)
    curve = treasury_curve(inputs['fred'])
    hy_state, hy_widen = series_state(inputs['fred']['BAMLH0A0HYM2'], widening_bp=100)
    baa_state, _ = series_state(inputs['fred']['BAA10Y'], widening_bp=50)
    spy = inputs['prices']['SPY'].dropna()
    panel, coverage, diagnostics = {}, [], {}
    for symbol, choice in inputs['selection'].items():
        if symbol not in inputs['prices']:
            coverage.append(dict(issuer=symbol, status='EXCLUDED_EQUITY', sessions=0))
            continue
        close = sessions_for(inputs['prices'], symbol)
        idx = close.index
        g = pd.DataFrame(index=idx)
        p1, p2, pknown = price_signals(close)
        g['P1_alarm'], g['P2_alarm'], g['price_known'] = p1, p2, pknown
        g['B1'] = published_next_session(hy_state, idx).to_numpy()
        g['B2'] = published_next_session(baa_state, idx).to_numpy()
        g['B1_state'] = g.B1.eq(WARN)
        g['B2_state'] = g.B2.eq(WARN)
        g['B1_alarm'], g['B2_alarm'] = g.B1_state, g.B2_state
        g['b1_known'] = g.B1.ne('UNKNOWN')
        for s in ['I0', 'I1', 'I2']:
            g[s + '_state'] = False
        g['i_known'] = False
        g['i0_known'] = False
        status = choice['status']
        if status == 'ELIGIBLE_ISSUER_CREDIT' and symbol in inputs['bonds']:
            raw, gs = gspread_panel(inputs['bonds'][symbol], inputs['meta'][symbol], curve)
            d0, t0 = issuer_states(raw, symbol, choice, idx, rules)
            d1, t1 = issuer_states(gs, symbol, choice, idx, rules)
            diagnostics[symbol] = (d0, d1)
            # TRACE end-of-day for trade date t is usable at session t+1.
            g['I0_state'] = t0.state.eq(WARN).shift(1, fill_value=False).to_numpy()
            g['i0_known'] = t0.state.ne('UNKNOWN').shift(1, fill_value=False).to_numpy()
            g['I1_state'] = t1.state.eq(WARN).shift(1, fill_value=False).to_numpy()
            g['i_known'] = t1.state.ne('UNKNOWN').shift(1, fill_value=False).to_numpy()
            hyw = hy_widen.reindex(idx)
            med = d1.loc[d1.state.ne('UNKNOWN')].groupby('date').minimum_widening_bp.median().reindex(idx)
            excess = (med - hyw) >= 50
            g['I2_state'] = (t1.state.eq(WARN).to_numpy() & excess.to_numpy())
            g['I2_state'] = g.I2_state.shift(1, fill_value=False)
        for s in ['I0', 'I1', 'I2']:
            g[s + '_alarm'] = g[s + '_state']
        fs = funding_states(inputs['filings'], symbol, idx)
        g['F1_alarm'], g['F2_alarm'] = fs.F1_alarm.to_numpy(), fs.F2_alarm.to_numpy()
        g['f_known'] = fs.F1.ne('UNKNOWN').to_numpy()
        g['F2_active'] = fs.F2.eq('FUNDING_GAP').to_numpy()
        g['E1_alarm'] = g.P2_alarm | g.I1_alarm
        recent_i1 = g.I1_state.astype(int).rolling(20, min_periods=1).max().shift(1, fill_value=0).astype(bool)
        g['E2_alarm'] = g.P2_alarm & (recent_i1 | g.F2_active)
        g['common'] = g.price_known & g.b1_known & g.i_known & g.f_known
        g['common_no_funding'] = g.price_known & g.b1_known & g.i_known
        g['own_price'] = g.price_known
        g['own_issuer'] = g.price_known & g.i_known
        g['own_funding'] = g.price_known & g.f_known
        g['own_broad'] = g.price_known & g.b1_known
        g.attrs['episodes'] = episodes(close)
        rel = (close / spy.reindex(idx)).dropna()
        g.attrs['episodes_relative'] = episodes(rel) if len(rel) == len(idx) else pd.DataFrame(
            columns=['onset', 'end', 'peak', 'onset_pos', 'end_pos'])
        panel[symbol] = g
        coverage.append(dict(issuer=symbol, status=status, sessions=len(idx),
                             issuer_known_sessions=int(g.i_known.sum()), funding_known_sessions=int(g.f_known.sum()),
                             common_sessions=int(g.common.sum()), episodes=len(g.attrs['episodes'])))
    return panel, pd.DataFrame(coverage), diagnostics


def run_phase(inputs, phase, samples=('common', 'common_no_funding')):
    panel, coverage, diagnostics = build_panel(inputs)
    period = inputs['protocol']['periods'][phase]
    results, alarm_tables = [], {}
    for mask in samples + ('own_price', 'own_issuer', 'own_funding', 'own_broad'):
        br, n = base_rate(panel, mask, period)
        for s in SIGNALS:
            r, a, e = evaluate(panel, s, mask, period)
            r.update(phase=phase, base_rate_pct=br, base_sessions=n)
            results.append(r)
            alarm_tables[(mask, s)] = a
    return dict(panel=panel, coverage=coverage, results=pd.DataFrame(results), alarms=alarm_tables,
                diagnostics=diagnostics, period=period)


def relative_panel(panel):
    """Copy of the panel using SPY-relative episodes as the target (secondary)."""
    out = {}
    for k, g in panel.items():
        h = g.copy()
        h.attrs['episodes'] = g.attrs['episodes_relative']
        out[k] = h
    return out


def verdict(results, dependence, sample, issuer_signal='I1', filter_signal='E2'):
    """Apply the frozen success criteria mechanically to one phase's tables."""
    r = results.loc[results['sample'].eq(sample)].set_index('signal')
    d = dependence.loc[dependence['sample'].eq(sample)]
    perm = d.dropna(subset=['permutation_p']).set_index('signal') if 'permutation_p' in d else pd.DataFrame()
    boot = d.dropna(subset=['ci90_low_pp']).set_index('signal') if 'ci90_low_pp' in d else pd.DataFrame()
    if r.loc[issuer_signal, 'alarm_onsets'] < 5:
        return dict(verdict='INCONCLUSIVE_LOW_POWER', reason=f'{issuer_signal} has fewer than 5 alarm onsets')
    p2 = r.loc['P2']
    passes = []
    for s in [issuer_signal, filter_signal]:
        diff = r.loc[s, 'precision_pct'] - p2.precision_pct
        lo = boot.loc[s + '-P2', 'ci90_low_pp'] if s + '-P2' in boot.index else np.nan
        pv = perm.loc[s, 'permutation_p'] if s in perm.index else np.nan
        passes.append(dict(criterion='a', signal=s, precision_gain_pp=diff, ci90_low_pp=lo, permutation_p=pv,
                           passed=bool(np.isfinite(diff) and diff >= 10 and np.isfinite(lo) and lo > 0
                                       and np.isfinite(pv) and pv < 0.05)))
    e1 = r.loc['E1']
    added = e1.warned - p2.warned
    extra_false = e1.false_alarms - p2.false_alarms
    p2_rate = p2.false_alarms / p2.hits if p2.hits else np.inf
    passes.append(dict(criterion='b', signal='E1', added_warned_episodes=int(added), added_false_alarms=int(extra_false),
                       passed=bool(added >= 2 and extra_false / added <= p2_rate) if added > 0 else False))
    ok = any(x['passed'] for x in passes)
    return dict(verdict='USEFUL_INCREMENTAL_WARNING' if ok else 'NOT_ESTABLISHED', checks=passes)
