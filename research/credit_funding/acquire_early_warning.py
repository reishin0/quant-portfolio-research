"""Acquire public evidence for the declared early-warning study (early_warning_20261018).

Network acquisition is separate from the offline notebook. Each stage writes into
data/early_warning_20261018/ and refuses to overwrite an existing file. Receipts record
URL, request, status, retrieval time and SHA-256; cookies and credentials are never saved.

Stages, in declared order (outcome data only after the selection is written):
  search    FINRA bondSearch per candidate (identifiers only)
  metadata  FINRA instrument terms for returned CUSIPs
  history   FINRA end-of-day last sale for selected bonds
  rates     FRED Treasury CMT, ICE BofA HY OAS and Moody's Baa-10y series
  equity    Yahoo adjusted daily closes for candidates and SPY
  sec       SEC submissions and XBRL company facts (needs SEC_USER_AGENT with a contact)
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import time
import pandas as pd
import requests
from research.credit_funding.fetch_bond_history import BASE

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / 'research/credit_funding/early_warning_protocol_20261018.json'
DATA = ROOT / 'data/early_warning_20261018'
FRED_SERIES = ['DGS1', 'DGS2', 'DGS3', 'DGS5', 'DGS7', 'DGS10', 'DGS20', 'DGS30',
               'BAMLH0A0HYM2', 'BAA10Y']
FINRA_HEADERS = {'Origin': 'https://www.finra.org',
                 'Referer': 'https://www.finra.org/finra-data/fixed-income/corp-and-agency/trade'}
META_FIELDS = ['cusip', 'issueSymbolIdentifier', 'issuerName', 'couponRate', 'maturityDate',
               'isCallable', 'isConvertible', 'is144A', 'couponType', 'productSubTypeCode']


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(raw)


def save_json(path, value):
    write_new(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))


def receipt(name, url, request, response, note):
    save_json(DATA / 'receipts' / (name + '.json'), dict(
        url=url, request=request, status=response.status_code, retrieved_at=now(),
        sha256=hashlib.sha256(response.content).hexdigest(), vintage=note))


def protocol():
    return json.loads(PROTOCOL.read_text(encoding='utf-8'))


class Finra:
    def __init__(self):
        self.s = requests.Session()
        self.s.get(BASE + '/CorporateAndAgencySecurities', timeout=40)
        if not self.s.cookies.get('XSRF-TOKEN'):
            raise RuntimeError('Public TRACE session unavailable; no workaround attempted')

    def post(self, dataset, payload, name):
        for attempt in range(4):
            r = self.s.post(BASE + '/' + dataset, json=payload, timeout=90,
                            headers=dict(FINRA_HEADERS, **{'X-XSRF-TOKEN': self.s.cookies.get('XSRF-TOKEN')}))
            if r.status_code not in (429, 500, 502, 503, 504):
                break
            time.sleep(5 * 2 ** attempt)
        write_new(DATA / 'raw' / (name + '.json'), r.content)
        receipt(name, BASE + '/' + dataset, payload, r, 'Current retrieval; historical delivery times unknown')
        r.raise_for_status()
        body = r.json()
        if body.get('status') != 'success':
            raise ValueError(body.get('statusMessage', 'TRACE request failed'))
        result = body['returnBody']
        rows = json.loads(result['data']) if isinstance(result['data'], str) else result['data']
        if len(rows or []) != int(result['headers']['Record-Total'][0]):
            raise ValueError('Truncated response; do not treat as complete: ' + name)
        time.sleep(0.4)
        return rows or []


def stage_search():
    f = Finra()
    for symbol, item in protocol()['universe']['candidates'].items():
        words = [w for w in item['bond_search'].replace('-', ' ').split() if w]
        rows = f.post('bondSearch', {
            'fields': ['cusip', 'issueSymbolIdentifier', 'issuerName', 'bondType'],
            'multiFieldMatchFilters': [{'searchValue': w, 'fuzzy': False, 'synonym': False,
                                        'fields': [{'name': 'issuerName', 'boost': 1}]} for w in words],
            'offset': 0, 'limit': 1000}, symbol + '_search')
        print(symbol, len(rows), sorted({r.get('issuerName') for r in rows})[:12], flush=True)


def stage_search2():
    f = Finra()
    terms = json.loads((DATA / 'search_amendment.json').read_text(encoding='utf-8'))['supplemental_terms']
    for symbol, phrases in terms.items():
        for k, phrase in enumerate(phrases):
            words = [w for w in phrase.replace('-', ' ').split() if w]
            rows = f.post('bondSearch', {
                'fields': ['cusip', 'issueSymbolIdentifier', 'issuerName', 'bondType'],
                'multiFieldMatchFilters': [{'searchValue': w, 'fuzzy': False, 'synonym': False,
                                            'fields': [{'name': 'issuerName', 'boost': 1}]} for w in words],
                'offset': 0, 'limit': 1000}, f'{symbol}_search_s{k}')
            print(symbol, phrase, len(rows), sorted({r.get('issuerName') for r in rows})[:12], flush=True)


def search_rows(symbol):
    found = []
    for path in sorted((DATA / 'raw').glob(symbol + '_search*.json')):
        body = json.loads(path.read_text(encoding='utf-8'))['returnBody']['data']
        found += (json.loads(body) if isinstance(body, str) else body) or []
    return found


def stage_metadata():
    f = Finra()
    for symbol in protocol()['universe']['candidates']:
        found = search_rows(symbol)
        cusips = sorted({r['cusip'] for r in found if r.get('cusip')})
        out = []
        for i in range(0, len(cusips), 200):
            out += f.post('corporateAndAgencySecurities', {
                'fields': META_FIELDS, 'domainFilters': [{'fieldName': 'cusip', 'values': cusips[i:i + 200]}],
                'offset': 0, 'limit': 1000}, f'{symbol}_metadata_{i // 200}')
        save_json(DATA / (symbol + '_instruments.json'), out)
        print(symbol, len(cusips), len(out), flush=True)


def stage_history():
    sel = json.loads((DATA / 'selection.json').read_text(encoding='utf-8'))
    start, end = protocol()['periods']['panel']
    years = range(int(start[:4]), int(end[:4]) + 1)
    f = Finra()
    for symbol, choice in sel['selection'].items():
        frames = []
        for cusip in choice['bonds']:
            for y in years:
                a, b = max(start, f'{y}-01-01'), min(end, f'{y}-12-31')
                rows = f.post('endOfDayPriceYield', {
                    'fields': ['tradeDate', 'cusip', 'lastSalePrice', 'lastSaleYield'],
                    'domainFilters': [{'fieldName': 'cusip', 'values': [cusip]}],
                    'dateRangeFilters': [{'fieldName': 'tradeDate', 'startDate': a, 'endDate': b}],
                    'sortFields': ['tradeDate'], 'offset': 0, 'limit': 5000}, f'{symbol}_{cusip}_{y}')
                frames.append(pd.DataFrame(rows, columns=['tradeDate', 'cusip', 'lastSalePrice', 'lastSaleYield']))
        if frames:
            panel = pd.concat(frames).sort_values(['tradeDate', 'cusip'])
            write_new(DATA / (symbol + '_bonds.csv'), panel.to_csv(index=False, lineterminator='\n').encode())
            print(symbol, len(panel), flush=True)


def stage_rates():
    for series in FRED_SERIES:
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
        r = requests.get(url, timeout=60)
        write_new(DATA / 'raw' / f'fred_{series}.csv', r.content)
        receipt('fred_' + series, url, None, r, 'FRED current vintage; ICE values published next business day')
        r.raise_for_status()
        print(series, len(r.content), flush=True)


def stage_equity():
    import yfinance as yf
    p = protocol()
    symbols = list(p['universe']['candidates']) + p['universe']['benchmarks']
    start, end = p['periods']['panel']
    end_excl = (pd.Timestamp(end) + pd.Timedelta(days=1)).date().isoformat()
    raw = yf.download(symbols, start=start, end=end_excl, auto_adjust=True, progress=False,
                      group_by='column', threads=False)
    close = raw['Close'][symbols]
    buf = close.to_csv(lineterminator='\n').encode()
    write_new(DATA / 'equity_adjusted.csv', buf)
    save_json(DATA / 'receipts' / 'equity.json', dict(
        source='Yahoo Finance via yfinance ' + yf.__version__, symbols=symbols, start=start,
        end_inclusive=end, auto_adjust=True, retrieved_at=now(),
        sha256=hashlib.sha256(buf).hexdigest(),
        vintage='Current adjusted history; split/dividend adjustments can change later'))
    print(close.shape, close.isna().sum().to_dict(), flush=True)


# Declared ticker-identity repair: Yahoo PARA now prices a different security; Paramount trades as PSKY.
EXTRA_RETRY = ['PSKY']


def stage_equity_retry():
    """One retry for symbols the combined download returned empty; never splices other sources."""
    import yfinance as yf
    p = protocol()
    start, end = p['periods']['panel']
    end_excl = (pd.Timestamp(end) + pd.Timedelta(days=1)).date().isoformat()
    base = pd.read_csv(DATA / 'equity_adjusted.csv', index_col=0)
    for symbol in [c for c in base if base[c].isna().all() or base[c].notna().sum() < 5] + EXTRA_RETRY:
        raw = yf.download(symbol, start=start, end=end_excl, auto_adjust=True, progress=False, threads=False)
        close = raw['Close'] if len(raw) else pd.DataFrame()
        buf = close.to_csv(lineterminator='\n').encode()
        write_new(DATA / f'equity_retry_{symbol}.csv', buf)
        save_json(DATA / 'receipts' / f'equity_retry_{symbol}.json', dict(
            source='Yahoo Finance via yfinance ' + yf.__version__, symbol=symbol, retrieved_at=now(),
            rows=int(len(close)), sha256=hashlib.sha256(buf).hexdigest()))
        print(symbol, len(close), flush=True)


def stage_sec():
    agent = os.environ.get('SEC_USER_AGENT')
    if not agent or '@' not in agent:
        raise RuntimeError('SEC requires a declared contact; set SEC_USER_AGENT')
    s = requests.Session()
    s.headers['User-Agent'] = agent
    tickers = s.get('https://www.sec.gov/files/company_tickers.json', timeout=60)
    write_new(DATA / 'raw' / 'sec_company_tickers.json', tickers.content)
    receipt('sec_company_tickers', tickers.url, None, tickers, 'Current SEC ticker map')
    tickers.raise_for_status()
    cik = {v['ticker']: int(v['cik_str']) for v in tickers.json().values()}
    for symbol in protocol()['universe']['candidates']:
        if symbol not in cik:
            print(symbol, 'NO_CIK', flush=True)
            continue
        for kind, url in [('submissions', f'https://data.sec.gov/submissions/CIK{cik[symbol]:010d}.json'),
                          ('facts', f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik[symbol]:010d}.json')]:
            r = s.get(url, timeout=90)
            write_new(DATA / 'raw' / f'sec_{symbol}_{kind}.json', r.content)
            receipt(f'sec_{symbol}_{kind}', url, None, r, 'Current SEC vintage; acceptanceDateTime from submissions')
            r.raise_for_status()
            time.sleep(0.25)
            data = r.json()
            # Older filings are paged into separate files; fetch them so 2021+ coverage is complete.
            for extra in (data.get('filings', {}).get('files', []) if kind == 'submissions' else []):
                u = 'https://data.sec.gov/submissions/' + extra['name']
                rx = s.get(u, timeout=90)
                write_new(DATA / 'raw' / f"sec_{symbol}_{extra['name']}", rx.content)
                receipt(f"sec_{symbol}_{extra['name']}", u, None, rx, 'Current SEC vintage')
                rx.raise_for_status()
                time.sleep(0.25)
        print(symbol, cik[symbol], flush=True)


def stage_manifest():
    """Pin every file. Large SEC raw downloads stay local (gitignored) and are pinned separately."""
    files = sorted(p for p in DATA.rglob('*') if p.is_file() and p.name != 'manifest.json')
    local = [p for p in files if p.parent.name == 'raw' and p.name.startswith('sec_')]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(created_at=now(), protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                    file_sha256={p.relative_to(DATA).as_posix(): digest(p) for p in files if p not in local},
                    local_raw_sha256={p.relative_to(DATA).as_posix(): digest(p) for p in local},
                    note='local_raw_sha256 files are verified when present; filings.json is the committed extract')
    save_json(DATA / 'manifest.json', manifest)
    print(len(files), 'files pinned;', len(local), 'local-only')


if __name__ == '__main__':
    stages = dict(search=stage_search, search2=stage_search2, metadata=stage_metadata, history=stage_history, rates=stage_rates,
                  equity=stage_equity, equity_retry=stage_equity_retry, sec=stage_sec, manifest=stage_manifest)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stage', choices=stages)
    stages[parser.parse_args().stage]()
