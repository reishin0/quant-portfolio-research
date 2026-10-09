"""Diagnostics and explicitly labelled experiments restored from the study.

Return inputs are decimal simple returns. Diagnostic fits do not alter the
maintained strategy targets. Network acquisition lives only in the notebook's
optional appendix; all functions here are deterministic and offline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from portfolio_tools import historical_metrics, portfolio_step
from research_extensions import _numeric_frame, FACTOR_COLUMNS, factor_regression


def performance_table(returns, annual_rf=0.03, periods_per_year=252, benchmark=None, cash_returns=None):
    data = _numeric_frame(returns, 'returns', minimum_rows=2)
    table = pd.DataFrame({name: historical_metrics(data[name], annual_rf, periods_per_year, cash_returns)
                          for name in data}).T
    if benchmark is not None:
        reference = pd.Series(benchmark).reindex(data.index)
        if not np.isfinite(reference.to_numpy()).all():
            raise ValueError('Benchmark dates must cover returns.')
        active = data.sub(reference, axis=0)
        table['Tracking error'] = active.std(ddof=1) * np.sqrt(periods_per_year)
        table['Information ratio'] = (active.mean() * periods_per_year
                                      / table['Tracking error'].replace(0, np.nan))
    return table


def capm_diagnostics(returns, benchmark, annual_rf=0.03):
    """OLS on matching daily excess returns; cash rate is an explicit assumption."""
    data = _numeric_frame(returns, 'returns', minimum_rows=24)
    market = pd.Series(benchmark).reindex(data.index)
    if not np.isfinite(market.to_numpy()).all() or market.var() <= 0:
        raise ValueError('Market must be finite, aligned and have positive variance.')
    rf = (1 + annual_rf) ** (1 / 252) - 1
    beta = data.apply(lambda x: x.cov(market) / market.var())
    alpha = (data.mean() - rf) - beta * (market.mean() - rf)
    return pd.DataFrame({'Beta': beta, 'Annual alpha': alpha * 252,
                         'Historical annual excess': (data.mean() - rf) * 252,
                         'CAPM annual excess': beta * (market.mean() - rf) * 252,
                         'R-squared': data.apply(lambda x: x.corr(market) ** 2),
                         'Observations': len(data)})


def rolling_market_model(returns, benchmark, window=60, annual_rf=0.03):
    """Trailing excess-return OLS coefficients shifted one observation forward."""
    data = _numeric_frame(returns, 'returns', minimum_rows=window + 1)
    market = pd.Series(benchmark).reindex(data.index)
    if not isinstance(window, int) or window < 3 or not np.isfinite(market).all():
        raise ValueError('Window and benchmark are invalid.')
    rf = (1 + annual_rf) ** (1 / 252) - 1
    x, y = market - rf, data - rf
    variance = x.rolling(window).var().replace(0, np.nan)
    beta = y.apply(lambda s: s.rolling(window).cov(x) / variance).shift(1)
    alpha = y.rolling(window).mean().shift(1) - beta.mul(x.rolling(window).mean().shift(1), axis=0)
    # Conditional on the realized market return; this is not an ex-ante return forecast.
    fitted = alpha + beta.mul(x, axis=0)
    return {'beta': beta, 'annual_alpha': alpha * 252,
            'conditional_excess': fitted}


def select_rolling_window(training_returns, benchmark, windows=(30, 60, 90), annual_rf=0.03):
    """Compare conditional return residuals on identical training-only dates."""
    data = _numeric_frame(training_returns, 'training_returns', minimum_rows=max(windows) + 2)
    rf = (1 + annual_rf) ** (1 / 252) - 1
    common = data.index[max(windows):]
    rows = []
    for window in windows:
        fitted = rolling_market_model(data, benchmark, window, annual_rf)['conditional_excess'].loc[common]
        if not np.isfinite(fitted.to_numpy()).all():
            raise ValueError('A candidate rolling regression has a zero-variance market window.')
        errors = data.loc[common] - rf - fitted
        rows.append({'Window': window, 'Conditional return MSE': float(np.mean(errors.to_numpy() ** 2)),
                     'Dates': len(common), 'Assets': data.shape[1],
                     'First scored date': str(common.min().date()),
                     'Last scored date': str(common.max().date())})
    scores = pd.DataFrame(rows).set_index('Window')
    return int(scores['Conditional return MSE'].idxmin()), scores


def capped_proportional_weights(scores, cap=0.35):
    """Allocate proportionally, repeatedly fixing saturated assets at their cap."""
    scores = pd.Series(scores, dtype=float).copy()
    if (scores.index.has_duplicates or not np.isfinite(scores).all()
            or (scores < 0).any() or scores.sum() <= 0
            or not 1 / len(scores) <= cap <= 1):
        raise ValueError('Scores must be nonnegative with a feasible cap and positive total.')
    weights = pd.Series(0.0, index=scores.index)
    free = list(scores.index)
    remaining = 1.0
    while free:
        values = scores.loc[free]
        proposal = remaining * (values / values.sum() if values.sum() > 0 else pd.Series(1 / len(free), index=free))
        saturated = proposal.index[proposal > cap + 1e-12]
        if len(saturated) == 0:
            weights.loc[free] = proposal
            break
        weights.loc[saturated] = cap
        remaining = 1 - weights.sum()
        free = [name for name in free if name not in saturated]
    return weights


def mean_variance_weights(expected_excess, covariance, risk_aversion=3.07, cap=0.35,
                          allow_cash=True):
    """Optimize annual excess utility mu'w - lambda/2 w'Sigma w."""
    mu = pd.Series(expected_excess, dtype=float)
    sigma = pd.DataFrame(covariance).loc[mu.index, mu.index].to_numpy(dtype=float)
    n = len(mu)
    if (not np.isfinite(mu).all() or not np.isfinite(sigma).all()
            or not np.allclose(sigma, sigma.T) or np.linalg.eigvalsh(sigma).min() < -1e-10
            or not np.isfinite(risk_aversion) or risk_aversion <= 0
            or not 0 < cap <= 1 or (not allow_cash and cap * n < 1)):
        raise ValueError('Invalid moments, risk aversion or allocation cap.')
    budget = {'type': 'ineq' if allow_cash else 'eq', 'fun': lambda w: 1 - w.sum()}
    start = np.zeros(n) if allow_cash else np.full(n, 1 / n)
    result = minimize(lambda w: float(-mu.to_numpy() @ w + .5 * risk_aversion * w @ sigma @ w),
                      start, method='SLSQP', bounds=[(0, cap)] * n, constraints=[budget],
                      options={'ftol': 1e-12, 'maxiter': 1000})
    w = result.x
    if (not result.success or not np.isfinite(w).all() or w.min() < -1e-7
            or w.max() > cap + 1e-7 or w.sum() > 1 + 1e-7
            or (not allow_cash and abs(w.sum() - 1) > 1e-7)):
        raise RuntimeError(f'Mean-variance optimization failed: {result.message}')
    return pd.Series(w, index=mu.index)


def higher_moment_diagnostics(returns, weights):
    """Population central tensors contracted into the actual portfolio moments.

    Raw asset moments must be contracted before standardizing by portfolio
    volatility. Contracting standardized asset co-moments with raw weights does
    not produce portfolio skewness/kurtosis. No small-sample correction is used.
    """
    data = _numeric_frame(returns, 'returns')
    w = pd.Series(weights).reindex(data.columns).to_numpy(dtype=float)
    if not np.isfinite(w).all():
        raise ValueError('Weights must cover each asset.')
    x = data.to_numpy() - data.mean().to_numpy()
    n = len(x)
    second = x.T @ x / n
    third = np.einsum('ti,tj,tk->ijk', x, x, x, optimize=True) / n
    fourth = np.einsum('ti,tj,tk,tl->ijkl', x, x, x, x, optimize=True) / n
    variance = float(w @ second @ w)
    if variance <= 0 or (np.diag(second) <= 0).any():
        raise ValueError('Higher moments require positive portfolio and asset variances.')
    skewness = float(np.einsum('i,j,k,ijk', w, w, w, third) / variance ** 1.5)
    kurtosis = float(np.einsum('i,j,k,l,ijkl', w, w, w, w, fourth) / variance ** 2)
    z = x / np.sqrt(np.diag(second))
    pair_skew = (z ** 2).T @ z / n
    pair_kurt = (z ** 2).T @ (z ** 2) / n
    portfolio = x @ w
    checks = pd.DataFrame({
        'Tensor contraction': [variance, skewness, kurtosis - 3],
        'Direct portfolio sample': [np.mean(portfolio ** 2),
                                    np.mean(portfolio ** 3) / variance ** 1.5,
                                    np.mean(portfolio ** 4) / variance ** 2 - 3]},
        index=['Daily variance', 'Skewness', 'Excess kurtosis'])
    checks['Absolute difference'] = (checks.iloc[:, 0] - checks.iloc[:, 1]).abs()
    return {'third': third, 'fourth': fourth, 'checks': checks,
            'pair_coskewness': pd.DataFrame(pair_skew, index=data.columns, columns=data.columns),
            'pair_cokurtosis': pd.DataFrame(pair_kurt, index=data.columns, columns=data.columns)}


def factor_fit_diagnostics(monthly_returns, factors):
    """Fitted excess returns use every factor, not a partial market-only line."""
    coefficients = factor_regression(monthly_returns, factors)
    dates = monthly_returns.index.intersection(factors.index)
    actual = monthly_returns.loc[dates].sub(factors.loc[dates, 'RF'], axis=0)
    fitted = pd.DataFrame(index=dates)
    for name in monthly_returns:
        beta = coefficients.loc[name, [f'{f} loading' for f in FACTOR_COLUMNS]].to_numpy(dtype=float)
        fitted[name] = coefficients.loc[name, 'Annual alpha'] / 12 + factors.loc[dates, FACTOR_COLUMNS].to_numpy() @ beta
    return coefficients, actual, fitted


def factor_tilt(weights, loadings, positive_threshold, negative_threshold, cap=.35):
    """Original +/-10% per-factor heuristic, with repeated cap enforcement."""
    base = pd.Series(weights, dtype=float)
    loadings = pd.DataFrame(loadings).loc[base.index]
    if (not np.isfinite(loadings.to_numpy()).all() or positive_threshold <= 0
            or negative_threshold <= 0):
        raise ValueError('Loadings must be finite and thresholds positive.')
    positive = (loadings >= positive_threshold).sum(axis=1)
    negative = (loadings <= -negative_threshold).sum(axis=1)
    scores = base * 1.1 ** positive * .9 ** negative
    return capped_proportional_weights(scores, cap)


def evaluate_targets(asset_returns, targets, annual_rf=.03, transaction_cost_bps=10,
                     annual_short_borrow_bps=100, cash_returns=None):
    """Evaluate precomputed dated targets with the same ledger as the main run.

    Caller is responsible for fitting targets before their effective dates.
    A target table includes asset columns and Cash and must start on day one.
    """
    returns = _numeric_frame(asset_returns, 'asset_returns', minimum_rows=2)
    targets = _numeric_frame(targets, 'targets', minimum_rows=1)
    names = list(returns.columns)
    if (list(targets.columns) != names + ['Cash'] or targets.index[0] != returns.index[0]
            or not targets.index.isin(returns.index).all()
            or not np.allclose(targets.sum(axis=1), 1)):
        raise ValueError('Targets must cover the initial date, assets and cash budget.')
    if (not np.isfinite([annual_rf, transaction_cost_bps, annual_short_borrow_bps]).all()
            or annual_rf <= -1 or min(transaction_cost_bps, annual_short_borrow_bps) < 0):
        raise ValueError('Invalid financing/cost assumptions.')
    rf = (1 + annual_rf) ** (1 / 252) - 1
    if cash_returns is not None and (not cash_returns.index.equals(returns.index)
                                    or not np.isfinite(cash_returns).all()
                                    or (cash_returns <= -1).any()):
        raise ValueError('Cash returns must exactly match evaluation dates.')
    borrow = annual_short_borrow_bps / 10000 / 252
    w, cash = np.zeros(len(names)), 1.0
    result, trades = [], []
    for date, row in returns.iterrows():
        cost = 0.0
        if date in targets.index:
            target = targets.loc[date, names].to_numpy()
            target_cash = float(targets.loc[date, 'Cash'])
            turnover = (np.abs(target - w).sum() + abs(target_cash - cash)) / 2
            cost = turnover * transaction_cost_bps / 10000
            trades.append({'Date': date, 'One-way turnover': turnover, 'Estimated cost': cost})
            w, cash = target, target_cash
        period_cash = rf if cash_returns is None else float(cash_returns.loc[date])
        net, w, cash, _ = portfolio_step(w, cash, row.to_numpy(), period_cash, borrow, cost)
        result.append(net)
    return pd.Series(result, index=returns.index), pd.DataFrame(trades).set_index('Date')


def normalize_context(series):
    """Full-sample z scores for display only; never a point-in-time signal."""
    values = pd.Series(series, dtype=float).dropna()
    if len(values) < 2 or not np.isfinite(values).all() or values.std() <= 0:
        raise ValueError('Context normalization needs finite, nonconstant observations.')
    return (values - values.mean()) / values.std()
