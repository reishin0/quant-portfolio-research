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


def factor_regression(monthly_asset_returns, monthly_factors, hac_lags=3):
    """OLS excess-return regressions on the Fama-French five factors.

    Both inputs must already be decimals. The output reports annualized alpha,
    factor loadings, IID t-statistics, Bartlett HAC uncertainty with Holm-adjusted
    alpha p-values, R-squared and observation count.
    """
    assets = _numeric_frame(monthly_asset_returns, 'monthly_asset_returns')
    factors = _numeric_frame(monthly_factors, 'monthly_factors')
    required = FACTOR_COLUMNS + ['RF']
    if not set(required).issubset(factors.columns):
        raise ValueError(f'monthly_factors requires {required}.')
    joined = assets.join(factors[required], how='inner').dropna()
    if len(joined) < 24:
        raise ValueError('Too few aligned months for factor regression; at least 24 required.')
    if not isinstance(hac_lags, int) or not 0 <= hac_lags < len(joined):
        raise ValueError('HAC lags must be a nonnegative integer below the sample size.')
    if not joined.index.to_period('M').equals(pd.period_range(joined.index[0], joined.index[-1], freq='M')):
        raise ValueError('HAC attribution requires contiguous monthly observations.')
    import statsmodels.api as sm
    from statsmodels.stats.sandwich_covariance import cov_hac
    from scipy.stats import norm
    x = np.column_stack([np.ones(len(joined)), joined[FACTOR_COLUMNS].to_numpy()])
    if np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError('Factor design matrix is rank deficient.')
    xtx_inverse = np.linalg.pinv(x.T @ x)
    rows = []
    for asset in assets.columns:
        y = (joined[asset] - joined['RF']).to_numpy()
        coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
        robust_covariance = cov_hac(sm.OLS(y, x).fit(), nlags=hac_lags, use_correction=True)
        robust_se = np.sqrt(np.maximum(np.diag(robust_covariance), 0))
        robust_z = np.divide(coefficients, robust_se, out=np.full_like(coefficients, np.nan), where=robust_se > 1e-14)
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
        row.update({'Annual alpha HAC SE': robust_se[0] * 12,
                    'Alpha HAC z': robust_z[0], 'Alpha HAC p': 2 * norm.sf(abs(robust_z[0])),
                    'Alpha HAC 95% lower': (coefficients[0] - 1.96 * robust_se[0]) * 12,
                    'Alpha HAC 95% upper': (coefficients[0] + 1.96 * robust_se[0]) * 12,
                    'HAC lags': hac_lags})
        for number, factor in enumerate(FACTOR_COLUMNS, start=1):
            row[f'{factor} loading'] = coefficients[number]
            row[f'{factor} t-stat'] = t_stats[number]
            row[f'{factor} HAC SE'] = robust_se[number]
            row[f'{factor} HAC z'] = robust_z[number]
        rows.append(row)
    table = pd.DataFrame(rows).set_index('Portfolio')
    # Holm controls the alpha-test family across displayed portfolios, not all research choices.
    from statsmodels.stats.multitest import multipletests
    valid = table['Alpha HAC p'].notna()
    table['Alpha HAC Holm p'] = np.nan
    if valid.any():
        table.loc[valid, 'Alpha HAC Holm p'] = multipletests(table.loc[valid, 'Alpha HAC p'], method='holm')[1]
    return table


def estimate_covariance(returns, estimator='sample'):
    """Annual covariance from the supplied prior window; shrinkage uses Ledoit-Wolf.

    The shrinkage estimator uses its ML (n) scaling; sample covariance uses n-1.
    Report that convention rather than silently modifying the library estimator.
    """
    data = _numeric_frame(returns, 'covariance returns', minimum_rows=24)
    if estimator == 'sample':
        covariance, shrinkage = data.cov() * 252, 0.0
    elif estimator == 'ledoit_wolf':
        from sklearn.covariance import LedoitWolf
        fit = LedoitWolf().fit(data.to_numpy())
        covariance = pd.DataFrame(fit.covariance_ * 252, index=data.columns, columns=data.columns)
        shrinkage = float(fit.shrinkage_)
    else:
        raise ValueError('Covariance estimator must be sample or ledoit_wolf.')
    covariance.attrs['shrinkage'] = shrinkage
    return covariance


def validate_view_register(register, symbols):
    """Validate explicitly sourced annual ETF relative-return view sets.

    Disabled qualitative records may have missing numerical/validity fields. Enabled
    sets require a 12-month arithmetic total-return spread and declared model confidence.
    """
    if not isinstance(register, list):
        raise ValueError('View register must be a list of dated view sets.')
    ids, publications = set(), set()
    for record in register:
        if not isinstance(record, dict) or not isinstance(record.get('id'), str) or record['id'] in ids:
            raise ValueError('View-set IDs must be unique strings.')
        ids.add(record['id'])
        if type(record.get('enabled')) is not bool:
            raise ValueError('View-set enabled must be a boolean.')
        for field in ['source_url', 'source_title', 'mapping_assumptions']:
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f'View set needs {field}.')
        date_fields = ['published_on', 'recorded_on'] + (['valid_from', 'expires_on'] if record['enabled'] else [])
        for field in date_fields:
            value = record.get(field)
            try:
                if not isinstance(value, str) or pd.Timestamp(value).strftime('%Y-%m-%d') != value:
                    raise ValueError()
            except Exception as exc:
                raise ValueError(f'View set needs a canonical {field} date.') from exc
        if not record['enabled']:
            if not record.get('inactive_reason'):
                raise ValueError('Disabled view sets need an inactive_reason.')
            continue
        if (record['published_on'] in publications or record.get('horizon_months') != 12
                or record.get('return_definition') != 'annual_arithmetic_total_return_spread'
                or not record['published_on'] <= record['valid_from'] < record['expires_on']
                or record['recorded_on'] > record['valid_from']):
            raise ValueError('Enabled views need unique publication dates, a 12-month spread, and valid recorded/activation/expiry dates.')
        publications.add(record['published_on'])
        if record.get('classification') not in {'provider_forecast_with_mapping', 'research_assumption'}:
            raise ValueError('View classification must distinguish provider mapping from research assumptions.')
        if not isinstance(record.get('views'), list) or not record['views']:
            raise ValueError('Enabled view sets require numerical views.')
        pairs = set()
        for view in record['views']:
            if not isinstance(view, dict):
                raise ValueError('Each numerical view must be an object.')
            pair = (view.get('long'), view.get('short'))
            values = [view.get('annual_spread'), view.get('confidence')]
            if (pair[0] not in symbols or pair[1] not in symbols or pair[0] == pair[1]
                    or frozenset(pair) in pairs
                    or not all(isinstance(v, (float, int)) and np.isfinite(v) for v in values)
                    or not 0 < values[1] < 1 or not view.get('uncertainty_basis')):
                raise ValueError('Views need distinct known assets, finite spreads, confidence strictly between 0 and 1 and an uncertainty basis.')
            pairs.add(frozenset(pair))
    return register


def eligible_view_set(register, decision_close, execution_close):
    """Latest available set supersedes earlier sets; expiry never resurrects an old set.

    Publication/recording are date-only and must both precede the decision close.
    Expiry is exclusive at execution; activation starts at a scheduled rebalance.
    """
    decision, execution = pd.Timestamp(decision_close).normalize(), pd.Timestamp(execution_close).normalize()
    candidates = [r for r in register if r['enabled']
                  and pd.Timestamp(r['published_on']) < decision
                  and pd.Timestamp(r['recorded_on']) < decision
                  and pd.Timestamp(r['valid_from']) <= decision]
    if not candidates:
        return [], None
    newest = max(candidates, key=lambda r: r['published_on'])
    if execution >= pd.Timestamp(newest['expires_on']):
        return [], None
    views = [(v['long'], v['short'], v['annual_spread'], v['confidence']) for v in newest['views']]
    return views, newest['id']


def higher_moment_weights(returns, cap=0.35, risk_aversion=3.0,
                          skew_preference=0.02, kurtosis_penalty=0.005):
    """Composite annual mean/variance and daily standardized-moment preference.

    Deterministic multistart SLSQP checks feasibility, not global optimality.
    Coefficients are explicit heuristic preferences, not a Taylor utility fit.
    """
    data = _numeric_frame(returns, 'returns', minimum_rows=252)
    n = data.shape[1]
    if n < 2:
        raise ValueError("Higher-moment allocation requires at least two assets.")
    if not 1 / n <= cap <= 1:
        raise ValueError(f'cap must be between {1/n:.3f} and 1.')
    if (not np.isfinite([risk_aversion, skew_preference, kurtosis_penalty]).all()
            or min(risk_aversion, skew_preference, kurtosis_penalty) < 0):
        raise ValueError('Higher-moment preferences must be nonnegative.')
    matrix = data.to_numpy()

    def negative_utility(weights):
        series = matrix @ weights
        if series.std(ddof=1) < 1e-12:
            return 1e12
        mean = series.mean() * PERIODS_PER_YEAR
        variance = series.var(ddof=1) * PERIODS_PER_YEAR
        utility = (mean - 0.5 * risk_aversion * variance
                   + skew_preference * skew(series, bias=False)
                   - kurtosis_penalty * kurtosis(series, fisher=True, bias=False))
        return -float(utility)

    equal = np.full(n, 1 / n)
    starts = [equal]
    for index in np.argsort(matrix.mean(axis=0))[-min(3, n):]:
        concentrated = np.full(n, (1 - cap) / (n - 1))
        concentrated[index] = cap
        starts.append(concentrated)
    attempts, candidates = [], []
    for number, start in enumerate(starts):
        result = minimize(negative_utility, start, method='SLSQP', bounds=[(0, cap)] * n,
                          constraints=[{'type': 'eq', 'fun': lambda weights: weights.sum() - 1}],
                          options={'ftol': 1e-12, 'maxiter': 1000})
        w = result.x
        valid = bool(result.success and np.isfinite(w).all() and np.isfinite(result.fun)
                     and result.fun < 1e11 and abs(w.sum() - 1) <= 1e-7
                     and w.min() >= -1e-7 and w.max() <= cap + 1e-7)
        attempts.append({'Start': number, 'Valid': valid, 'Utility': -float(result.fun),
                         'Message': str(result.message)})
        if valid:
            candidates.append(result)
    if not candidates:
        raise RuntimeError(f'Higher-moment optimization found no feasible solution: {attempts}')
    best = min(candidates, key=lambda result: result.fun)
    weights = pd.Series(best.x, index=data.columns, name='Higher-moment utility')
    weights.attrs['solver_attempts'] = attempts
    weights.attrs['local_utility_spread'] = float(max(r.fun for r in candidates) - best.fun)
    return weights


def fractional_kelly_weights(returns, annual_rf=0.03, fraction=0.5, cap=0.35,
                             holding_period='monthly'):
    """Solve capped, unlevered full Kelly with cash, then scale risky weights.

    The fraction is a multiplier of that constrained full-Kelly solution, not
    a required risky exposure. Negative opportunities may leave all wealth cash.
    The cap applies to full Kelly before scaling. Default scenarios are completed
    calendar-month buy-and-hold asset returns (both boundary months excluded).
    Daily mode describes daily rebalancing and is not used by the monthly strategy.
    """
    data = _numeric_frame(returns, 'returns', minimum_rows=252)
    n = data.shape[1]
    if not 0 < fraction <= 1:
        raise ValueError('fraction must be in (0, 1].')
    if not np.isfinite(cap) or not 0 < cap <= 1:
        raise ValueError('cap must be in (0, 1].')
    if not np.isfinite(annual_rf) or annual_rf <= -1:
        raise ValueError('annual_rf must be finite and greater than -1.')
    if holding_period == 'monthly':
        scenarios = monthly_compound(data)
        if len(scenarios) < 10:
            raise ValueError('Monthly Kelly requires at least 10 complete historical months.')
        period_rf = (1 + annual_rf) ** (1 / 12) - 1
    elif holding_period == 'daily':
        scenarios = data
        period_rf = (1 + annual_rf) ** (1 / PERIODS_PER_YEAR) - 1
    else:
        raise ValueError('holding_period must be monthly or daily.')
    matrix = scenarios.to_numpy()

    def negative_log_growth(weights):
        gross = 1 + matrix @ weights + (1 - weights.sum()) * period_rf
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
