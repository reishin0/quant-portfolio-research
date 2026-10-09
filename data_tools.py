"""Frozen input integrity, exchange-session checks and realized cash proxies."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


def load_price_snapshot(path, symbols, start, end):
    """Read a provider snapshot only after verifying its immutable manifest."""
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    price_path = manifest_path.parent / manifest['price_file']
    if hashlib.sha256(price_path.read_bytes()).hexdigest() != manifest['price_sha256']:
        raise ValueError('Price snapshot hash mismatch.')
    actions_path = manifest_path.parent / manifest['actions_file']
    if hashlib.sha256(actions_path.read_bytes()).hexdigest() != manifest['actions_sha256']:
        raise ValueError('Corporate-action snapshot hash mismatch.')
    prices = pd.read_csv(price_path, index_col=0, parse_dates=True, float_precision='round_trip')
    if (list(prices.columns) != manifest['symbols'] or len(prices) != manifest['rows']
            or str(prices.index.min().date()) != manifest['first_price']
            or str(prices.index.max().date()) != manifest['last_price']):
        raise ValueError('Price snapshot schema or coverage differs from its manifest.')
    if (pd.Timestamp(start) < pd.Timestamp(manifest['requested_start'])
            or pd.Timestamp(end) > pd.Timestamp(manifest['requested_end_exclusive'])):
        raise ValueError('Requested dates exceed the frozen snapshot; explicitly refresh Yahoo inputs.')
    if not set(symbols).issubset(prices.columns):
        raise ValueError('Snapshot does not cover the requested symbols.')
    selected = prices.loc[(prices.index >= pd.Timestamp(start)) & (prices.index < pd.Timestamp(end)), symbols]
    return selected, manifest


def audit_prices(prices, start, end, actions=None, calendar='NYSE', jump_threshold=.10):
    """Reject missing sessions/quotes; flag large adjusted moves for review, never repair them."""
    if (not isinstance(prices.index, pd.DatetimeIndex) or prices.index.has_duplicates
            or not prices.index.is_monotonic_increasing or prices.columns.has_duplicates
            or prices.empty or not np.isfinite(prices.to_numpy()).all()
            or (prices <= 0).any().any()):
        raise ValueError('Price audit requires ordered unique dates and finite positive quotes.')
    if calendar:
        import pandas_market_calendars as mcal
        expected = mcal.get_calendar(calendar).valid_days(
            start_date=start, end_date=pd.Timestamp(end) - pd.Timedelta(days=1)).tz_localize(None)
    else:
        expected = pd.bdate_range(start, end, inclusive='left')
    missing, extra = expected.difference(prices.index), prices.index.difference(expected)
    if len(missing) or len(extra):
        raise ValueError(f'Exchange-session mismatch: missing={list(missing.date)}, unexpected={list(extra.date)}')
    returns = prices.pct_change(fill_method=None)
    flags = returns.where(returns.abs() > jump_threshold).stack().rename('Adjusted return').to_frame()
    flags.index.names = ['Date', 'ETF']
    flags['Corporate action'] = ''
    if actions is not None:
        required = {'Date', 'ETF', 'Action', 'Value'}
        if not required.issubset(actions.columns):
            raise ValueError('Corporate actions require Date, ETF, Action, Value.')
        for date, symbol in flags.index:
            related = actions.loc[(pd.to_datetime(actions['Date']) == date) & (actions['ETF'] == symbol)]
            flags.loc[(date, symbol), 'Corporate action'] = '; '.join(
                f'{r.Action}={r.Value}' for r in related.itertuples())
    coverage = pd.DataFrame({'Observations': prices.count(), 'Missing quotes': prices.isna().sum(),
                             'Flagged moves': [(flags.index.get_level_values('ETF') == s).sum() for s in prices]})
    return coverage, flags


def load_sofr_cash_returns(price_dates, manifest_path='data/sofr_provenance_20261009.json'):
    """Realized ACT/360 overnight proxy, aligned to close-to-close calendar intervals.

    SOFR is observed in arrears and may be revised. It is never a forecast input.
    Simple interest accrues across each quoted overnight period (including weekends).
    The close-to-close application is an explicit accounting approximation.
    """
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    path = manifest_path.parent / manifest['file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('SOFR snapshot hash mismatch.')
    data = pd.read_csv(path, na_values=['.'])
    rates = pd.Series(pd.to_numeric(data['SOFR']).to_numpy() / 100,
                      index=pd.to_datetime(data.iloc[:, 0])).dropna().sort_index()
    dates = pd.DatetimeIndex(price_dates)
    if (len(dates) < 2 or dates.has_duplicates or not dates.is_monotonic_increasing
            or rates.index.has_duplicates or not np.isfinite(rates).all()
            or (rates < 0).any() or rates.index.min() > dates.min()
            or (dates.max() - rates.index.max()).days > 4
            or rates.index.to_series().diff().dt.days.max() > 7):
        raise ValueError('SOFR coverage, dates or rates are invalid; no constant-rate fallback.')
    levels = pd.Series(index=pd.date_range(rates.index.min(), dates.max(), freq='D'), dtype=float)
    wealth = 1.0
    for i, (date, rate) in enumerate(rates.items()):
        if date > dates.max():
            break
        stop = min(rates.index[i + 1] if i + 1 < len(rates) else dates.max(), dates.max())
        interval = pd.date_range(date, stop, freq='D')
        values = wealth * (1 + rate * (interval - date).days.to_numpy() / 360)
        levels.loc[interval] = values
        wealth = values[-1]
    selected = levels.reindex(dates)
    if selected.isna().any():
        raise ValueError('SOFR cannot cover every price interval.')
    result = selected.pct_change(fill_method=None).iloc[1:].rename('SOFR realized cash proxy')
    return result, manifest
