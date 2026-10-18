"""Issuer-scoped funding and yield diagnostics; never a qualified OAS signal."""
from datetime import date, datetime, timedelta
import re
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

DIAGNOSTIC_COLUMNS = ['issuer', 'cusip', 'date', 'yield_pct', 'state',
                      'baseline_yield_pct', 'minimum_widening_bp']
TIMELINE_COLUMNS = ['date', 'eligible_bonds', 'warning_bonds', 'state', 'onset_or_resumption']


def inside(root, relative):
    """Case references are repository-relative, with no path escape."""
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Expected relative evidence path')
    path = (root/relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Evidence path escapes its root')
    return path


def verify_preserved(root, manifest, case):
    """Allow declared Git line-ending changes only for supporting text files.

    Mathematical code, notebooks and data always require their exact byte hashes.
    The canonical LF digest must be recorded explicitly in the case declaration.
    """
    preserved = manifest.get('preserved_project_sha256',{})
    canonical = case.get('preserved_text_lf_sha256',{})
    for name in canonical:
        if name not in preserved or not (name == '.gitattributes' or Path(name).suffix in {'.md','.txt','.bat','.command'}):
            raise ValueError('Text normalization is forbidden for this frozen artifact')
    for name, expected in preserved.items():
        raw = inside(root,name).read_bytes()
        if hashlib.sha256(raw).hexdigest() == expected:
            continue
        if name in canonical and hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest() == canonical[name]:
            continue
        raise ValueError('Preserved project changed: '+name)


def load_case(root, case_path):
    """Verify immutable evidence and issuer ownership before calculating a case."""
    root = Path(root).resolve()
    case = json.loads(inside(root, case_path).read_text(encoding='utf-8'))
    if not re.fullmatch(r'[a-z0-9_-]+', case.get('case_id','')):
        raise ValueError('Case id must be a safe lowercase identifier')
    spec = dict(case['rules'], issuer=case['issuer'], bonds=case['bonds'], bond_window=case['bond_window'])
    validate_spec(spec)
    ZoneInfo(case['reporting_timezone'])
    if not re.fullmatch(r'[A-Z]{3} millions', case['units']) or case['units'].split()[0] != case['bond_currency']:
        raise ValueError('Case requires one declared monetary currency; no implicit FX conversion')
    data = inside(root, case['evidence_dir'])
    manifest_path = data/'manifest.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != case['evidence_manifest_sha256']:
        raise ValueError('Evidence manifest changed')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    required = {'bond_daily.csv','equity_adjusted.csv','funding_disclosures.json','instruments.json'}
    if not required.issubset(manifest['file_sha256']):
        raise ValueError('Case inputs must all be pinned in the evidence manifest')
    for name, expected in manifest['file_sha256'].items():
        if hashlib.sha256(inside(data,name).read_bytes()).hexdigest() != expected:
            raise ValueError('Evidence changed: '+name)
    verify_preserved(root,manifest,case)
    if 'source_spec_sha256' in manifest:
        prior = inside(root, case['prior_spec_path'])
        if hashlib.sha256(prior.read_bytes()).hexdigest() != manifest['source_spec_sha256']:
            raise ValueError('Prior case specification changed')
    instruments = pd.DataFrame(json.loads((data/'instruments.json').read_text(encoding='utf-8')))
    if not {'cusip','issuerName'}.issubset(instruments) or instruments.cusip.duplicated().any():
        raise ValueError('Invalid instrument ownership table')
    selected = instruments.loc[instruments.cusip.isin(case['bonds'])].copy()
    if set(selected.cusip) != set(case['bonds']) or not selected.issuerName.eq(case['bond_issuer_name']).all():
        raise ValueError('Bond ownership does not match declared issuer')
    bonds = pd.read_csv(data/'bond_daily.csv',dtype={'cusip':str})
    equity = pd.read_csv(data/'equity_adjusted.csv',index_col=0,parse_dates=True)
    if set(equity.columns) != set(case['equity_symbols']) or case['issuer'] not in equity.columns:
        raise ValueError('Equity panel does not match case symbols')
    equity = equity[case['equity_symbols']]
    funding = json.loads((data/'funding_disclosures.json').read_text(encoding='utf-8'))
    return case, spec, manifest, selected, bonds, equity, funding


def positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f'{name} must be a positive integer')
    return value


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Expected YYYY-MM-DD date, without an intraday time')
    return date.fromisoformat(value)


def daily_index(values, unique=True):
    result = pd.DatetimeIndex(pd.to_datetime(values, errors='raise'))
    if result.tz is not None or result.hasnans or (result != result.normalize()).any():
        raise ValueError('Expected timezone-naive daily session dates')
    if unique and result.has_duplicates:
        raise ValueError('Duplicate session date')
    return result


def validate_spec(spec):
    if not isinstance(spec.get('issuer'), str) or not spec['issuer'].strip():
        raise ValueError('Case issuer is required')
    bonds = spec.get('bonds')
    if not isinstance(bonds, list) or not bonds or any(not isinstance(b, str) or not b.strip() for b in bonds):
        raise ValueError('Declare nonempty instrument identifiers')
    if len(bonds) != len(set(bonds)):
        raise ValueError('Duplicate configured instrument')
    for key in ('history', 'persistence', 'max_gap_calendar_days', 'min_warning_bonds'):
        positive_int(spec.get(key), key)
    if spec['min_warning_bonds'] > len(bonds):
        raise ValueError('Warning quorum exceeds configured instruments')
    threshold = spec.get('widening_bp')
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Widening threshold must be positive finite basis points')
    window = spec.get('bond_window')
    if not isinstance(window, list) or len(window) != 2 or iso_date(window[0]) > iso_date(window[1]):
        raise ValueError('Invalid bond window')


def funding_timeline(records, *, issuer, units, reporting_timezone):
    """One issuer/currency; preserve periods and revisions as dated disclosures.

    This returns disclosure events, not a carried-forward current funding state.
    Eligibility is the following local midnight, not measured historical receipt.
    """
    if not issuer or not re.fullmatch(r'[A-Z]{3} millions', units):
        raise ValueError('Declare issuer and units such as USD millions')
    zone = ZoneInfo(reporting_timezone)
    result, seen = [], set()
    for r in records:
        if r['issuer'] != issuer or r['units'] != units:
            raise ValueError('Mixed issuer or monetary units')
        start, end, filed = [iso_date(r[k]) for k in ('period_start', 'period_end', 'filed_on')]
        identity = (start, end, filed)
        if start > end or end > filed or identity in seen:
            raise ValueError('Invalid or duplicate financial disclosure')
        seen.add(identity)
        url = urlparse(r['source_url'])
        if url.scheme != 'https' or not url.hostname:
            raise ValueError('Missing public HTTPS disclosure source')
        values = [r[k] for k in ('cash_capex', 'operating_cash_flow', 'debt_principal')]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not np.isfinite(x) for x in values):
            raise ValueError('Invalid monetary input')
        if r['cash_capex'] < 0 or r['debt_principal'] < 0:
            raise ValueError('Cash capex and principal must be nonnegative')
        available = datetime.combine(filed + timedelta(days=1), datetime.min.time(), tzinfo=zone)
        gap = r['cash_capex'] - r['operating_cash_flow']
        result.append(dict(issuer=issuer, period_start=start.isoformat(), period_end=end.isoformat(),
                           period=r['period_label'], eligible_at=available.isoformat(),
                           historical_gap=gap, debt_principal=r['debt_principal'], units=units,
                           state='FUNDING_VULNERABILITY' if gap > 0 and r['debt_principal'] > 0 else 'NO_FLAG',
                           source_url=r['source_url']))
    columns = ['issuer','period_start','period_end','period','eligible_at','historical_gap',
               'debt_principal','units','state','source_url']
    return pd.DataFrame(result, columns=columns).sort_values(['eligible_at','period_end','period_start']).reset_index(drop=True)


def bond_diagnostics(frame, spec):
    """Trade-date diagnostics only. Missing prices/yields invalidate their windows."""
    validate_spec(spec)
    f = frame.copy()
    required = {'cusip', 'tradeDate', 'lastSalePrice', 'lastSaleYield'}
    if not required.issubset(f):
        raise ValueError('Missing TRACE columns')
    if 'issuer' in f and not f['issuer'].eq(spec['issuer']).all():
        raise ValueError('Mixed issuer panel')
    f['tradeDate'] = daily_index(f['tradeDate'], unique=False)
    if f.duplicated(['cusip', 'tradeDate']).any():
        raise ValueError('Duplicate instrument-day')
    if not set(f.cusip).issubset(spec['bonds']):
        raise ValueError('Unexpected instrument')
    if (f.tradeDate < pd.Timestamp(spec['bond_window'][0])).any() or (f.tradeDate > pd.Timestamp(spec['bond_window'][1])).any():
        raise ValueError('Observation outside declared window')
    for col in ('lastSalePrice', 'lastSaleYield'):
        if f[col].map(lambda x: isinstance(x, (bool, np.bool_))).any():
            raise ValueError('Boolean price/yield is invalid')
        f[col] = pd.to_numeric(f[col], errors='raise')
        if np.isinf(f[col]).any() or (col == 'lastSalePrice' and (f[col] <= 0).any()):
            raise ValueError('Invalid price or yield')
    n, p = spec['history'], spec['persistence']
    out = []
    for cusip, g in f.groupby('cusip'):
        g = g.sort_values('tradeDate').reset_index(drop=True)
        for i, row in g.iterrows():
            item = dict(issuer=spec['issuer'], cusip=cusip, date=row.tradeDate, yield_pct=row.lastSaleYield,
                        state='UNKNOWN', baseline_yield_pct=np.nan, minimum_widening_bp=np.nan)
            if i + 1 >= n + p:
                window = g.iloc[i + 1 - n - p:i + 1]
                if (not window[['lastSalePrice','lastSaleYield']].isna().any().any()
                        and window.tradeDate.diff().dropna().dt.days.max() <= spec['max_gap_calendar_days']):
                    baseline = window.lastSaleYield.iloc[:n].median()
                    widening = (window.lastSaleYield.iloc[n:] - baseline) * 100
                    item.update(baseline_yield_pct=baseline, minimum_widening_bp=widening.min(),
                                state='YIELD_WARNING_DIAGNOSTIC' if (widening >= spec['widening_bp']).all() else 'NO_FLAG')
            out.append(item)
    return pd.DataFrame(out, columns=DIAGNOSTIC_COLUMNS).sort_values(['date','cusip']).reset_index(drop=True)


def issuer_timeline(diagnostics, session_dates, spec):
    """Count distinct same-day bonds from one declared issuer; never fill prints."""
    validate_spec(spec)
    d = diagnostics.copy()
    if not set(DIAGNOSTIC_COLUMNS).issubset(d):
        raise ValueError('Missing diagnostic columns')
    d['date'] = daily_index(d['date'], unique=False)
    if d.duplicated(['cusip','date']).any():
        raise ValueError('Duplicate diagnostic instrument-day')
    if not d['issuer'].eq(spec['issuer']).all() or not set(d.cusip).issubset(spec['bonds']):
        raise ValueError('Diagnostic issuer/instrument mismatch')
    if not d.state.isin(['UNKNOWN','NO_FLAG','YIELD_WARNING_DIAGNOSTIC']).all():
        raise ValueError('Invalid diagnostic state')
    rows = []
    for session in daily_index(session_dates).sort_values():
        day = d.loc[d.date == session]
        flags = int((day.state == 'YIELD_WARNING_DIAGNOSTIC').sum())
        known = int((day.state != 'UNKNOWN').sum())
        quorum = spec['min_warning_bonds']
        state = 'YIELD_WARNING_DIAGNOSTIC' if flags >= quorum else ('NO_QUORUM' if known >= quorum else 'UNKNOWN')
        rows.append(dict(date=session, eligible_bonds=known, warning_bonds=flags, state=state))
    timeline = pd.DataFrame(rows, columns=TIMELINE_COLUMNS[:-1])
    timeline['onset_or_resumption'] = (timeline.state == 'YIELD_WARNING_DIAGNOSTIC') & (timeline.state.shift() != 'YIELD_WARNING_DIAGNOSTIC')
    return timeline


def equity_context(timeline, equity, horizons=(5, 20)):
    """Forward changes over observed rows, not executable or calendar-day returns."""
    if not horizons or len(horizons) != len(set(horizons)):
        raise ValueError('Declare unique positive session horizons')
    for horizon in horizons:
        positive_int(horizon, 'horizon')
    prices = equity.copy()
    prices.index = daily_index(prices.index)
    prices = prices.sort_index()
    if prices.columns.has_duplicates or any(not isinstance(c,str) or not c for c in prices.columns):
        raise ValueError('Equity symbol columns must be unique strings')
    if prices.isna().any().any() or any(prices[c].map(lambda x: isinstance(x,(bool,np.bool_))).any() for c in prices):
        raise ValueError('Invalid equity panel; do not fill missing prices')
    try:
        prices = prices.apply(pd.to_numeric, errors='raise')
        if not np.isfinite(prices.to_numpy(dtype=float)).all() or (prices <= 0).any().any():
            raise ValueError('Equity prices must be positive and finite')
    except (TypeError, ValueError) as exc:
        raise ValueError('Invalid equity prices') from exc
    if not {'date','onset_or_resumption'}.issubset(timeline):
        raise ValueError('Missing timeline columns')
    daily_index(timeline.date)
    if not timeline.onset_or_resumption.map(lambda x:isinstance(x,(bool,np.bool_))).all():
        raise ValueError('Onset flags must be boolean')
    columns = ['date'] + [f'{s}_{h}_sessions_pct' for s in prices.columns for h in horizons]
    rows = []
    for session in pd.to_datetime(timeline.loc[timeline.onset_or_resumption, 'date']):
        if session not in prices.index:
            raise ValueError('Missing event-date equity price')
        pos = prices.index.get_loc(session)
        r = dict(date=session)
        for symbol in prices.columns:
            for horizon in horizons:
                r[f'{symbol}_{horizon}_sessions_pct'] = (100 * (prices.iloc[pos+horizon][symbol] / prices.iloc[pos][symbol] - 1)
                    if pos+horizon < len(prices) else np.nan)
        rows.append(r)
    return pd.DataFrame(rows, columns=columns)
