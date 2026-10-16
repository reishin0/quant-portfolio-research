"""Core calculations for the maintained portfolio-construction research.

Synthetic data support deterministic validation; Yahoo mode requests adjusted
historical prices. No brokerage or order APIs are used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from research_extensions import (bab_weights, fractional_kelly_weights,
                                 higher_moment_weights, estimate_covariance,
                                 validate_view_register, eligible_view_set)
from data_tools import load_price_snapshot

ASSETS = ['VUG', 'SPHD', 'MTUM', 'ACWI', 'XLK', 'XLE', 'IEO', 'GLD']
BENCHMARK = 'SPY'
PERIODS_PER_YEAR = 252


def load_prices(mode='synthetic', start='2020-01-01', end='2024-08-23', seed=42,
                cache_path=None):
    """Return a date-by-symbol table and provenance; never silently change mode."""
    start_date, end_date = pd.Timestamp(start), pd.Timestamp(end)
    if pd.isna(start_date) or pd.isna(end_date) or start_date >= end_date:
        raise ValueError('START_DATE must be earlier than END_DATE; use YYYY-MM-DD.')
    symbols = ASSETS + [BENCHMARK]
    if mode in {'synthetic', 'demo'}:
        dates = pd.bdate_range(start_date, end_date, inclusive='left')
        if len(dates) < 253:
            raise ValueError('Choose at least 253 business days for this example.')
        rng = np.random.default_rng(seed)
        market = rng.normal(0.00025, 0.01, len(dates))
        common = rng.normal(0, 0.004, len(dates))
        beta = np.array([1.1, 0.65, 0.95, 0.85, 1.25, 0.9, 1.0, 0.1])
        drift = np.array([.00005, .00001, .00004, .00001, .00008, .00002, .00001, .00003])
        noise = rng.normal(0, 0.006, (len(dates), len(ASSETS)))
        log_returns = market[:, None] * beta + common[:, None] + drift + noise
        levels = np.column_stack([100 * np.exp(np.cumsum(log_returns, axis=0)),
                                  100 * np.exp(np.cumsum(market))])
        prices = pd.DataFrame(levels, index=dates, columns=symbols)
        mode = 'synthetic'
        label = 'SYNTHETIC VALIDATION DATA - not real ETF performance'
        details = {'seed': seed, 'calendar': 'weekdays, including market holidays'}
    elif mode == 'snapshot':
        path = Path(cache_path) if cache_path else Path('data/etf_snapshot_20261009.json')
        prices, snapshot = load_price_snapshot(path, symbols, start, end)
        label = 'FROZEN YAHOO SNAPSHOT - adjusted ETF prices retrieved 9 October 2026'
        details = {'snapshot_manifest': snapshot, 'source_file_sha256': snapshot['price_sha256']}
    elif mode == 'submission':
        from submission_data import DATA_DIR, file_sha256, load_submission_prices
        path = Path(cache_path) if cache_path else DATA_DIR / 'efts_dataset.csv'
        prices = load_submission_prices(path, symbols, start, end)
        label = 'SUBMISSION SNAPSHOT - adjusted ETF prices supplied with the 2024 study'
        details = {'source_file': path.name, 'source_file_sha256': file_sha256(path),
                   'price_field': 'Adj Close', 'aum_used': False,
                   'vintage': '2024 submission; exact provider download timestamp unknown'}
    elif mode == 'yahoo':
        import yfinance as yf
        try:
            raw = yf.download(symbols, start=start, end=end, auto_adjust=True,
                              progress=False, threads=False, timeout=30,
                              multi_level_index=True)
        except Exception as exc:
            raise RuntimeError('Yahoo download failed. Check your internet connection, '
                               'or explicitly change DATA_MODE to "synthetic".') from exc
        if raw is None or raw.empty or 'Close' not in raw:
            raise ValueError('Yahoo returned no usable prices. Try again later or choose DATA_MODE="synthetic".')
        prices = raw['Close'].copy()
        missing = set(symbols) - set(prices.columns)
        if missing:
            raise ValueError(f'Yahoo did not return these symbols: {sorted(missing)}. No substitute data were used.')
        prices = prices.reindex(columns=symbols)
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        label = 'YAHOO FINANCE - adjusted historical prices, downloaded now'
        details = {'auto_adjust': True, 'downloaded_utc': datetime.now(timezone.utc).isoformat()}
    else:
        raise ValueError('DATA_MODE must be "snapshot", "submission", "synthetic" or "yahoo".')

    prices = prices.sort_index()
    if prices.index.has_duplicates:
        raise ValueError('Duplicate price dates: review the source before continuing.')
    prices = prices.apply(pd.to_numeric, errors='raise')
    finite_prices = prices.to_numpy()[np.isfinite(prices.to_numpy())]
    if (finite_prices <= 0).any() or np.isinf(prices.to_numpy()).any():
        raise ValueError('Prices must be positive finite numbers or missing observations.')
    if prices.notna().sum().min() < 253:
        raise ValueError('At least one symbol has fewer than 253 prices. Expand the date range.')
    prices.index.name = 'Date'
    provenance = {
        'mode': mode, 'label': label, 'requested_start': start, 'requested_end_exclusive': end,
        'first_price': str(prices.index.min().date()), 'last_price': str(prices.index.max().date()),
        'price_rows': len(prices), 'symbols': symbols,
        'missing_prices_by_symbol': prices.isna().sum().astype(int).to_dict(),
        'prices_csv_sha256': hashlib.sha256(prices.to_csv().encode('utf-8')).hexdigest(),
        **details,
    }
    return prices, provenance


def aligned_returns(prices):
    """Trim unavailable endpoints and reject gaps inside the common price history.

    Dropping an internal return row would erase held assets' gains/losses. This
    function does not invent prices or an exchange calendar for absent dates.
    """
    if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.has_duplicates:
        raise ValueError('Prices require unique datetime observations.')
    prices = prices.sort_index()
    if prices.columns.has_duplicates or prices.empty or prices.isna().all().any():
        raise ValueError('Price columns must be unique and contain observations.')
    start = max(prices.apply(lambda x: x.first_valid_index()))
    end = min(prices.apply(lambda x: x.last_valid_index()))
    common = prices.loc[start:end]
    if common.isna().any().any():
        raise ValueError('Internal missing prices: repair the source or define an explicit valuation policy; return days cannot be dropped.')
    if not np.isfinite(common.to_numpy()).all() or (common <= 0).any().any():
        raise ValueError('Prices must be finite and positive.')
    returns = common.pct_change(fill_method=None).iloc[1:]
    if len(returns) < 252:
        raise ValueError('Fewer than 252 complete aligned return observations. Expand the dates or inspect gaps.')
    if not np.isfinite(returns.to_numpy()).all():
        raise ValueError('Returns contain non-finite values.')
    if (returns <= -1).any().any():
        raise ValueError('A simple return is at or below -100%; inspect the price data.')
    return returns


def black_litterman(covariance, prior_weights=None, risk_aversion=3.07, tau=0.1,
                    return_details=False, views=None, omega=None):
    """Annual excess-return posterior, using view-scaled uncertainty.

    A None comparator specifies an absolute annual excess return for one asset.
    Otherwise Q is the annual return difference between two assets.
    """
    names = list(covariance.columns)
    if names != list(covariance.index) or len(names) < 2:
        raise ValueError('Covariance labels and ordering must match.')
    sigma = covariance.to_numpy(dtype=float)
    if not np.isfinite(sigma).all() or not np.allclose(sigma, sigma.T):
        raise ValueError('Covariance must be finite and symmetric.')
    if np.linalg.eigvalsh(sigma).min() < -1e-10:
        raise ValueError('Covariance must be positive semidefinite.')
    if not np.isfinite([tau, risk_aversion]).all() or tau <= 0 or risk_aversion <= 0:
        raise ValueError('tau and risk aversion must be positive.')
    weights = np.full(len(names), 1 / len(names)) if prior_weights is None else np.asarray(prior_weights, dtype=float)
    if weights.shape != (len(names),) or not np.isfinite(weights).all() or (weights < 0).any() or not np.isclose(weights.sum(), 1):
        raise ValueError('Prior weights must be finite, nonnegative and sum to one.')
    # ORIGINAL 2024 SUBMISSION views (21 August 2024); inactive reference only:
    # views = [('GLD', 'MTUM', .15, .90), ('XLK', 'XLE', .08, .70), ('SPHD', 'VUG', .06, .80)]
    views = [] if views is None else list(views)
    for view in views:
        if (len(view) != 4 or view[0] not in names or (view[1] is not None and view[1] not in names)
                or view[0] == view[1] or not np.isfinite(view[2:]).all()
                or not 0 < view[3] <= 1):
            raise ValueError('Views require a known asset, a different known comparator or None for absolute excess, a finite annual Q and confidence in (0, 1].')
    p = np.zeros((len(views), len(names)))
    for j, (long_asset, short_asset, _, _) in enumerate(views):
        p[j, names.index(long_asset)] = 1
        if short_asset is not None:
            p[j, names.index(short_asset)] = -1
    q = np.array([view[2] for view in views])
    confidence = np.array([view[3] for view in views])
    prior = risk_aversion * sigma @ weights
    scaled = tau * sigma
    view_variance = np.diag(p @ scaled @ p.T)
    explicit_omega = omega is not None
    if omega is None:
        omega = np.diag(np.maximum(view_variance, 1e-12) * (1 - confidence) / confidence)
    else:
        omega = np.asarray(omega, dtype=float)
        if (omega.shape != (len(views), len(views)) or not np.isfinite(omega).all()
                or not np.allclose(omega, omega.T)
                or (len(views) and np.linalg.eigvalsh(omega).min() <= 0)):
            raise ValueError('Explicit Omega must be finite, symmetric, positive definite and match views.')
    posterior = prior + scaled @ p.T @ np.linalg.solve(p @ scaled @ p.T + omega, q - p @ prior)
    table = pd.DataFrame(views, columns=['Outperformer', 'Comparator', 'Annual difference', 'Assumed confidence'])
    if explicit_omega:
        table['Assumed confidence'] = np.nan
    if len(views):
        table['Effective marginal weight'] = view_variance / (view_variance + np.diag(omega))
    if return_details:
        mean_covariance = scaled - scaled @ p.T @ np.linalg.solve(p @ scaled @ p.T + omega, p @ scaled)
        labels = [f'{v[0]} - {v[1]}' if v[1] is not None else f'{v[0]} excess' for v in views]
        return {
            'prior': pd.Series(prior, index=names),
            'posterior': pd.Series(posterior, index=names), 'views': table,
            'P': pd.DataFrame(p, index=labels, columns=names),
            'Q': pd.Series(q, index=labels, name='Annual excess/relative view'),
            'Omega': pd.DataFrame(omega, index=labels, columns=labels),
            'mean_covariance': pd.DataFrame(mean_covariance, index=names, columns=names),
            'predictive_covariance': pd.DataFrame(sigma + mean_covariance, index=names, columns=names),
        }
    return pd.Series(prior, index=names), pd.Series(posterior, index=names), table


def optimize_weights(expected_excess, covariance, returns, benchmark, cap=0.35):
    """Long-only, fully invested examples, with checked solver results."""
    names = list(covariance.columns)
    if list(covariance.index) != names or list(expected_excess.index) != names or list(returns.columns) != names:
        raise ValueError('All asset labels must use the same ordering.')
    if not returns.index.equals(benchmark.index):
        raise ValueError('Asset and benchmark dates must match.')
    n = len(names)
    if not 1 / n <= cap <= 1:
        raise ValueError(f'With {n} assets, MAX_WEIGHT must be between {1/n:.3f} and 1.')
    sigma = covariance.to_numpy(dtype=float)
    mu = expected_excess.to_numpy(dtype=float)
    history = returns.to_numpy(dtype=float)
    bench = benchmark.to_numpy(dtype=float)
    if not all(np.isfinite(value).all() for value in [sigma, mu, history, bench]):
        raise ValueError('Optimization inputs must be finite.')
    if (not np.allclose(sigma, sigma.T) or np.linalg.eigvalsh(sigma).min() <= 1e-12):
        raise ValueError('Optimizer covariance must be symmetric positive definite; inspect ill conditioning.')
    equal = np.full(n, 1 / n)

    def variance(w):
        return float(w @ sigma @ w)

    def neg_sharpe(w):
        return float(-(w @ mu) / np.sqrt(max(variance(w), 1e-15)))

    def tracking_variance(w):
        return float(np.var(history @ w - bench, ddof=1) * PERIODS_PER_YEAR)

    result_weights = {'Equal weight': equal}
    for label, objective in [('Minimum variance', variance), ('BL maximum Sharpe', neg_sharpe),
                             ('Minimum tracking error', tracking_variance)]:
        result = minimize(objective, equal, method='SLSQP', bounds=[(0, cap)] * n,
                          constraints=[{'type': 'eq', 'fun': lambda w: w.sum() - 1}],
                          options={'ftol': 1e-12, 'maxiter': 1000})
        w = result.x
        if not result.success or not np.isfinite(w).all() or abs(w.sum() - 1) > 1e-7 or w.min() < -1e-7 or w.max() > cap + 1e-7:
            raise RuntimeError(f'{label} did not find valid weights: {result.message}')
        result_weights[label] = w
    return pd.DataFrame(result_weights, index=names)


def historical_metrics(series, annual_rf=0.03, periods_per_year=PERIODS_PER_YEAR,
                       cash_returns=None):
    """Annualized metrics from explicit period frequency; default is daily/252."""
    values = np.asarray(series, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError('At least two finite period returns above -100% are required.')
    if not np.isfinite(annual_rf) or annual_rf <= -1:
        raise ValueError('The annual risk-free assumption must be finite and greater than -100%.')
    if not np.isfinite(periods_per_year) or periods_per_year <= 0:
        raise ValueError('periods_per_year must be positive.')
    volatility = values.std(ddof=1) * np.sqrt(periods_per_year)
    if cash_returns is None:
        cash = np.full(len(values), (1 + annual_rf) ** (1 / periods_per_year) - 1)
    else:
        if isinstance(series, pd.Series) and not cash_returns.index.equals(series.index):
            raise ValueError('Cash returns must match performance dates exactly.')
        cash = np.asarray(cash_returns, dtype=float)
        if cash.shape != values.shape or not np.isfinite(cash).all() or (cash <= -1).any():
            raise ValueError('Invalid performance cash returns.')
    excess = values - cash
    excess_volatility = excess.std(ddof=1) * np.sqrt(periods_per_year)
    downside = np.sqrt(np.mean(np.minimum(excess, 0) ** 2) * periods_per_year)
    wealth = np.concatenate([[1.0], np.cumprod(1 + values)])
    drawdown = wealth / np.maximum.accumulate(wealth) - 1
    return {
        'Annual mean': values.mean() * periods_per_year,
        'CAGR': wealth[-1] ** (periods_per_year / len(values)) - 1,
        'Annual volatility': volatility,
        'Sharpe': excess.mean() * periods_per_year / excess_volatility if excess_volatility > 1e-15 else np.nan,
        'Sortino': excess.mean() * periods_per_year / downside if downside > 0 else np.nan,
        'Max drawdown': drawdown.min(),
    }


def portfolio_step(weights, cash, asset_returns, daily_rf, daily_borrow_rate, cost=0.0):
    """One self-financing holding day; borrow fees debit cash.

    Rebalance costs reduce initial wealth proportionally before target holdings
    are established. Borrow payments then reduce end-of-day cash and NAV.
    """
    weights = np.asarray(weights, dtype=float)
    asset_returns = np.asarray(asset_returns, dtype=float)
    if (weights.shape != asset_returns.shape or not np.isfinite(weights).all()
            or not np.isfinite(asset_returns).all() or (asset_returns <= -1).any()
            or not np.isfinite([cash, daily_rf, daily_borrow_rate, cost]).all()
            or not 0 <= cost < 1 or daily_borrow_rate < 0
            or not np.isclose(weights.sum() + cash, 1)):
        raise ValueError('Invalid holdings, returns, financing or transaction cost.')
    fee = float(np.maximum(-weights, 0).sum() * daily_borrow_rate)
    closing_assets = weights * (1 + asset_returns)
    closing_cash = cash * (1 + daily_rf) - fee
    gross = float(closing_assets.sum() + closing_cash)
    if gross <= 0:
        raise RuntimeError('Portfolio lost at least 100% after financing and borrow costs.')
    return ((1 - cost) * gross - 1, closing_assets / gross,
            closing_cash / gross, fee)


def analyze(prices, annual_rf=0.03, max_weight=0.35, training_days=504,
            transaction_cost_bps=10.0, annual_short_borrow_bps=100.0,
            kelly_fraction=0.5, bab_gross_limit=2.0,
            investor_views=None, views_as_of=None, cash_returns=None,
            view_register=None, apply_registered_views=True,
            training_window_days=None, covariance_estimator='sample',
            evaluation_start_date=None, bab_failure_policy='raise'):
    """Run an expanding-window, monthly walk-forward portfolio comparison.

    For a first earned return ending t, fitting stops at close t-2; execution
    occurs at close t-1. Targets are held between month starts, asset weights drift
    with returns, and one-way turnover is charged at the stated basis-point rate.
    Dated views enter only when the fit cutoff close is strictly after
    their publication date. Date-only sources are treated as available after
    that entire day; the monthly schedule is not changed to force activation.
    """
    if not isinstance(training_days, int) or training_days < 252:
        raise ValueError('TRAINING_DAYS must be an integer of at least 252.')
    if not np.isfinite(transaction_cost_bps) or transaction_cost_bps < 0:
        raise ValueError('TRANSACTION_COST_BPS must be a finite nonnegative number.')
    if not np.isfinite(annual_short_borrow_bps) or annual_short_borrow_bps < 0:
        raise ValueError('ANNUAL_SHORT_BORROW_BPS must be a finite nonnegative number.')

    if training_window_days is not None and (not isinstance(training_window_days, int) or training_window_days < 252):
        raise ValueError('Training window must be None or at least 252 sessions.')
    if bab_failure_policy not in {'raise', 'cash'}:
        raise ValueError('BAB failure policy must be raise or cash.')
    register = validate_view_register([] if view_register is None else view_register, ASSETS)
    if register and investor_views:
        raise ValueError('Use the dated view register or legacy fixed views, not both.')
    configured_views = [] if investor_views is None else list(investor_views)
    publication_date = None
    if configured_views:
        try:
            parsed = datetime.strptime(views_as_of, '%Y-%m-%d')
            if parsed.strftime('%Y-%m-%d') != views_as_of:
                raise ValueError('Noncanonical date')
            publication_date = pd.Timestamp(parsed)
        except (TypeError, ValueError) as exc:
            raise ValueError('Nonempty investor views require VIEWS_AS_OF in YYYY-MM-DD format.') from exc

    returns = aligned_returns(prices)
    if len(returns) <= training_days + 1:
        raise ValueError('The aligned history must contain observations after TRAINING_DAYS.')
    # Validate configured views even if their date lies beyond the sample.
    black_litterman(returns.iloc[:training_days][ASSETS].cov() * PERIODS_PER_YEAR,
                   views=configured_views)
    assets = returns[ASSETS]
    benchmark = returns[BENCHMARK]
    if cash_returns is None:
        cash_series = pd.Series((1 + annual_rf) ** (1 / PERIODS_PER_YEAR) - 1, index=returns.index)
        cash_label = 'constant annual cash-rate assumption'
    else:
        if (not isinstance(cash_returns, pd.Series) or not cash_returns.index.equals(returns.index)
                or not np.isfinite(cash_returns).all() or (cash_returns <= -1).any()):
            raise ValueError('Cash returns must exactly cover all aligned return dates.')
        cash_series = cash_returns.copy()
        cash_label = 'supplied realized cash proxy; fixed annual_rf remains the forecast assumption'
    evaluation = returns.iloc[training_days + 1:]
    if evaluation_start_date is not None:
        evaluation = evaluation.loc[pd.Timestamp(evaluation_start_date):]
    if len(evaluation) < 2:
        raise ValueError('At least two evaluation sessions are required.')
    # Monthly activation, plus execution at the first session on/after view expiry.
    rebalance_dates = evaluation.groupby(evaluation.index.to_period('M')).head(1).index
    expiry_effective_dates = []
    for record in register:
        if record['enabled']:
            execution_positions = np.flatnonzero(returns.index >= pd.Timestamp(record['expires_on']))
            if len(execution_positions) and execution_positions[0] + 1 < len(returns):
                effective = returns.index[execution_positions[0] + 1]
                if effective in evaluation.index:
                    expiry_effective_dates.append(effective)
    rebalance_dates = rebalance_dates.union(pd.DatetimeIndex(expiry_effective_dates)).sort_values()
    positions = [returns.index.get_loc(date) for date in rebalance_dates]
    methods = ['Equal weight', 'Minimum variance', 'BL maximum Sharpe',
               'Minimum tracking error', 'Higher-moment utility',
               'Fractional Kelly', 'BAB beta-neutral']
    current = {name: {'assets': np.zeros(len(ASSETS)), 'cash': 1.0} for name in methods}
    net_returns = {name: [] for name in methods}
    net_dates = []
    target_records = []
    turnover_records = []
    view_records = []
    solver_records = []
    borrow_cost_totals = {name: 0.0 for name in methods}
    last_fit = None
    cost_rate = transaction_cost_bps / 10_000
    daily_rf = (1 + annual_rf) ** (1 / PERIODS_PER_YEAR) - 1
    daily_short_borrow_rate = annual_short_borrow_bps / 10_000 / PERIODS_PER_YEAR
    last_bab_diagnostics = None

    for number, start_position in enumerate(positions):
        stop_position = positions[number + 1] if number + 1 < len(positions) else len(returns)
        # Fit after close t-2, execute at close t-1, earn the return ending t.
        train = returns.iloc[:start_position - 1]
        if training_window_days is not None:
            train = train.iloc[-training_window_days:]
        test = returns.iloc[start_position:stop_position]
        covariance = estimate_covariance(train[ASSETS], covariance_estimator)
        decision_close = train.index[-1]
        eligible = (publication_date is not None
                    and decision_close.normalize() > publication_date)
        active_views = configured_views if eligible else []
        active_set = None
        if register:
            active_views, active_set = eligible_view_set(register, decision_close, returns.index[start_position - 1])
            if not apply_registered_views:
                active_views, active_set = [], None
        prior, posterior, views = black_litterman(covariance, views=active_views)
        view_records.append({'Date': test.index[0], 'Decision close': decision_close,
                             'Execution close': returns.index[start_position - 1],
                             'Publication date': next((r['published_on'] for r in register if r['id'] == active_set), None) if register else (views_as_of if configured_views else None),
                             'Configured views': sum(len(r.get('views', [])) for r in register if r['enabled']) if register else len(configured_views),
                             'Active set': active_set,
                             'Fit start': train.index[0], 'Fit observations': len(train),
                             'Covariance estimator': covariance_estimator,
                             'Shrinkage': covariance.attrs['shrinkage'],
                             'Covariance condition number': float(np.linalg.cond(covariance)),
                             'Active views': len(active_views)})
        targets = optimize_weights(posterior, covariance, train[ASSETS],
                                   train[BENCHMARK], max_weight)
        higher = higher_moment_weights(train[ASSETS], cap=max_weight)
        targets['Higher-moment utility'] = higher
        for attempt in higher.attrs['solver_attempts']:
            solver_records.append({'Date': test.index[0], **attempt,
                                   'Local utility spread': higher.attrs['local_utility_spread']})
        targets['Fractional Kelly'] = fractional_kelly_weights(
            train[ASSETS], annual_rf=annual_rf, fraction=kelly_fraction,
            cap=max_weight)
        try:
            targets['BAB beta-neutral'], last_bab_diagnostics = bab_weights(
                train[ASSETS], train[BENCHMARK], gross_limit=bab_gross_limit)
            view_records[-1]['BAB construction'] = 'beta-neutral target'
        except ValueError as exc:
            if bab_failure_policy != 'cash' or 'positive average beta' not in str(exc):
                raise
            # Explicit experiment policy: do not force leverage through near-zero/negative leg beta.
            targets['BAB beta-neutral'] = pd.Series(0., index=ASSETS)
            betas = train[ASSETS].apply(lambda col: col.cov(train[BENCHMARK]) / train[BENCHMARK].var())
            last_bab_diagnostics = pd.DataFrame({'Beta': betas, 'Weight': 0., 'Leg': 'Cash: ineligible leg beta'})
            last_bab_diagnostics.attrs.update(portfolio_beta=0., gross_exposure=0.)
            view_records[-1]['BAB construction'] = 'cash: nonpositive or near-zero leg beta'
        for name in methods:
            target = targets[name].to_numpy(dtype=float)
            target_cash = 1 - target.sum()
            before = current[name]
            turnover = float((np.abs(target - before['assets']).sum()
                              + abs(target_cash - before['cash'])) / 2)
            turnover_records.append({'Date': test.index[0], 'Portfolio': name,
                                     'One-way turnover': turnover,
                                     'Estimated cost': turnover * cost_rate})
            target_records.append({'Date': test.index[0], 'Portfolio': name,
                                   **dict(zip(ASSETS, target)), 'Cash': target_cash})
            current[name] = {'assets': target.copy(), 'cash': target_cash}

        for row_number, (date, row) in enumerate(test[ASSETS].iterrows()):
            net_dates.append(date)
            asset_returns = row.to_numpy(dtype=float)
            for name in methods:
                weights_now = current[name]['assets']
                cash_now = current[name]['cash']
                cost = turnover_records[-len(methods) + methods.index(name)]['Estimated cost'] if row_number == 0 else 0.0
                net, closing_weights, closing_cash, short_borrow = portfolio_step(
                    weights_now, cash_now, asset_returns, float(cash_series.loc[date]),
                    daily_short_borrow_rate, cost)
                net_returns[name].append(net)
                borrow_cost_totals[name] += short_borrow
                current[name] = {
                    'assets': closing_weights,
                    'cash': closing_cash,
                }
        last_fit = (covariance, prior, posterior, views, targets, last_bab_diagnostics)

    portfolio_returns = pd.DataFrame(net_returns, index=pd.DatetimeIndex(net_dates))
    portfolio_returns[BENCHMARK] = evaluation[BENCHMARK]
    portfolio_returns['Cash proxy'] = cash_series.loc[evaluation.index]
    historical = pd.DataFrame({name: historical_metrics(portfolio_returns[name], annual_rf,
                                                       cash_returns=cash_series.loc[evaluation.index])
                               for name in portfolio_returns}).T
    covariance, prior, posterior, views, asset_weights, bab_diagnostics = last_fit
    cash_weights = 1 - asset_weights.sum(axis=0)
    weights = pd.concat([asset_weights, pd.DataFrame([cash_weights], index=['Cash'])])
    model = pd.DataFrame(index=asset_weights.columns)
    model['Expected annual return'] = [annual_rf + asset_weights[name].to_numpy() @ posterior.to_numpy()
                                       for name in asset_weights]
    model['Annual volatility'] = [np.sqrt(asset_weights[name].to_numpy() @ covariance.to_numpy()
                                          @ asset_weights[name].to_numpy()) for name in asset_weights]
    model['Expected Sharpe'] = ((model['Expected annual return'] - annual_rf)
                                / model['Annual volatility'])
    target_history = pd.DataFrame(target_records).set_index(['Date', 'Portfolio'])
    turnover = pd.DataFrame(turnover_records).set_index(['Date', 'Portfolio'])
    years = len(portfolio_returns) / PERIODS_PER_YEAR
    trading = turnover.groupby('Portfolio').sum()
    trading['Estimated short-borrow cost'] = pd.Series(borrow_cost_totals)
    trading['Estimated total implementation cost'] = (trading['Estimated cost']
                                                       + trading['Estimated short-borrow cost'])
    trading['Annualized one-way turnover'] = trading['One-way turnover'] / years
    trading['Cost assumption (bps)'] = transaction_cost_bps
    trading = trading.reindex(methods)
    return dict(returns=returns, covariance=covariance, prior=prior, posterior=posterior,
                views=views, weights=weights, bab_diagnostics=bab_diagnostics,
                weight_history=target_history,
                turnover=turnover, trading=trading, historical=historical, model=model,
                portfolio_returns=portfolio_returns, evaluation_start=evaluation.index[0],
                evaluation_end=evaluation.index[-1], training_days=training_days,
                transaction_cost_bps=transaction_cost_bps,
                annual_short_borrow_bps=annual_short_borrow_bps,
                kelly_fraction=kelly_fraction, bab_gross_limit=bab_gross_limit,
                views_as_of=view_records[-1]['Publication date'] if register else (views_as_of if configured_views else None),
                configured_view_count=sum(len(r.get('views', [])) for r in register if r['enabled']) if register else len(configured_views),
                view_history=pd.DataFrame(view_records).set_index('Date'),
                solver_history=pd.DataFrame(solver_records).set_index(['Date', 'Start']),
                cash_returns=cash_series, cash_label=cash_label,
                view_register=register, max_weight=max_weight, bab_failure_policy=bab_failure_policy, training_window_days=training_window_days,
                covariance_estimator=covariance_estimator, apply_registered_views=apply_registered_views)


def charts(result, label):
    import matplotlib.pyplot as plt
    weights_figure, ax = plt.subplots(figsize=(11, 5))
    (result['weights'] * 100).plot.bar(ax=ax)
    ax.set(title=f'{label}\nLatest walk-forward target weights', ylabel='Allocation (%)', xlabel='Asset label')
    ax.legend(fontsize=8)
    weights_figure.tight_layout()
    growth_figure, ax = plt.subplots(figsize=(11, 5))
    rets = result['portfolio_returns']
    growth = (1 + rets).cumprod()
    initial = pd.DataFrame(1.0, index=[rets.index[0] - pd.Timedelta(days=1)], columns=rets.columns)
    growth = pd.concat([initial, growth])
    growth.plot(ax=ax)
    ax.set(title=f'{label}\nWalk-forward growth - portfolio returns are after stated costs',
           ylabel='Growth of 1 unit', xlabel='Date')
    ax.legend(fontsize=8)
    growth_figure.tight_layout()
    return weights_figure, growth_figure


def save_run(result, provenance, annual_rf, max_weight, parent='outputs'):
    """Save each run separately and carry the data-mode label into every result."""
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    target = parent / f'{provenance["mode"]}_{name}'
    target.mkdir(exist_ok=False)
    for key in ['weights', 'weight_history', 'turnover', 'trading', 'historical',
                'model', 'portfolio_returns', 'covariance', 'views', 'bab_diagnostics',
                'view_history', 'solver_history']:
        table = result[key].copy()
        table.insert(0, 'Data source', provenance['label'])
        table.to_csv(target / f'{key}.csv')
    result['cash_returns'].to_csv(target / 'cash_returns.csv')
    expected_returns = pd.DataFrame({'Prior annual excess return': result['prior'],
                                     'BL posterior annual excess return': result['posterior']})
    expected_returns.insert(0, 'Data source', provenance['label'])
    expected_returns.to_csv(target / 'black_litterman_returns.csv')
    metadata = {**provenance, 'annual_risk_free_assumption': annual_rf,
                'max_asset_weight': max_weight, 'return_rows_used': len(result['returns']),
                'training_days_before_first_evaluation': result['training_days'],
                'evaluation_start': str(result['evaluation_start'].date()),
                'evaluation_end': str(result['evaluation_end'].date()),
                'rebalance_rule': 'monthly plus registered-view expiry; first earned-return dates recorded',
                'training_window_days': result['training_window_days'],
                'covariance_estimator': result['covariance_estimator'],
                'view_register': result['view_register'],
                'apply_registered_views': result['apply_registered_views'],
                'bab_failure_policy': result['bab_failure_policy'],
                'execution_contract': 'fit after close t-2, execute close t-1, first earned return ends t',
                'cash_model': result['cash_label'],
                'cash_returns_sha256': hashlib.sha256(result['cash_returns'].to_csv().encode()).hexdigest(),
                'transaction_cost_bps_per_one_way_turnover': result['transaction_cost_bps'],
                'annual_short_borrow_bps': result['annual_short_borrow_bps'],
                'kelly_fraction': result['kelly_fraction'],
                'kelly_definition': 'complete-month buy-and-hold log-growth objective; fraction scales capped full-Kelly risky weights; fixed annual_rf cash forecast',
                'borrow_accounting': 'daily short charges debited from cash; weights normalized by after-borrow NAV',
                'missing_price_policy': 'notebook audits requested exchange sessions and rejects missing quotes; library aligned_returns rejects internal gaps',
                'bab_gross_limit': result['bab_gross_limit'],
                'portfolio_methods': list(result['weights'].columns),
                'universe_selection': 'fixed eight ETFs selected retrospectively in the 2024 study',
                'views_as_of': result['views_as_of'],
                'configured_view_count': result['configured_view_count'],
                'active_view_count': len(result['views']),
                'view_activation_rule': 'publication date strictly before fit cutoff t-2; execute t-1; monthly rebalances only',
                'first_view_activation': (str(result['view_history'].query('`Active views` > 0').index[0].date())
                                          if result['view_history']['Active views'].gt(0).any() else None),
                'evaluation': ('retrospective scenario with chronological walk-forward parameter fitting; '
                               'the 2024-selected universe is applied to earlier dates; '
                               'only explicitly supplied views are active; '
                               'not a point-in-time out-of-sample strategy test')}
    (target / 'run_info.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return target
