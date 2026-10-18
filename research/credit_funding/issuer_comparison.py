"""Offline, fixed-rule cross-issuer diagnostic with explicit coverage and censoring."""
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
import pandas as pd
from research.credit_funding.issuer_replay import (
    inside, iso_date, daily_index, positive_int, bond_diagnostics, issuer_timeline,
)

STUDY_PATH = 'research/credit_funding/issuer_study_20261018.json'
STUDY_DATA = 'data/issuer_study_20261018'
WARNING = 'YIELD_WARNING_DIAGNOSTIC'


def prepare_bonds(raw):
    """Keep invalid observations as missing, invalidating their entire windows."""
    frame = raw.copy()
    required = {'cusip', 'tradeDate', 'lastSalePrice', 'lastSaleYield'}
    if not required.issubset(frame):
        raise ValueError('Missing bond columns')
    for field in ['lastSalePrice', 'lastSaleYield']:
        if frame[field].map(lambda x: isinstance(x, (bool, np.bool_))).any():
            raise ValueError('Boolean bond observation')
        frame[field] = pd.to_numeric(frame[field], errors='raise')
    invalid = (~np.isfinite(frame.lastSalePrice) | (frame.lastSalePrice <= 0)
               | ~np.isfinite(frame.lastSaleYield))
    frame.loc[invalid, ['lastSalePrice', 'lastSaleYield']] = np.nan
    return frame, int(invalid.sum())


def validate_prices(prices):
    result = prices.copy()
    result.index = daily_index(result.index)
    if not result.index.is_monotonic_increasing or result.empty or result.columns.has_duplicates:
        raise ValueError('Prices require unique columns and ordered daily observations')
    if any(result[c].map(lambda x: isinstance(x, (bool, np.bool_))).any() for c in result):
        raise ValueError('Boolean equity observation')
    result = result.apply(pd.to_numeric, errors='raise')
    if not np.isfinite(result.to_numpy()).all() or (result <= 0).any().any():
        raise ValueError('Missing/invalid equity observations; do not fill')
    return result


def forward_outcomes(prices, dates, symbol, horizons=(5, 20), threshold=-10):
    """Anchor at event close, exclude same-day moves, censor incomplete windows.

    minimum_close_pct is relative to the event close, not peak-to-trough drawdown.
    The event close is a descriptive anchor, not a verified executable entry.
    """
    prices = validate_prices(prices)
    if symbol not in prices or not horizons or len(set(horizons)) != len(horizons):
        raise ValueError('Invalid symbol or horizons')
    for h in horizons:
        positive_int(h, 'horizon')
    if isinstance(threshold, bool) or not np.isfinite(threshold) or not -100 < threshold < 0:
        raise ValueError('Loss threshold must be between -100 and zero')
    rows = []
    for date in daily_index(dates):
        if date not in prices.index:
            raise ValueError('Event must have an observed close')
        pos = prices.index.get_loc(date)
        for h in horizons:
            available = min(h, len(prices) - pos - 1)
            item = dict(issuer=symbol, date=date, horizon=h, observed_after=available,
                        complete=available == h, close_return_pct=np.nan,
                        minimum_close_pct=np.nan, loss_hit=None, excess_spy_pct=np.nan)
            if available == h:
                path = 100 * (prices[symbol].iloc[pos+1:pos+h+1] / prices[symbol].iloc[pos] - 1)
                item.update(close_return_pct=float(path.iloc[-1]), minimum_close_pct=float(path.min()),
                            loss_hit=bool(path.min() <= threshold))
                if 'SPY' in prices:
                    item['excess_spy_pct'] = float(path.iloc[-1] - 100 * (
                        prices.SPY.iloc[pos+h] / prices.SPY.iloc[pos] - 1))
            rows.append(item)
    columns = ['issuer', 'date', 'horizon', 'observed_after', 'complete',
               'close_return_pct', 'minimum_close_pct', 'loss_hit', 'excess_spy_pct']
    return pd.DataFrame(rows, columns=columns)


def disclosure_events(records, prices):
    """One event per declared issuer; no carrying stale balance sheets forward."""
    prices = validate_prices(prices)
    result, seen = [], set()
    for r in records:
        symbol = r['issuer']
        if symbol in seen or symbol not in prices:
            raise ValueError('Duplicate/unknown disclosure issuer')
        seen.add(symbol)
        published, start, end = [iso_date(r[k]) for k in ['published_on', 'period_start', 'period_end']]
        if start > end or end > published or r['units'] != 'USD millions':
            raise ValueError('Invalid disclosure period or units')
        if urlparse(r['source_url']).scheme != 'https':
            raise ValueError('Primary disclosure URL required')
        for key in ['operating_cash_flow', 'cash_capex', 'reported_debt']:
            value = r[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
                raise ValueError('Invalid funding input')
        if r['cash_capex'] < 0 or r['reported_debt'] < 0 or not r.get('debt_basis'):
            raise ValueError('Invalid capex/debt or missing debt basis')
        eligible = pd.Timestamp(published + timedelta(days=1))
        sessions = prices.index[prices.index >= eligible]
        gap = r['cash_capex'] - r['operating_cash_flow']
        result.append(dict(issuer=symbol, published_on=str(published), period_start=str(start), period_end=str(end),
            eligible_date=eligible, event_close=sessions[0] if len(sessions) else pd.NaT,
            historical_gap_usdm=gap, state='FUNDING_VULNERABILITY' if gap > 0 and r['reported_debt'] > 0 else 'NO_FLAG',
            source_url=r['source_url']))
    return pd.DataFrame(result)


def crash_audit(prices, symbol, timeline=None, threshold=-10, lookback=20):
    """Prior 1..20 closes only; unknown coverage is never a missed signal."""
    prices = validate_prices(prices)
    positive_int(lookback, 'lookback')
    returns = prices[symbol].pct_change(fill_method=None) * 100
    states = None
    if timeline is not None:
        dates = daily_index(timeline.date)
        if not dates.equals(prices.index) or not timeline.state.isin([WARNING, 'NO_QUORUM', 'UNKNOWN']).all():
            raise ValueError('Timeline must match the full equity calendar and valid states')
        states = timeline.set_index('date').state
    rows = []
    for date in returns.index[returns <= threshold]:
        pos = prices.index.get_loc(date)
        status, lead = 'NOT_EVALUABLE', np.nan
        if states is not None:
            prior = states.iloc[max(0, pos-lookback):pos]
            hits = prior.index[prior.eq(WARNING)]
            if len(hits):
                status, lead = 'PRIOR_WARNING', pos - prices.index.get_loc(hits[-1])
            elif len(prior) < lookback or prior.eq('UNKNOWN').any():
                status = 'UNKNOWN_PRIOR_COVERAGE'
            else:
                status = 'NO_PRIOR_WARNING'
        rows.append(dict(issuer=symbol, date=date, daily_return_pct=float(returns[date]),
                         bond_prior_status=status, latest_warning_lead_sessions=lead))
    return pd.DataFrame(rows, columns=['issuer','date','daily_return_pct','bond_prior_status','latest_warning_lead_sessions'])


def load_study(root, expected_manifest_sha=None):
    root = Path(root)
    directory = inside(root, STUDY_DATA)
    manifest_raw = (directory/'manifest.json').read_bytes()
    if expected_manifest_sha and hashlib.sha256(manifest_raw).hexdigest() != expected_manifest_sha:
        raise ValueError('Study manifest changed')
    manifest = json.loads(manifest_raw)
    plan = json.loads(inside(root, STUDY_PATH).read_text(encoding='utf-8'))
    required = {'selection.json','equity_adjusted.csv','funding_disclosures.json','bond_currency_sources.json'}
    required.update(s+'_instruments.json' for s in plan['candidates'])
    if not required.issubset(manifest['file_sha256']):
        raise ValueError('Unpinned study inputs')
    for name, digest in manifest['file_sha256'].items():
        if hashlib.sha256(inside(directory, name).read_bytes()).hexdigest() != digest:
            raise ValueError('Study evidence changed: ' + name)
    raw = inside(root, STUDY_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['study_sha256']:
        raise ValueError('Study declaration changed')
    plan = json.loads(raw)
    selection = json.loads((directory/'selection.json').read_text(encoding='utf-8'))
    if selection['study_sha256'] != manifest['study_sha256']:
        raise ValueError('Selection refers to a different plan')
    if set(selection['selection']) != set(plan['candidates']):
        raise ValueError('Selection must retain the declared universe')
    for symbol, choice in selection['selection'].items():
        if choice['bonds'] and symbol+'_bonds.csv' not in manifest['file_sha256']:
            raise ValueError('Unpinned bond input')
    prices = validate_prices(pd.read_csv(directory/'equity_adjusted.csv', index_col=0, parse_dates=True))
    if set(prices) != set(plan['candidates']) | {'SPY','QQQ'}:
        raise ValueError('Unexpected equity universe')
    if prices.index.min() < pd.Timestamp(plan['window'][0]) or prices.index.max() > pd.Timestamp(plan['window'][1]):
        raise ValueError('Equity outside study window')
    # Require full XNYS session coverage; this detects missing whole dates, not just NaNs.
    import exchange_calendars as xcals
    expected = pd.DatetimeIndex(xcals.get_calendar('XNYS').sessions_in_range(*plan['window']))
    if expected.tz is not None:
        expected = expected.tz_localize(None)
    if not prices.index.equals(expected):
        raise ValueError('Incomplete exchange-session panel; no synthetic replacement')
    funding = json.loads((directory/'funding_disclosures.json').read_text(encoding='utf-8'))
    if {r['issuer'] for r in funding['records']} != set(plan['candidates']):
        raise ValueError('Disclosure coverage must retain all candidates')
    return plan, selection['selection'], prices, funding, manifest


def disclosure_price_context(prices, disclosures):
    """Was weakness already visible by the disclosure's observed-close anchor?"""
    prices = validate_prices(prices)
    rows = []
    for r in disclosures.to_dict('records'):
        symbol, event = r['issuer'], r['event_close']
        if pd.isna(event):
            continue
        if symbol not in prices or event not in prices.index:
            raise ValueError('Disclosure context requires an observed symbol/date')
        p = prices[symbol]
        pos = p.index.get_loc(event)
        item = dict(issuer=symbol, event_close=event,
                    from_window_start_pct=100*(p.iloc[pos]/p.iloc[0]-1),
                    earlier_daily_10pct_falls_in_20_sessions=int(
                        p.pct_change(fill_method=None).iloc[max(1,pos-20):pos].le(-.10).sum()))
        for h in (5,20):
            item[f'change_to_anchor_over_previous_{h}_sessions_pct'] = (
                100*(p.iloc[pos]/p.iloc[pos-h]-1) if pos >= h else np.nan)
        rows.append(item)
    return pd.DataFrame(rows)


def summarize_arm(outcomes, symbol, arm):
    rows = []
    for h in (5,20):
        f = outcomes.loc[outcomes.horizon == h]
        complete = f.loc[f.complete]
        hits = int(complete.loss_hit.sum()) if len(complete) else 0
        rows.append(dict(issuer=symbol, arm=arm, horizon=h, events=len(f), complete=len(complete),
            censored=len(f)-len(complete), loss_hits=hits,
            loss_frequency_pct=100*hits/len(complete) if len(complete) else np.nan,
            no_loss_frequency_pct=100*(len(complete)-hits)/len(complete) if len(complete) else np.nan,
            mean_close_return_pct=complete.close_return_pct.mean()))
    return rows


def run_study(root, expected_manifest_sha=None):
    plan, selected, prices, funding, manifest = load_study(root, expected_manifest_sha)
    directory = inside(root, STUDY_DATA)
    disclosures = disclosure_events(funding['records'], prices)
    events, comparisons, crashes, coverage, instruments = [], [], [], [], []
    timelines = {}
    for symbol in plan['candidates']:
        choice = selected[symbol]
        metadata = pd.DataFrame(json.loads((directory/(symbol+'_instruments.json')).read_text(encoding='utf-8')))
        if metadata.cusip.duplicated().any():
            raise ValueError('Duplicate instrument metadata')
        chosen = metadata.loc[metadata.cusip.isin(choice['bonds'])].copy()
        if set(chosen.cusip) != set(choice['bonds']):
            raise ValueError('Missing ownership metadata')
        instruments.extend([dict(equity_symbol=symbol, **r) for r in chosen.to_dict('records')])
        timeline = None
        raw_rows = unavailable = 0
        if choice['bonds']:
            raw = pd.read_csv(directory/(symbol+'_bonds.csv'), dtype={'cusip':str})
            clean, unavailable = prepare_bonds(raw)
            raw_rows = len(raw)
            if not set(clean.cusip).issubset(choice['bonds']):
                raise ValueError('Unexpected bond history identifier')
            # A quoted Reg S/144A twin is never a second independent issue.
            if chosen.duplicated(['issuerName','maturityDate','couponRate']).any():
                raise ValueError('Duplicate economic issue')
            if not chosen.isConvertible.eq('N').all() or not chosen.couponType.eq('FXPV').all():
                raise ValueError('Ineligible bond type')
            if choice.get('legal_issuer'):
                if not chosen.issuerName.eq(choice['legal_issuer']).all():
                    raise ValueError('Mixed legal borrowers cannot establish quorum')
                currency = json.loads((directory/'bond_currency_sources.json').read_text(encoding='utf-8'))
                if currency['currency'] != 'USD' or not set(choice['bonds']).issubset(currency['sources']):
                    raise ValueError('Missing currency evidence')
                spec = dict(plan['rules'], issuer=symbol, bonds=choice['bonds'], bond_window=plan['window'])
                timeline = issuer_timeline(bond_diagnostics(clean, spec), prices.index, spec)
                timelines[symbol] = timeline
            else:
                # Validate each project separately without pretending its single issue meets quorum.
                for borrower, group in chosen.groupby('issuerName'):
                    ids = group.cusip.tolist()
                    if len(ids) >= plan['rules']['min_warning_bonds']:
                        raise ValueError('Coverage declaration needs review: potentially evaluable legal issuer')
                    spec = dict(plan['rules'], issuer=borrower, bonds=ids, min_warning_bonds=1, bond_window=plan['window'])
                    bond_diagnostics(clean.loc[clean.cusip.isin(ids)], spec)
        coverage.append(dict(issuer=symbol, role=choice['role'], bond_rows=raw_rows,
            unavailable_bond_rows=unavailable, equity_sessions=len(prices),
            last_bond_date=raw.tradeDate.max() if raw_rows else None,
            evaluable_sessions=int(timeline.state.ne('UNKNOWN').sum()) if timeline is not None else 0,
            unknown_or_ineligible_sessions=int(timeline.state.eq('UNKNOWN').sum()) if timeline is not None else len(prices),
            warning_sessions=int(timeline.state.eq(WARNING).sum()) if timeline is not None else None,
            warning_onsets=int(timeline.onset_or_resumption.sum()) if timeline is not None else None))
        arms = {'all_equity_days': prices.index,
                'price_only_minus5pct': prices.index[prices[symbol].pct_change(fill_method=None).le(-.05)]}
        if timeline is not None:
            arms.update(bond_warning_onsets=pd.DatetimeIndex(timeline.loc[timeline.onset_or_resumption,'date']),
                        eligible_nonwarning_days=pd.DatetimeIndex(timeline.loc[timeline.state.eq('NO_QUORUM'),'date']),
                        price_only_same_bond_coverage=prices.index[
                            prices[symbol].pct_change(fill_method=None).le(-.05) & timeline.state.ne('UNKNOWN').to_numpy()])
        disclosure = disclosures.loc[disclosures.issuer.eq(symbol)].iloc[0]
        arms['first_funding_watch'] = pd.DatetimeIndex([disclosure.event_close] if
            disclosure.state == 'FUNDING_VULNERABILITY' and pd.notna(disclosure.event_close) else [])
        for arm, dates in arms.items():
            result = forward_outcomes(prices, dates, symbol, plan['outcomes']['horizons'], plan['outcomes']['loss_threshold_pct'])
            comparisons.extend(summarize_arm(result, symbol, arm))
            if arm in ['first_funding_watch','bond_warning_onsets']:
                result['arm'] = arm
                events.append(result)
        crashes.append(crash_audit(prices, symbol, timeline, plan['outcomes']['loss_threshold_pct']))
    return dict(plan=plan, manifest=manifest, prices=prices, disclosures=disclosures,
                disclosure_context=disclosure_price_context(prices, disclosures),
                coverage=pd.DataFrame(coverage), instruments=pd.DataFrame(instruments),
                events=pd.DataFrame([row for f in events for row in f.to_dict('records')], columns=list(events[0])),
                comparison=pd.DataFrame(comparisons),
                crashes=pd.DataFrame([row for f in crashes for row in f.to_dict('records')], columns=list(crashes[0])), timelines=timelines,
                funding_records=pd.DataFrame(funding['records']))
