"""Read the frozen submission inputs without positional series selection."""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / 'data'
INFLATION_SERIES = {
    'HCPI_GLOBAL_MED': 'Median',
    'HCPI_GLOBAL_AVE': 'Average',
    'HCPI_GLOBAL_AVE_GDP': 'GDP-weighted average',
}
BIS_SERIES = dict(FREQ='Q', CURR_DENOM='TO1', BORROWERS_CTY='5J',
                  BORROWERS_SECTOR='A', LENDERS_SECTOR='B', L_POS_TYPE='I',
                  L_INSTR='A', UNIT_MEASURE='770', UNIT_MULT='0')


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_submission_files(root=None):
    """Verify imported bytes against the checked-in provenance manifest."""
    root = Path(root) if root else DATA_DIR.parent
    manifest = json.loads((root / 'data/manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = root / item['path']
        if not path.is_file() or file_sha256(path) != item['sha256']:
            raise ValueError(f'Submission file missing or changed: {item["path"]}')
    return manifest


def load_submission_prices(path=None, symbols=None, start=None, end=None):
    """Pivot genuine adjusted closes, rejecting duplicate keys and invalid prices.

    Market Cap is a repeated snapshot, not historical market weights. It is never
    used here. A requested end is exclusive. Missing observations stay missing.
    """
    path = Path(path) if path else DATA_DIR / 'efts_dataset.csv'
    raw = pd.read_csv(path)
    required = {'Date', 'ETF', 'Adj Close'}
    if not required.issubset(raw.columns):
        raise ValueError(f'ETF cache requires columns {sorted(required)}.')
    if raw[list(required)].isna().any().any():
        raise ValueError('ETF cache contains missing keys or adjusted prices.')
    raw['Date'] = pd.to_datetime(raw['Date'], errors='raise')
    if raw.duplicated(['Date', 'ETF']).any():
        raise ValueError('ETF cache contains duplicate (Date, ETF) observations.')
    raw['Adj Close'] = pd.to_numeric(raw['Adj Close'], errors='raise')
    if not np.isfinite(raw['Adj Close']).all() or (raw['Adj Close'] <= 0).any():
        raise ValueError('Adjusted prices must be finite and positive.')
    prices = raw.pivot(index='Date', columns='ETF', values='Adj Close').sort_index()
    if symbols is not None:
        missing = set(symbols) - set(prices.columns)
        if missing:
            raise ValueError(f'ETF cache is missing symbols: {sorted(missing)}')
        prices = prices.loc[:, list(symbols)]
    if start is not None:
        prices = prices.loc[prices.index >= pd.Timestamp(start)]
    if end is not None:
        prices = prices.loc[prices.index < pd.Timestamp(end)]
    if prices.empty:
        raise ValueError('No submission prices in the requested date range.')
    prices.columns.name = None
    return prices


def load_inflation(path=None):
    """Global annual CPI rates in percentage points, selected by Series Name."""
    path = Path(path) if path else DATA_DIR / 'Inflation-data.xlsx'
    raw = pd.read_excel(path, sheet_name='Aggregate', engine='openpyxl')
    if 'Series Name' not in raw:
        raise ValueError('Inflation Aggregate sheet requires Series Name.')
    selected = raw.loc[raw['Series Name'].isin(INFLATION_SERIES)]
    if len(selected) != 3 or selected['Series Name'].duplicated().any():
        raise ValueError('Inflation file must contain each global CPI series exactly once.')
    years = [c for c in raw if re.fullmatch(r'\d{4}', str(c))]
    if not years:
        raise ValueError('Inflation file has no annual observation columns.')
    result = selected.set_index('Series Name')[years].T.rename(columns=INFLATION_SERIES)
    result.index = pd.Index([int(y) for y in years], name='Year')
    result = result.apply(pd.to_numeric, errors='raise').sort_index()
    if np.isinf(result.to_numpy()).any():
        raise ValueError('Inflation contains infinite values.')
    result.attrs.update(unit='percent per year', sha256=file_sha256(path))
    return result


def load_liquidity(path=None):
    """BIS bank credit as percent of GDP, selected by its full economic key."""
    path = Path(path) if path else DATA_DIR / 'WS_GLI_csv_col.csv'
    raw = pd.read_csv(path, dtype=str)
    missing = set(BIS_SERIES) - set(raw.columns)
    if missing:
        raise ValueError(f'BIS file lacks series metadata: {sorted(missing)}')
    mask = pd.Series(True, index=raw.index)
    for key, value in BIS_SERIES.items():
        mask &= raw[key].str.strip().eq(value)
    selected = raw.loc[mask]
    if len(selected) != 1:
        raise ValueError(f'BIS economic key must match exactly one series, found {len(selected)}.')
    quarters = [c for c in raw if re.fullmatch(r'\d{4}-Q[1-4]', c)]
    if not quarters:
        raise ValueError('BIS file has no quarterly observation columns.')
    values = pd.to_numeric(selected.iloc[0][quarters], errors='raise')
    result = pd.Series(values.to_numpy(dtype=float),
                       index=pd.PeriodIndex(quarters, freq='Q'), name='Bank credit (% of GDP)').sort_index()
    if np.isinf(result.to_numpy()).any() or result.notna().sum() == 0:
        raise ValueError('BIS observations must contain finite data.')
    result.index.name = 'Quarter'
    result.attrs.update(unit='percent of GDP', series_key=BIS_SERIES, sha256=file_sha256(path))
    return result
