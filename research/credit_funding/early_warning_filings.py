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


def ytd(f, tags, accn, end):
    """Longest duration fact ending at `end` in this accession (fiscal year to date)."""
    for tag in tags:
        c = f.loc[f.tag.eq(tag) & f.accn.eq(accn) & f.end.eq(end) & f.days.notna()]
        if len(c):
            c = c.sort_values('days')
            return float(c.val.iloc[-1]), int(c.days.iloc[-1]), tag
    return np.nan, None, None


def filing_records(symbol, facts, submissions, sessions):
    f = facts_frame(facts)
    acc = acceptance_map(submissions)
    out = []
    flows = f.loc[f.tag.isin(OCF + CAPEX)]
    for accn, grp in flows.groupby('accn'):
        meta = acc.get(accn)
        if not meta or meta['form'] not in FORMS:
            continue
        end = grp.end.max()
        ocf, d_ocf, ocf_tag = ytd(f, OCF, accn, end)
        capex, d_cap, cap_tag = ytd(f, CAPEX, accn, end)
        if not np.isfinite(ocf) or not np.isfinite(capex) or d_ocf != d_cap:
            out.append(dict(issuer=symbol, accn=accn, form=meta['form'], period_end=str(end.date()),
                            status='MISSING_CASH_FLOW_TAGS'))
            continue
        ttm_ocf, ttm_capex, basis = ocf, capex, 'annual'
        if d_ocf < 330:
            # TTM = latest prior annual + this YTD - prior-year comparative YTD (both from filings already public).
            prev_end = end - pd.DateOffset(years=1)
            p_ocf = pick(f, OCF, accn, f.loc[(f.end - prev_end).abs().dt.days <= 7, 'end'].max(), d_ocf)[0] \
                if ((f.end - prev_end).abs().dt.days <= 7).any() else np.nan
            p_cap = pick(f, CAPEX, accn, f.loc[(f.end - prev_end).abs().dt.days <= 7, 'end'].max(), d_ocf)[0] \
                if ((f.end - prev_end).abs().dt.days <= 7).any() else np.nan
            filed = pd.Timestamp(meta['filing_date'])
            annual = f.loc[f.tag.isin(OCF + CAPEX) & f.form.isin(['10-K', '10-K/A', '20-F', '40-F'])
                           & (f.filed < filed) & (f.days.between(350, 380)) & (f.end < end)]
            if annual.empty or not np.isfinite(p_ocf) or not np.isfinite(p_cap):
                out.append(dict(issuer=symbol, accn=accn, form=meta['form'], period_end=str(end.date()),
                                status='TTM_NOT_CONSTRUCTIBLE'))
                continue
            last = annual.loc[annual.filed.eq(annual.filed.max())]
            fy_end = last.end.max()
            a_ocf = last.loc[last.tag.isin(OCF) & last.end.eq(fy_end), 'val']
            a_cap = last.loc[last.tag.isin(CAPEX) & last.end.eq(fy_end), 'val']
            if a_ocf.empty or a_cap.empty or (end - fy_end).days > 300:
                out.append(dict(issuer=symbol, accn=accn, form=meta['form'], period_end=str(end.date()),
                                status='TTM_NOT_CONSTRUCTIBLE'))
                continue
            ttm_ocf = float(a_ocf.iloc[0]) + ocf - p_ocf
            ttm_capex = float(a_cap.iloc[0]) + capex - p_cap
            basis = 'prior annual + YTD - prior YTD'
        cash, _ = pick(f, CASH, accn, end)
        debt, debt_tag = pick(f, DEBT, accn, end)
        due, due_tag = pick(f, DEBT_CURRENT, accn, end)
        accepted = accepted_local(meta['acceptance'])
        gap = ttm_capex - ttm_ocf
        f1 = 'UNKNOWN' if not np.isfinite(debt) else ('FUNDING_WATCH' if gap > 0 and debt > 0 else 'NO_FLAG')
        if f1 == 'FUNDING_WATCH':
            f2 = 'UNKNOWN' if not np.isfinite(cash) else (
                'FUNDING_GAP' if cash < (due if np.isfinite(due) else 0) + gap else 'NO_FLAG')
        else:
            f2 = f1 if f1 == 'UNKNOWN' else 'NO_FLAG'
        reported = {t: pick(f, [t], accn, end)[0] for t in REPORTED_ONLY[:3]}
        reported.update({t: ytd(f, [t], accn, end)[0] for t in REPORTED_ONLY[3:]})
        out.append(dict(issuer=symbol, accn=accn, form=meta['form'], period_end=str(end.date()),
                        filing_date=meta['filing_date'], acceptance_local=accepted.isoformat(),
                        alarm_session=str(alarm_session(accepted, sessions).date()) if pd.notna(alarm_session(accepted, sessions)) else None,
                        ttm_basis=basis, ttm_ocf_usd=ttm_ocf, ttm_capex_usd=ttm_capex, capex_tag=cap_tag, ocf_tag=ocf_tag,
                        unrestricted_cash_usd=cash, debt_usd=debt, debt_tag=debt_tag,
                        debt_due_12m_usd=due, debt_due_tag=due_tag, F1=f1, F2=f2,
                        status='OK', **{'reported_' + k: v for k, v in reported.items()}))
    return out


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
