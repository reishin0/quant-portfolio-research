"""Chronological experiments, paired uncertainty and portfolio diagnostics.

All candidate outcomes are retained. These are retrospective experiments, not a
claim of an untouched holdout or prospective performance.
"""
import numpy as np
import pandas as pd

from portfolio_tools import ASSETS, BENCHMARK, analyze, historical_metrics
from research_extensions import _numeric_frame
from research_diagnostics import evaluate_targets, performance_table


def run_research_experiments(prices, cash_returns=None, view_register=None,
                             development_start='2022-01-04', development_end='2023-12-31',
                             evaluation_start='2024-01-01', annual_rf=.03,
                             max_weight=.35, transaction_cost_bps=10,
                             annual_short_borrow_bps=100, training_days=504,
                             kelly_fraction=.5, bab_gross_limit=2.):
    """Select one configuration using development minimum-variance volatility only.

    Candidate windows/estimators are fixed before this run, but the entire historical
    sample has already been inspected. Evaluation never participates in selection.
    Every evaluation starts from cash on a common date and pays its initial turnover.
    """
    start, end, later = map(pd.Timestamp, [development_start, development_end, evaluation_start])
    if not start < end < later or prices.index.max() < later:
        raise ValueError('Need disjoint chronological development and evaluation windows.')
    development_prices = prices.loc[:end]
    development_cash = None if cash_returns is None else cash_returns.loc[development_prices.index[1:]]
    candidates = [('expanding_sample', None, 'sample'), ('252_sample', 252, 'sample'),
                  ('504_sample', 504, 'sample'), ('504_ledoit_wolf', 504, 'ledoit_wolf')]
    common = dict(annual_rf=annual_rf, max_weight=max_weight, training_days=training_days,
                  transaction_cost_bps=transaction_cost_bps,
                  annual_short_borrow_bps=annual_short_borrow_bps,
                  kelly_fraction=kelly_fraction, bab_gross_limit=bab_gross_limit,
                  view_register=[] if view_register is None else view_register, bab_failure_policy='cash')
    development, evaluations, rows = {}, {}, []
    dates = None
    for label, window, estimator in candidates:
        result = analyze(development_prices, cash_returns=development_cash,
                         training_window_days=window, covariance_estimator=estimator,
                         evaluation_start_date=start, **common)
        if dates is not None and not dates.equals(result['portfolio_returns'].index):
            raise ValueError('Candidate development dates differ.')
        dates = result['portfolio_returns'].index
        development[label] = result
        metric = result['historical'].loc['Minimum variance']
        rows.append({'Configuration': label, 'Window': 'expanding' if window is None else str(window),
                     'Estimator': estimator, 'Development first': str(dates[0].date()),
                     'Development last': str(dates[-1].date()), 'Development sessions': len(dates),
                     'Selection score: minimum-variance volatility': metric['Annual volatility'],
                     'Development CAGR': metric['CAGR'], 'Development Sharpe': metric['Sharpe']})
    registry = pd.DataFrame(rows).set_index('Configuration')
    # Stable tie break by declared configuration label, never by evaluation outcome.
    selected = registry.sort_values(['Selection score: minimum-variance volatility', 'Configuration']).index[0]
    registry['Selected on development'] = registry.index == selected
    for label, window, estimator in candidates:
        evaluations[label] = analyze(prices, cash_returns=cash_returns,
                                    training_window_days=window, covariance_estimator=estimator,
                                    evaluation_start_date=later, **common)
    selected_result = evaluations[selected]
    eval_dates = selected_result['portfolio_returns'].index
    if any(not r['portfolio_returns'].index.equals(eval_dates) for r in evaluations.values()):
        raise ValueError('Candidate evaluation dates differ.')
    comparison = pd.concat({label: r['historical'] for label, r in evaluations.items()}, names=['Configuration', 'Portfolio'])
    # Same schedule, covariance, constraints and costs isolate the registered views.
    prior_result = analyze(prices, cash_returns=cash_returns,
                           training_window_days=selected_result['training_window_days'],
                           covariance_estimator=selected_result['covariance_estimator'],
                           evaluation_start_date=later, apply_registered_views=False, **common)
    if not prior_result['weight_history'].index.equals(selected_result['weight_history'].index):
        raise ValueError('Prior and views comparison must use identical execution schedules.')
    return {'registry': registry, 'selected': selected, 'result': selected_result,
            'development': development, 'evaluations': evaluations,
            'evaluation_comparison': comparison, 'prior_result': prior_result,
            'development_end': str(end.date()), 'evaluation_start': str(later.date())}


def paired_block_bootstrap(returns, cash_returns, benchmark='Equal weight',
                           block_length=21, replications=2000, seed=42, confidence=.95):
    """Paired circular moving-block percentile intervals for CAGR/Sharpe differences.

    Resample identical contiguous indices for every strategy and cash. Preserve
    within-block dependence and cross-strategy pairing. Targets are not refitted;
    intervals are conditional on the realized strategy paths and stationarity.
    Pointwise intervals are unadjusted for the many research comparisons.
    """
    data = _numeric_frame(returns, 'bootstrap returns', minimum_rows=60)
    if (benchmark not in data or not cash_returns.index.equals(data.index)
            or not np.isfinite(cash_returns).all() or (data <= -1).any().any()
            or (cash_returns <= -1).any() or not isinstance(block_length, int)
            or not 1 <= block_length <= len(data) // 2
            or not isinstance(replications, int) or replications < 200
            or not 0 < confidence < 1):
        raise ValueError('Invalid bootstrap inputs, pairing, block length or replication count.')
    names, values, cash = list(data), data.to_numpy(), cash_returns.to_numpy()
    n, columns = values.shape
    base = names.index(benchmark)

    def statistics(v, c):
        growth = np.expm1(np.log1p(v).mean(axis=0) * 252)
        excess = v - c[:, None]
        vol = excess.std(axis=0, ddof=1)
        sharpe = np.divide(excess.mean(axis=0) * np.sqrt(252), vol,
                           out=np.full(columns, np.nan), where=vol > 1e-15)
        return np.stack([growth - growth[base], sharpe - sharpe[base]], axis=1)

    rng = np.random.default_rng(seed)
    samples = np.empty((replications, columns, 2))
    blocks = int(np.ceil(n / block_length))
    for b in range(replications):
        starts = rng.integers(0, n, size=blocks)
        indices = ((starts[:, None] + np.arange(block_length)) % n).ravel()[:n]
        samples[b] = statistics(values[indices], cash[indices])
    point = statistics(values, cash)
    tail = (1 - confidence) / 2
    rows = []
    for j, name in enumerate(names):
        if name == benchmark:
            continue
        for k, metric in enumerate(['CAGR difference', 'Sharpe difference']):
            draws = samples[:, j, k]
            finite = draws[np.isfinite(draws)]
            lower, upper = np.quantile(finite, [tail, 1 - tail]) if len(finite) else [np.nan, np.nan]
            rows.append({'Portfolio': name, 'Metric': metric, 'Estimate': point[j, k],
                         'Lower': lower, 'Upper': upper, 'Block sessions': block_length,
                         'Replications': replications, 'Finite replicates': len(finite),
                         'Benchmark': benchmark, 'Confidence': confidence,
                         'Inference': 'pointwise, conditional, exploratory'})
    return pd.DataFrame(rows).set_index(['Portfolio', 'Metric'])


def drawdown_duration(returns):
    """Longest/current underwater run in observed sessions, including initial NAV=1."""
    values = np.asarray(returns, dtype=float)
    if not len(values) or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError('Drawdown needs finite returns above -100%.')
    wealth = np.r_[1., np.cumprod(1 + values)]
    drawdown = wealth / np.maximum.accumulate(wealth) - 1
    longest, current = 0, 0
    for value in drawdown[1:]:
        current = current + 1 if value < -1e-12 else 0
        longest = max(longest, current)
    return {'Longest underwater sessions': longest, 'Current underwater sessions': current}


def portfolio_risk_diagnostics(result):
    """Exposure, concentration, signed risk contribution and realized BAB market beta."""
    history = result['weight_history']
    risky = history[ASSETS]
    gross = risky.abs().sum(axis=1)
    target_exposure = pd.DataFrame({'Target gross risky': gross, 'Target net risky': risky.sum(axis=1),
                                    'Target cash': history['Cash'],
                                    'Target max absolute weight': risky.abs().max(axis=1),
                                    'Risky HHI (absolute normalized)': risky.abs().div(gross.replace(0, np.nan), axis=0).pow(2).sum(axis=1)})
    # HHI is undefined for an all-cash portfolio, not zero concentration.
    target_exposure.loc[gross < 1e-12, 'Risky HHI (absolute normalized)'] = np.nan
    summary = target_exposure.groupby('Portfolio').mean()
    summary = summary.join(result['trading'][['Annualized one-way turnover', 'Estimated total implementation cost']])
    durations = pd.DataFrame({name: drawdown_duration(result['portfolio_returns'][name]) for name in result['weights']}).T
    summary = summary.join(durations)
    sigma = result['covariance'].to_numpy()
    contributions = {}
    for name in result['weights']:
        w = result['weights'].loc[ASSETS, name].to_numpy()
        variance = w @ sigma @ w
        contributions[name] = w * (sigma @ w) / variance if variance > 1e-15 else np.full(len(w), np.nan)
    risk_share = pd.DataFrame(contributions, index=ASSETS)
    excess = result['portfolio_returns'].sub(result['cash_returns'].loc[result['portfolio_returns'].index], axis=0)
    beta = excess['BAB beta-neutral'].rolling(63).cov(excess[BENCHMARK]) / excess[BENCHMARK].rolling(63).var()
    return {'summary': summary, 'target_exposure': target_exposure,
            'latest_signed_variance_contributions': risk_share,
            'realized_bab_beta': beta.rename('63-session realized excess-return beta').to_frame()}


def financing_sensitivity(result, transaction_costs=(0, 10, 25), borrow_costs=(0, 100, 300), annual_rf=.03):
    """Replay fixed target paths on a declared cost grid; no cost-aware refitting."""
    dates = result['portfolio_returns'].index
    cash = result['cash_returns'].loc[dates]
    rows, paths = [], {}
    for cost in transaction_costs:
        for borrow in borrow_costs:
            for name in result['weights']:
                target = result['weight_history'].xs(name, level='Portfolio')
                series, _ = evaluate_targets(result['returns'].loc[dates, ASSETS], target,
                                             annual_rf, cost, borrow, cash_returns=cash)
                metrics = historical_metrics(series, annual_rf, cash_returns=cash)
                rows.append({'Transaction bps': cost, 'Borrow bps': borrow, 'Portfolio': name, **metrics})
                paths[(cost, borrow, name)] = series
    return pd.DataFrame(rows).set_index(['Transaction bps', 'Borrow bps', 'Portfolio']), paths


def view_confidence_sensitivity(prices, selected_result, annual_rf=.03, confidence_levels=(.25, .5, .75)):
    """Change model confidence only for explicitly enabled sets; never invent views."""
    import copy
    register = selected_result['view_register']
    columns = ['Confidence', 'Portfolio', 'Status', 'CAGR', 'Sharpe', 'Max drawdown']
    if not any(r['enabled'] for r in register):
        return pd.DataFrame([{'Confidence': c, 'Portfolio': 'BL maximum Sharpe',
                              'Status': 'Not estimable: no enabled numerical view sets'} for c in confidence_levels], columns=columns)
    rows = []
    for confidence in confidence_levels:
        modified = copy.deepcopy(register)
        for record in modified:
            if record['enabled']:
                for view in record['views']:
                    view['confidence'] = confidence
                    view['uncertainty_basis'] = 'Research sensitivity override; not provider confidence.'
        run = analyze(prices, annual_rf=annual_rf, max_weight=selected_result['max_weight'],
                      training_days=selected_result['training_days'],
                      kelly_fraction=selected_result['kelly_fraction'], bab_gross_limit=selected_result['bab_gross_limit'],
                      transaction_cost_bps=selected_result['transaction_cost_bps'],
                      annual_short_borrow_bps=selected_result['annual_short_borrow_bps'],
                      cash_returns=selected_result['cash_returns'], view_register=modified,
                      training_window_days=selected_result['training_window_days'],
                      covariance_estimator=selected_result['covariance_estimator'],
                      evaluation_start_date=selected_result['evaluation_start'],
                      bab_failure_policy=selected_result['bab_failure_policy'])
        rows.append({'Confidence': confidence, 'Portfolio': 'BL maximum Sharpe',
                     'Status': 'Evaluated' if run['view_history']['Active views'].gt(0).any() else 'No eligible view in evaluated dates',
                     **run['historical'].loc['BL maximum Sharpe'].to_dict()})
    return pd.DataFrame(rows)


def research_summary(experiment, intervals, risk):
    """One source of headline numbers: evaluation metrics, intervals and exposures."""
    result = experiment['result']
    table = result['historical'].copy()
    table['CAGR minus equal weight'] = table['CAGR'] - table.loc['Equal weight', 'CAGR']
    table['Sharpe minus equal weight'] = table['Sharpe'] - table.loc['Equal weight', 'Sharpe']
    for metric, prefix in [('CAGR difference', 'CAGR delta'), ('Sharpe difference', 'Sharpe delta')]:
        subset = intervals.xs(metric, level='Metric')
        table[f'{prefix} lower'] = subset['Lower']
        table[f'{prefix} upper'] = subset['Upper']
    table = table.join(risk['summary'])
    table['Configuration'] = experiment['selected']
    table['Interpretation'] = 'Retrospective; conditional pointwise intervals; no prospective claim'
    return table
