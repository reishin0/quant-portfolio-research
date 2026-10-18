"""Point-in-time funding states from saved SEC XBRL company facts and submissions.

Each 10-Q/10-K uses only facts tagged with its own accession number plus the latest annual
total filed before it. Acceptance times come from the submissions index. Nothing is carried
forward beyond the declared staleness limit by the evaluator, and missing tags stay missing.
"""
from datetime import datetime, time
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

NY = ZoneInfo('America/New_York')
FORMS = {'10-Q', '10-K', '10-Q/A', '10-K/A', '20-F', '40-F'}
OCF = ['NetCashProvidedByUsedInOperatingActivities',
       'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations']
CAPEX = ['PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets',
         'PaymentsForCapitalImprovements', 'PaymentsToAcquireOilAndGasPropertyAndEquipment',
         'PaymentsToAcquireOilAndGasProperty', 'PaymentsToDevelopRealEstateAssets',
         'PaymentsToAcquireAndDevelopRealEstate']
CASH = ['CashAndCashEquivalentsAtCarryingValue']
DEBT = ['LongTermDebt', 'LongTermDebtNoncurrent', 'DebtLongtermAndShorttermCombinedAmount',
        'LongTermDebtAndCapitalLeaseObligations', 'SeniorNotes', 'ConvertibleNotesPayable',
        'DebtInstrumentCarryingAmount']
DEBT_CURRENT = ['LongTermDebtCurrent', 'DebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent',
                'LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths']
REPORTED_ONLY = ['RestrictedCashCurrent', 'RestrictedCashAndCashEquivalentsAtCarryingValue',
                 'LineOfCreditFacilityRemainingBorrowingCapacity', 'ProceedsFromIssuanceOfLongTermDebt',
                 'ProceedsFromIssuanceOfCommonStock']


def facts_frame(facts):
    rows = []
    for tag, body in facts.get('facts', {}).get('us-gaap', {}).items():
        for unit, items in body.get('units', {}).items():
            if unit != 'USD':
                continue
            for it in items:
                rows.append(dict(tag=tag, start=it.get('start'), end=it['end'], val=it['val'],
                                 accn=it['accn'], form=it.get('form'), filed=it.get('filed')))
    f = pd.DataFrame(rows, columns=['tag', 'start', 'end', 'val', 'accn', 'form', 'filed'])
    for c in ['start', 'end', 'filed']:
        f[c] = pd.to_datetime(f[c])
    f['days'] = (f.end - f.start).dt.days
    return f


def acceptance_map(submission_files):
    out = {}
    for sub in submission_files:
        recent = sub.get('filings', {}).get('recent', sub)
        for accn, acc, form, fdate in zip(recent.get('accessionNumber', []), recent.get('acceptanceDateTime', []),
                                          recent.get('form', []), recent.get('filingDate', [])):
            out[accn] = dict(acceptance=acc, form=form, filing_date=fdate)
    return out


def accepted_local(value):
    """EDGAR's acceptanceDateTime is Eastern wall-clock time despite its trailing Z.

    Checked against filingDate: filings accepted after 17:30 Eastern receive the next filing date.
    """
    t = datetime.fromisoformat(value.replace('Z', '').split('.')[0])
    return t.replace(tzinfo=NY)


def alarm_session(accepted, sessions):
    """First session whose 16:00 New York close is strictly after acceptance."""
    for s in sessions:
        if datetime.combine(s.date(), time(16, 0), tzinfo=NY) > accepted:
            return s
    return pd.NaT


def pick(f, tags, accn, end, duration=None, tol=12):
    for tag in tags:
        c = f.loc[f.tag.eq(tag) & f.accn.eq(accn) & f.end.eq(end)]
        if duration is None:
            c = c.loc[c.start.isna()]
        else:
            c = c.loc[(c.days - duration).abs() <= tol]
        if len(c):
            return float(c.val.iloc[0]), tag
    return np.nan, None


def ytd_tag(f, tags, accn, end):
    """First tag (priority order) with a fiscal-year-to-date fact ending at `end` in this accession."""
    for tag in tags:
        c = f.loc[f.tag.eq(tag) & f.accn.eq(accn) & f.end.eq(end) & f.days.notna()]
        if len(c):
            c = c.sort_values('days')
            return tag, float(c.val.iloc[-1]), int(c.days.iloc[-1])
    return None, np.nan, None


def same_tag(f, tag, accn, end, duration, end_tol=7, dur_tol=12):
    """Fact for one tag inside one accession near a given end and duration (52/53-week tolerant)."""
    c = f.loc[f.tag.eq(tag) & f.accn.eq(accn) & ((f.end - end).abs().dt.days <= end_tol)
              & ((f.days - duration).abs() <= dur_tol)]
    return (float(c.val.iloc[0]), c.end.iloc[0]) if len(c) else (np.nan, pd.NaT)


def unknown_record(symbol, accn, meta, end, status, sessions):
    accepted = accepted_local(meta['acceptance'])
    s = alarm_session(accepted, sessions)
    return dict(issuer=symbol, accn=accn, form=meta['form'], period_end=str(end.date()),
                filing_date=meta['filing_date'], acceptance_local=accepted.isoformat(),
                alarm_session=str(s.date()) if pd.notna(s) else None, F1='UNKNOWN', F2='UNKNOWN', status=status)


def filing_records(symbol, facts, submissions, sessions):
    """One record per periodic filing; anything not constructible is UNKNOWN from its alarm session."""
    f = facts_frame(facts)
    acc = acceptance_map(submissions)
    out = []
    flows = f.loc[f.tag.isin(OCF + CAPEX) & f.days.notna()]
    for accn, grp in flows.groupby('accn'):
        meta = acc.get(accn)
        if not meta or meta['form'] not in FORMS:
            continue
        end = grp.end.max()
        ocf_tag, ocf, d_ocf = ytd_tag(f, OCF, accn, end)
        cap_tag, capex, d_cap = ytd_tag(f, CAPEX, accn, end)
        if ocf_tag is None or cap_tag is None or abs(d_ocf - d_cap) > 12:
            out.append(unknown_record(symbol, accn, meta, end, 'MISSING_CASH_FLOW_TAGS', sessions))
            continue
        ttm_ocf, ttm_capex, basis = ocf, capex, 'annual'
        if d_ocf < 330:
            # TTM = latest prior annual + this YTD - prior-year comparative YTD, all with the same tags.
            prev_end = end - pd.DateOffset(years=1)
            p_ocf, _ = same_tag(f, ocf_tag, accn, prev_end, d_ocf)
            p_cap, _ = same_tag(f, cap_tag, accn, prev_end, d_ocf)
            filed = pd.Timestamp(meta['filing_date'])
            annual = f.loc[f.form.isin(['10-K', '10-K/A', '20-F', '40-F']) & (f.filed < filed)
                           & f.days.between(350, 380) & (f.end < end) & ((end - f.end).dt.days <= 300)]
            a_ocf = annual.loc[annual.tag.eq(ocf_tag)]
            a_cap = annual.loc[annual.tag.eq(cap_tag)]
            if a_ocf.empty or a_cap.empty or not np.isfinite(p_ocf) or not np.isfinite(p_cap):
                out.append(unknown_record(symbol, accn, meta, end, 'TTM_NOT_CONSTRUCTIBLE', sessions))
                continue
            # Latest filed annual value for the most recent fiscal year end, same for both tags.
            fy_end = min(a_ocf.end.max(), a_cap.end.max())
            a_ocf = a_ocf.loc[a_ocf.end.eq(fy_end)].sort_values('filed')
            a_cap = a_cap.loc[a_cap.end.eq(fy_end)].sort_values('filed')
            if a_ocf.empty or a_cap.empty:
                out.append(unknown_record(symbol, accn, meta, end, 'TTM_NOT_CONSTRUCTIBLE', sessions))
                continue
            ttm_ocf = float(a_ocf.val.iloc[-1]) + ocf - p_ocf
            ttm_capex = float(a_cap.val.iloc[-1]) + capex - p_cap
            basis = 'prior annual + YTD - prior YTD (same tags)'
        cash, _ = pick(f, CASH, accn, end)
        debt, debt_tag = pick(f, DEBT, accn, end)
        due, due_tag = pick(f, DEBT_CURRENT, accn, end)
        gap = ttm_capex - ttm_ocf
        f1 = 'UNKNOWN' if not np.isfinite(debt) else ('FUNDING_WATCH' if gap > 0 and debt > 0 else 'NO_FLAG')
        if f1 == 'FUNDING_WATCH':
            f2 = 'UNKNOWN' if not np.isfinite(cash) else (
                'FUNDING_GAP' if cash < (due if np.isfinite(due) else 0) + gap else 'NO_FLAG')
        else:
            f2 = f1 if f1 == 'UNKNOWN' else 'NO_FLAG'
        reported = {t: pick(f, [t], accn, end)[0] for t in REPORTED_ONLY[:3]}
        reported.update({t: ytd_tag(f, [t], accn, end)[1] for t in REPORTED_ONLY[3:]})
        rec = unknown_record(symbol, accn, meta, end, 'OK', sessions)
        rec.update(ttm_basis=basis, ttm_ocf_usd=ttm_ocf, ttm_capex_usd=ttm_capex, capex_tag=cap_tag, ocf_tag=ocf_tag,
                   unrestricted_cash_usd=cash, debt_usd=debt, debt_tag=debt_tag, debt_due_12m_usd=due,
                   debt_due_tag=due_tag, F1=f1, F2=f2, **{'reported_' + k: v for k, v in reported.items()})
        out.append(rec)
    return current_only(out)


def current_only(records):
    """A filing for a period older than one already public (e.g. a late amendment) never replaces the
    current state; it is kept in the ledger as OLDER_PERIOD_REVISION with no state effect."""
    records = sorted(records, key=lambda r: r['acceptance_local'])
    latest = None
    for r in records:
        if latest is not None and r['period_end'] <= latest:
            r['status'] = 'OLDER_PERIOD_REVISION'
            r['state_effect'] = False
        else:
            r['state_effect'] = True
            latest = r['period_end']
    return records


def build(data_dir, sessions):
    data_dir = Path(data_dir)
    records = []
    for facts_path in sorted((data_dir / 'raw').glob('sec_*_facts.json')):
        symbol = facts_path.name[4:-11]
        subs = [json.loads(p.read_text(encoding='utf-8'))
                for p in sorted((data_dir / 'raw').glob(f'sec_{symbol}_*.json')) if 'facts' not in p.name]
        facts = json.loads(facts_path.read_text(encoding='utf-8'))
        records += filing_records(symbol, facts, subs, sessions)
    return records


def build_addendum(root):
    """Write funding_addendum/filings.json and its manifest from saved SEC files; never overwrites."""
    import hashlib
    from datetime import timezone as tz
    root = Path(root)
    data = root / 'data/early_warning_20261018'
    out = data / 'funding_addendum'
    for name in ['filings.json', 'manifest.json']:
        if (out / name).exists():
            raise FileExistsError(out / name)
    sessions = pd.read_csv(data / 'equity_adjusted.csv', index_col=0, parse_dates=True).index
    records = build(data, sessions)
    clean = json.loads(pd.DataFrame(records).replace({np.nan: None}).to_json(orient='records'))
    (out / 'filings.json').write_text(json.dumps(dict(created_at=datetime.now(tz.utc).isoformat(), records=clean), indent=1) + '\n',
                                     encoding='utf-8')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    raw = sorted((data / 'raw').glob('sec_*'))
    manifest = dict(created_at=datetime.now(tz.utc).isoformat(),
                    file_sha256={n: digest(out / n) for n in ['declaration.json', 'filings.json']},
                    parser_sha256=digest(Path(__file__)),
                    local_raw_sha256={p.name: digest(p) for p in raw},
                    sec_receipts={p.name: digest(p) for p in sorted((data / 'receipts').glob('sec_*'))})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return records


def load_addendum(root, expected_manifest_sha=None):
    import hashlib
    out = Path(root) / 'data/early_warning_20261018/funding_addendum'
    raw = (out / 'manifest.json').read_bytes()
    if expected_manifest_sha and hashlib.sha256(raw).hexdigest() != expected_manifest_sha:
        raise ValueError('Funding addendum manifest changed')
    manifest = json.loads(raw)
    for name, d in manifest['file_sha256'].items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != d:
            raise ValueError('Funding addendum changed: ' + name)
    for name, d in manifest['local_raw_sha256'].items():
        p = out.parent / 'raw' / name
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != d:
            raise ValueError('Local SEC raw file changed: ' + name)
    f = pd.DataFrame(json.loads((out / 'filings.json').read_text(encoding='utf-8'))['records'])
    usable = f.loc[f.state_effect.astype(bool) & f.alarm_session.notna()].copy()
    return f, usable, manifest


if __name__ == '__main__':
    recs = build_addendum(Path(__file__).resolve().parents[2])
    print(pd.DataFrame(recs).groupby(['issuer', 'status']).size().unstack(fill_value=0).to_string())
