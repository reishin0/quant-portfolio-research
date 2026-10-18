"""Acquire public evidence for the declared 2026 issuer comparison.

Network acquisition is separate from the offline notebook. Never updates a frozen
snapshot. Request receipts exclude session cookies and credentials.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import requests
from research.credit_funding.fetch_bond_history import BASE

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/issuer_study_20261018'


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def query(session, dataset, payload, name):
    target = DATA / (name + '_response.json')
    if target.exists():
        raise FileExistsError(target)
    response = session.post(BASE + '/' + dataset, json=payload, timeout=60,
        headers={'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN'),
                 'Origin': 'https://www.finra.org',
                 'Referer': 'https://www.finra.org/finra-data/fixed-income/corp-and-agency/trade'})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    save_json(DATA / (name + '_request.json'), {
        'url': BASE + '/' + dataset, 'request': payload, 'status': response.status_code,
        'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'sha256': hashlib.sha256(response.content).hexdigest(),
        'vintage': 'Current retrieval; historical delivery times unknown'})
    response.raise_for_status()
    body = response.json()
    if body.get('status') != 'success':
        raise ValueError(body.get('statusMessage', 'TRACE request failed'))
    result = body['returnBody']
    rows = json.loads(result['data']) if isinstance(result['data'], str) else result['data']
    if len(rows) != int(result['headers']['Record-Total'][0]):
        raise ValueError('Truncated response; do not treat as complete')
    return rows


def session():
    s = requests.Session()
    s.get(BASE + '/CorporateAndAgencySecurities', timeout=40)
    if not s.cookies.get('XSRF-TOKEN'):
        raise RuntimeError('Public TRACE session unavailable')
    return s


def discover():
    terms = {'APLD': 'APLD', 'IREN': 'IREN', 'NBIS': 'NEBIUS',
             'CORZ': 'CORE SCIENTIFIC', 'ORCL': 'ORACLE', 'EQIX': 'EQUINIX'}
    with session() as s:
        for symbol, term in terms.items():
            rows = query(s, 'bondSearch', {
                'fields': ['cusip', 'issueSymbolIdentifier', 'issuerName', 'bondType'],
                'multiFieldMatchFilters': [{'searchValue': word, 'fuzzy': False, 'synonym': False,
                                 'fields': [{'name': 'issuerName', 'boost': 1}]}
                                for word in term.split()], 'offset': 0, 'limit': 1000},
                symbol + '_search_v2')
            save_json(DATA / (symbol + '_search.json'), rows)
            print(symbol, len(rows), flush=True)


if __name__ == '__main__':
    discover()
