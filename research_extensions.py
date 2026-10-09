"""Validated extensions for the maintained portfolio-construction study.

All return inputs use decimal units: 0.01 means one percent. Functions reject
ambiguous factor units and return labelled pandas objects for auditability.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import kurtosis, skew

PERIODS_PER_YEAR = 252
FACTOR_COLUMNS = ['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA']


def _numeric_frame(frame, name, minimum_rows=24):
    if not isinstance(frame, pd.DataFrame) or len(frame) < minimum_rows:
        raise ValueError(f'{name} must be a DataFrame with at least {minimum_rows} rows.')
    result = frame.apply(pd.to_numeric, errors='raise').copy()
    if result.index.has_duplicates:
        raise ValueError(f'{name} has duplicate dates.')
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError(f'{name} must contain finite values.')
    return result.sort_index()


def monthly_compound(daily_returns, trim_boundary_months=True):
    """Compound daily returns; conservatively exclude both boundary months.

    A return-only series cannot prove complete first/last month coverage. Trimming
    prevents partial periods being regressed against full-month factor returns.
    Set False only when complete coverage has been independently established.
    """
    daily = _numeric_frame(daily_returns, 'daily_returns', minimum_rows=40)
    if not isinstance(daily.index, pd.DatetimeIndex):
        raise ValueError('daily_returns must use a DatetimeIndex.')
    periods = daily.index.to_period('M')
    monthly = (1 + daily).groupby(periods).prod() - 1
    if trim_boundary_months:
        monthly = monthly.iloc[1:-1]
    monthly.index = monthly.index.to_timestamp('M')
    return monthly


def load_fama_french_csv(path, unit='percent'):
    """Load a cleaned monthly Fama-French five-factor CSV with explicit units."""
    if unit not in {'percent', 'decimal'}:
        raise ValueError('unit must be "percent" or "decimal".')
    frame = pd.read_csv(Path(path))
    date_column = frame.columns[0]
    dates = frame[date_column].astype(str).str.strip()
    valid = dates.str.fullmatch(r'\d{6}')
    if not valid.all():
        raise ValueError('Cleaned factor file must contain only YYYYMM monthly rows.')
    frame = frame.loc[valid].copy()
    frame.index = pd.to_datetime(dates.loc[valid], format='%Y%m') + pd.offsets.MonthEnd(0)
    required = FACTOR_COLUMNS + ['RF']
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f'Factor file is missing columns: {sorted(missing)}')
    frame = _numeric_frame(frame[required], 'factor file')
    if unit == 'percent':
        frame /= 100
    if frame.abs().max().max() >= 1:
        raise ValueError('Factor values are implausible decimal returns; check the unit setting.')
    frame.attrs['source_unit'] = unit
    frame.attrs['stored_unit'] = 'decimal'
    return frame


def factor_regression(monthly_asset_returns, monthly_factors):
    """OLS excess-return regressions on the Fama-French five factors.

    Both inputs must already be decimals. The output reports annualized alpha,
    factor loadings, coefficient t-statistics, R-squared and observation count.
    """
    assets = _numeric_frame(monthly_asset_returns, 'monthly_asset_returns')
    factors = _numeric_frame(monthly_factors, 'monthly_factors')
    required = FACTOR_COLUMNS + ['RF']
    if not set(required).issubset(factors.columns):
        raise ValueError(f'monthly_factors requires {required}.')
    joined = assets.join(factors[required], how='inner').dropna()
    if len(joined) < 24:
        raise ValueError('Too few aligned months for factor regression; at least 24 required.')
    x = np.column_stack([np.ones(len(joined)), joined[FACTOR_COLUMNS].to_numpy()])
    if np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError('Factor design matrix is rank deficient.')
    xtx_inverse = np.linalg.pinv(x.T @ x)
    rows = []
    for asset in assets.columns:
        y = (joined[asset] - joined['RF']).to_numpy()
        coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
        residuals = y - x @ coefficients
        dof = len(y) - x.shape[1]
        residual_variance = float(residuals @ residuals / dof)
        standard_errors = np.sqrt(np.diag(xtx_inverse) * residual_variance)
        t_stats = np.divide(coefficients, standard_errors,
                            out=np.full_like(coefficients, np.nan), where=standard_errors > 0)
        total = float(((y - y.mean()) ** 2).sum())
        r_squared = 1 - float(residuals @ residuals) / total if total > 0 else np.nan
        row = {'Portfolio': asset, 'Annual alpha': coefficients[0] * 12,
               'Alpha t-stat': t_stats[0], 'R-squared': r_squared,
               'Observations': len(y),
               'First month': str(joined.index.min().date()),
               'Last month': str(joined.index.max().date())}
        for number, factor in enumerate(FACTOR_COLUMNS, start=1):
            row[f'{factor} loading'] = coefficients[number]
            row[f'{factor} t-stat'] = t_stats[number]
        rows.append(row)
    return pd.DataFrame(rows).set_index('Portfolio')


def higher_moment_weights(returns, cap=0.35, risk_aversion=3.0,
                          skew_preference=0.02, kurtosis_penalty=0.005):
    """Long-only weights maximizing a stated mean/variance/skew/kurtosis utility."""
    data = _numeric_frame(returns, 'returns', minimum_rows=252)
    n = data.shape[1]
    if not 1 / n <= cap <= 1:
        raise ValueError(f'cap must be between {1/n:.3f} and 1.')
    if min(risk_aversion, skew_preference, kurtosis_penalty) < 0:
        raise ValueError('Higher-moment preferences must be nonnegative.')
    matrix = data.to_numpy()

    def negative_utility(weights):
        series = matrix @ weights
        mean = series.mean() * PERIODS_PER_YEAR
        variance = series.var(ddof=1) * PERIODS_PER_YEAR
        utility = (mean - 0.5 * risk_aversion * variance
                   + skew_preference * skew(series, bias=False)
                   - kurtosis_penalty * kurtosis(series, fisher=True, bias=False))
        return -float(utility)

    equal = np.full(n, 1 / n)
    result = minimize(negative_utility, equal, method='SLSQP', bounds=[(0, cap)] * n,
                      constraints=[{'type': 'eq', 'fun': lambda weights: weights.sum() - 1}],
                      options={'ftol': 1e-12, 'maxiter': 1000})
    if not result.success:
        raise RuntimeError(f'Higher-moment optimization failed: {result.message}')
    return pd.Series(result.x, index=data.columns, name='Higher-moment utility')


def fractional_kelly_weights(returns, annual_rf=0.03, fraction=0.5, cap=0.35):
    """Solve capped, unlevered full Kelly with cash, then scale risky weights.

    The fraction is a multiplier of that constrained full-Kelly solution, not
    a required risky exposure. Negative opportunities may leave all wealth cash.
    The cap applies to full Kelly before scaling.
    """
    data = _numeric_frame(returns, 'returns', minimum_rows=252)
    n = data.shape[1]
    if not 0 < fraction <= 1:
        raise ValueError('fraction must be in (0, 1].')
    if not np.isfinite(cap) or not 0 < cap <= 1:
        raise ValueError('cap must be in (0, 1].')
    if not np.isfinite(annual_rf) or annual_rf <= -1:
        raise ValueError('annual_rf must be finite and greater than -1.')
    daily_rf = (1 + annual_rf) ** (1 / PERIODS_PER_YEAR) - 1
    matrix = data.to_numpy()

    def negative_log_growth(weights):
        gross = 1 + matrix @ weights + (1 - weights.sum()) * daily_rf
        return np.inf if (gross <= 0).any() else -float(np.log(gross).mean())

    start = np.zeros(n)
    result = minimize(negative_log_growth, start, method='SLSQP',
                      bounds=[(0, cap)] * n,
                      constraints=[{'type': 'ineq', 'fun': lambda weights: 1 - weights.sum()}],
                      options={'ftol': 1e-12, 'maxiter': 1000})
    if (not result.success or not np.isfinite(result.x).all()
            or result.x.min() < -1e-7 or result.x.max() > cap + 1e-7
            or result.x.sum() > 1 + 1e-7 or not np.isfinite(result.fun)):
        raise RuntimeError(f'Fractional Kelly optimization failed: {result.message}')
    return pd.Series(result.x * fraction, index=data.columns, name='Fractional Kelly')


def bab_weights(asset_returns, benchmark_returns, gross_limit=2.0):
    """Construct beta-neutral low-minus-high beta weights with bounded gross exposure."""
    assets = _numeric_frame(asset_returns, 'asset_returns', minimum_rows=252)
    benchmark = pd.Series(benchmark_returns, copy=True).reindex(assets.index)
    if benchmark.isna().any() or not np.isfinite(benchmark.to_numpy()).all():
        raise ValueError('benchmark_returns must be finite and aligned with asset_returns.')
    if gross_limit <= 0:
        raise ValueError('gross_limit must be positive.')
    benchmark_variance = benchmark.var(ddof=1)
    if benchmark_variance <= 0:
        raise ValueError('benchmark_returns must have positive variance.')
    betas = assets.apply(lambda column: column.cov(benchmark) / benchmark_variance)
    ordered = betas.sort_values()
    half = len(ordered) // 2
    low_names, high_names = ordered.index[:half], ordered.index[-half:]
    low_beta, high_beta = betas[low_names].mean(), betas[high_names].mean()
    if low_beta <= 0.05 or high_beta <= 0.05:
        raise ValueError('BAB construction requires positive average beta in both legs.')
    raw = pd.Series(0.0, index=assets.columns)
    raw.loc[low_names] = 1 / (len(low_names) * low_beta)
    raw.loc[high_names] = -1 / (len(high_names) * high_beta)
    weights = raw * (gross_limit / raw.abs().sum())
    diagnostics = pd.DataFrame({'Beta': betas, 'Weight': weights,
                                'Leg': np.where(weights > 0, 'Low-beta long', 'High-beta short')})
    diagnostics.attrs['portfolio_beta'] = float(weights @ betas)
    diagnostics.attrs['gross_exposure'] = float(weights.abs().sum())
    return weights.rename('BAB beta-neutral'), diagnostics.sort_values('Beta')
