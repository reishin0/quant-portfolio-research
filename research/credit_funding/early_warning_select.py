"""Mechanical bond selection for early_warning_20261018 from saved FINRA metadata only.

Runs before any price, yield, spread, filing or equity outcome is retrieved.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/early_warning_20261018'
PROTOCOL = ROOT / 'research/credit_funding/early_warning_protocol_20261018.json'

# Names returned by word search that are not the equity issuer or a consolidated borrower,
# plus structures that are not unsecured straight issuer debt. Declared before outcomes.
EXCLUDED_NAME_PARTS = ['KEYBANK', 'PARAMOUNT BANCORP', 'PARAMOUNT BAPTIST', 'PARAMOUNT RES', 'SWEDISH EXPT',
    'KADISH', 'INTELSAT', 'INTELLIGENT PACKAGING', 'HAWAIIAN BRAND', 'INTERACTIVE INTELLIGENCE',
    'MILEAGE PLUS', 'OCCIDENTAL COLLEGE', 'CANADIAN OCCIDENTAL', 'PEAPACK', 'HF SINCLAIR', 'WIWYNN',
    'WYNNTON', 'AST SPACEMOBILE', 'FIAT CHRYSLER', 'STRATS TR', 'PASS THRU', 'PASS THROUGH',
    'ESCROW', 'INTERNOTES', 'MEDIUM TERM', 'MED TERM', 'CBS OUTDOOR']
# A name owned by another candidate in this universe never counts for this one.
FOREIGN_CANDIDATE = {'AES': ['CAESARS']}


def select():
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    out, ledger = {}, []
    for symbol in protocol['universe']['candidates']:
        m = pd.DataFrame(json.loads((DATA / (symbol + '_instruments.json')).read_text(encoding='utf-8')))
        if m.empty:
            out[symbol] = dict(legal_issuer=None, bonds=[], status='NOT_EVALUABLE_NO_INSTRUMENTS')
            continue
        m['mat'] = pd.to_datetime(m.maturityDate, errors='coerce')
        names = m.issuerName.fillna('')
        bad = names.map(lambda n: any(p in n for p in EXCLUDED_NAME_PARTS + FOREIGN_CANDIDATE.get(symbol, [])))
        e = m.loc[~bad & m.couponType.eq('FXPV') & m.isConvertible.eq('N') & m.mat.between('2028-01-01', '2036-12-31')
                  & m.couponRate.notna()].copy()
        # One economic issue per coupon/maturity. Amendment v2 (before outcomes): a CUSIP starting with a
        # letter is an international (CINS, normally Reg S) number; prefer registered, then 144A, then Reg S.
        e['twin_rank'] = e.cusip.str[0].str.isalpha().astype(int) * 2 + e.is144A.eq('Y').astype(int)
        e = e.sort_values(['twin_rank', 'cusip']).drop_duplicates(['issuerName', 'couponRate', 'maturityDate'])
        counts = e.groupby('issuerName').size().sort_index()
        conv = sorted(m.loc[~bad & m.isConvertible.eq('Y'), 'cusip'])
        if counts.empty or counts.max() < 2:
            out[symbol] = dict(legal_issuer=counts.idxmax() if len(counts) else None,
                               bonds=sorted(e.cusip)[:4], convertible_cusips=conv,
                               status='NOT_EVALUABLE_FEWER_THAN_TWO_STRAIGHT_BONDS')
            continue
        name = counts[counts == counts.max()].index[0]  # tie-break: alphabetical issuerName
        chosen = e.loc[e.issuerName.eq(name)].sort_values(['mat', 'cusip']).head(4)
        out[symbol] = dict(legal_issuer=name, bonds=chosen.cusip.tolist(),
                           callable=chosen.set_index('cusip').isCallable.to_dict(),
                           convertible_cusips=conv, other_eligible_names=counts.drop(name).to_dict(),
                           status='ELIGIBLE_ISSUER_CREDIT',
                           guarantee_collateral='UNVERIFIED; FINRA metadata has no guarantor or collateral fields')
    result = dict(selected_at=datetime.now(timezone.utc).isoformat(),
                  protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                  excluded_name_parts=EXCLUDED_NAME_PARTS, foreign_candidate=FOREIGN_CANDIDATE,
                  amendment_before_outcomes=('Retail note programs (Internotes, medium-term note books) and '
                      'pass-through/equipment trusts are excluded as separately documented or collateralized '
                      'programs; escrow issuers excluded. Ties on bond count break alphabetically by issuerName. '
                      'Selection v2 replaces v1 (retained as selection_superseded_v1.json) because v1 preferred Reg S CINS '
                      'twins, which rarely print in TRACE; the twin preference is registered, then 144A, then Reg S. '
                      'Currency is not a FINRA metadata field: TRACE corporate prices are treated as USD issues and '
                      'this remains an unverified assumption.'),
                  selection=out)
    target = DATA / 'selection.json'
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for s, c in out.items():
        print(s, c['status'], c['legal_issuer'], c['bonds'])


if __name__ == '__main__':
    select()
