"""Download a bounded public TRACE panel into a NEW directory.

Example: python -m research.credit_funding.fetch_bond_history NEW_DIRECTORY \
    --cusips 21873SAB4 21873SAC2 --start 2026-01-01 --end 2026-10-16
The public schema was checked using OpenBB's FINRA provider on 2026-10-17:
https://github.com/OpenBB-finance/OpenBB/tree/develop/openbb_platform/providers/finra
This fetch is current-vintage EOD data, not point-in-time OAS or a complete case.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import pandas as pd
import requests
from research.credit_funding.issuer_replay import iso_date, bond_diagnostics

BASE = 'https://services-dynarep.ddwa.finra.org/public/reporting/v2/data/group/FixedIncomeMarket/name'


def fetch(directory, cusips, start_date, end_date):
    if not cusips or len(cusips)!=len(set(cusips)) or any(not isinstance(c,str) or not re.fullmatch(r'[A-Z0-9]{9}',c) for c in cusips):
        raise ValueError('Provide distinct nine-character CUSIPs')
    if iso_date(start_date)>iso_date(end_date):
        raise ValueError('Start date must precede end date')
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    payload = dict(fields=['tradeDate','cusip','issueSymbolIdentifier','lastSalePrice','lastSaleYield'],
                   domainFilters=[dict(fieldName='cusip',values=cusips)],
                   dateRangeFilters=[dict(fieldName='tradeDate',startDate=start_date,endDate=end_date)],
                   sortFields=['tradeDate'], offset=0, limit=5000)
    with requests.Session() as session:
        bootstrap = session.get(BASE+'/CorporateAndAgencySecurities', timeout=40)
        token = session.cookies.get('XSRF-TOKEN')
        if not token:
            raise RuntimeError('Public TRACE session unavailable; no access workaround attempted')
        response = session.post(BASE+'/endOfDayPriceYield', json=payload, timeout=60,
                                headers={'X-XSRF-TOKEN':token,'Origin':'https://www.finra.org',
                                         'Referer':'https://www.finra.org/finra-data/fixed-income/corp-and-agency/trade'})
    raw = response.content
    (target/'finra_response.json').write_bytes(raw)
    receipt = dict(url=BASE+'/endOfDayPriceYield', request=payload, status=response.status_code,
                   bootstrap_status=bootstrap.status_code, retrieved_at=datetime.now(timezone.utc).isoformat(),
                   sha256=hashlib.sha256(raw).hexdigest(), vintage='current; no historical receipt timestamps')
    (target/'finra_request.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    response.raise_for_status()
    body = response.json()
    if body.get('status') != 'success':
        raise RuntimeError('TRACE rejected request')
    returned = body['returnBody']
    rows = json.loads(returned['data']) if isinstance(returned['data'],str) else returned['data']
    total = int(returned['headers']['Record-Total'][0])
    if not isinstance(rows,list) or len(rows)!=total or total==0:
        raise RuntimeError('Empty or truncated response; narrow request dates; no completed panel written')
    frame = pd.DataFrame(rows)
    # Structural validation only; issuer ownership must be verified in the case metadata.
    bond_diagnostics(frame,dict(issuer='UNVERIFIED_FETCH',bonds=cusips,bond_window=[start_date,end_date],
                               history=20,persistence=3,max_gap_calendar_days=4,min_warning_bonds=1,widening_bp=100.))
    frame.sort_values(['tradeDate','cusip']).to_csv(target/'bond_daily.csv',index=False)
    print(f'Retained {len(rows)} current-vintage observations in {target}; issuer ownership not yet qualified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_directory')
    parser.add_argument('--cusips',nargs='+',required=True)
    parser.add_argument('--start',required=True)
    parser.add_argument('--end',required=True)
    args=parser.parse_args()
    fetch(args.new_directory,args.cusips,args.start,args.end)
