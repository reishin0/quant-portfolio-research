"""Research-design, chronology and independent statistical checks."""
import copy
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from portfolio_tools import ASSETS, analyze, load_prices
from research_extensions import (FACTOR_COLUMNS, eligible_view_set, estimate_covariance,
                                 factor_regression, validate_view_register)
from research_validation import (drawdown_duration, paired_block_bootstrap,
                                 portfolio_risk_diagnostics, run_research_experiments,
                                 view_confidence_sensitivity)


def view_set(identifier='v1', published='2021-01-01', valid='2021-01-02', expires='2022-03-01'):
    return dict(id=identifier, enabled=True, source_url='https://example.org/test-fixture',
                source_title='Synthetic test fixture; not a real forecast',
                published_on=published, recorded_on=published, valid_from=valid,
                expires_on=expires, horizon_months=12,
                return_definition='annual_arithmetic_total_return_spread',
                mapping_assumptions='Test-only relative ETF scenario', classification='research_assumption',
                views=[dict(long='GLD', short='MTUM', annual_spread=.04,
                            confidence=.5, uncertainty_basis='Test-only assumed confidence')])


class ViewRegisterChecks(unittest.TestCase):
    def test_publication_mapping_date_activation_and_expiry(self):
        record = view_set()
        record['recorded_on'], record['valid_from'] = '2021-02-01', '2021-02-02'
        register = validate_view_register([record], ASSETS)
        self.assertEqual(eligible_view_set(register, '2021-02-01', '2021-02-02'), ([], None))
        self.assertEqual(eligible_view_set(register, '2021-02-02', '2021-02-03')[1], 'v1')
        self.assertEqual(eligible_view_set(register, '2022-02-28', '2022-03-01'), ([], None))

    def test_newer_expired_set_does_not_resurrect_old_set(self):
        records = [view_set(expires='2023-01-01'), view_set('v2', '2021-06-01', '2021-06-02', '2021-07-01')]
        validate_view_register(records, ASSETS)
        self.assertEqual(eligible_view_set(records, '2021-06-10', '2021-06-11')[1], 'v2')
        self.assertEqual(eligible_view_set(records, '2021-07-02', '2021-07-05'), ([], None))

    def test_invalid_views_fail_before_evaluation(self):
        for key, value in [('horizon_months', 6), ('expires_on', '2020-01-01'),
                           ('source_url', ''), ('return_definition', 'price target'),
                           ('recorded_on', '2026-01-01')]:
            record = view_set(); record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_view_register([record], ASSETS)
        for key in ['horizon_months', 'return_definition']:
            record = view_set(); del record[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                validate_view_register([record], ASSETS)
        record = view_set(); record['views'][0]['confidence'] = 1
        with self.assertRaises(ValueError):
            validate_view_register([record], ASSETS)

    def test_expiry_rebalances_and_prior_control_uses_identical_dates(self):
        prices, _ = load_prices(end='2022-04-01')
        record = view_set(expires='2022-02-15')
        viewed = analyze(prices, view_register=[record])
        prior = analyze(prices, view_register=[record], apply_registered_views=False)
        pd.testing.assert_index_equal(viewed['weight_history'].index, prior['weight_history'].index)
        history = viewed['view_history']
        self.assertTrue(history['Active views'].gt(0).any())
        self.assertTrue((history.loc[history['Active views'].gt(0), 'Publication date'] == record['published_on']).all())
        exit_row = history.loc[history['Execution close'] >= pd.Timestamp(record['expires_on'])].iloc[0]
        self.assertEqual(exit_row['Execution close'], pd.Timestamp('2022-02-15'))
        self.assertEqual(exit_row['Active views'], 0)
        self.assertTrue((history.loc[history['Execution close'] >= '2022-02-15', 'Active views'] == 0).all())
        pd.testing.assert_series_equal(viewed['portfolio_returns']['Equal weight'], prior['portfolio_returns']['Equal weight'])


class StatisticalChecks(unittest.TestCase):
    def test_hac_matches_independent_bartlett_sandwich(self):
        rng = np.random.default_rng(7)
        index = pd.date_range('2015-01-31', periods=120, freq='ME')
        factors = pd.DataFrame(rng.normal(0, .02, (120, 5)), index=index, columns=FACTOR_COLUMNS)
        factors['RF'] = .001
        errors = np.zeros(120)
        for t in range(1, 120): errors[t] = .7 * errors[t - 1] + rng.normal(0, .01)
        asset = pd.DataFrame({'A': .002 + factors.RF + factors['Mkt-RF'] + errors})
        result = factor_regression(asset, factors, hac_lags=3)
        x = np.column_stack([np.ones(120), factors[FACTOR_COLUMNS]])
        y = (asset.A - factors.RF).to_numpy()
        beta = np.linalg.lstsq(x, y, rcond=None)[0]
        scores = x * (y - x @ beta)[:, None]
        meat = scores.T @ scores
        for lag in range(1, 4):
            gamma = scores[lag:].T @ scores[:-lag]
            meat += (1 - lag / 4) * (gamma + gamma.T)
        bread = np.linalg.inv(x.T @ x)
        expected = bread @ meat @ bread * 120 / (120 - 6)
        self.assertAlmostEqual(result.loc['A', 'Annual alpha HAC SE'], np.sqrt(expected[0, 0]) * 12)
        self.assertAlmostEqual(result.loc['A', 'Annual alpha'], beta[0] * 12)
        self.assertGreaterEqual(result.loc['A', 'Alpha HAC Holm p'], result.loc['A', 'Alpha HAC p'])

    def test_shrinkage_psd_scaling_and_singular_sample(self):
        rng = np.random.default_rng(2)
        a = rng.normal(0, .01, 60)
        frame = pd.DataFrame({'A': a, 'B': a, 'C': rng.normal(0, .02, 60)})
        estimate = estimate_covariance(frame, 'ledoit_wolf')
        self.assertGreater(np.linalg.eigvalsh(estimate).min(), 0)
        np.testing.assert_allclose(estimate_covariance(frame * 2, 'ledoit_wolf'), estimate * 4)
        np.testing.assert_allclose(estimate_covariance(frame), frame.cov() * 252)

    def test_paired_bootstrap_identity_and_repeatability(self):
        rng = np.random.default_rng(11)
        dates = pd.bdate_range('2020-01-01', periods=150)
        values = rng.normal(.0005, .01, 150)
        returns = pd.DataFrame({'Equal weight': values, 'Copy': values}, index=dates)
        cash = pd.Series(.0001, index=dates)
        a = paired_block_bootstrap(returns, cash, replications=200)
        b = paired_block_bootstrap(returns, cash, replications=200)
        pd.testing.assert_frame_equal(a, b)
        np.testing.assert_array_equal(a[['Estimate', 'Lower', 'Upper']], 0)
        with self.assertRaises(ValueError):
            paired_block_bootstrap(returns, cash.iloc[::-1], replications=200)

    def test_drawdown_duration_counts_initial_loss_and_recovery(self):
        result = drawdown_duration([-.1, 0, 1 / .9 - 1, -.1, -.1, 0])
        self.assertEqual(result['Longest underwater sessions'], 3)
        self.assertEqual(result['Current underwater sessions'], 3)


class DesignChecks(unittest.TestCase):
    def test_infeasible_bab_is_explicit_cash_only_when_requested(self):
        prices, _ = load_prices(end='2022-02-01')
        message = 'BAB construction requires positive average beta in both legs.'
        with patch('portfolio_tools.bab_weights', side_effect=ValueError(message)):
            with self.assertRaisesRegex(ValueError, 'positive average beta'):
                analyze(prices)
            result = analyze(prices, bab_failure_policy='cash')
        target = result['weight_history'].xs('BAB beta-neutral', level='Portfolio')
        np.testing.assert_array_equal(target[ASSETS], 0)
        np.testing.assert_array_equal(target.Cash, 1)
        np.testing.assert_allclose(result['portfolio_returns']['BAB beta-neutral'],
                                   result['portfolio_returns']['Cash proxy'])
        self.assertTrue(result['view_history']['BAB construction'].str.startswith('cash:').all())

    def test_future_changes_cannot_change_development_choice(self):
        # Exercise the selector's boundaries with a deterministic oracle to keep
        # this timing test independent of numerical optimization performance.
        dates = pd.bdate_range('2020-01-01', '2024-02-01')
        prices = pd.DataFrame({'A': np.arange(len(dates)) + 100.}, index=dates)
        received = []

        def oracle(p, evaluation_start_date=None, training_window_days=None, covariance_estimator=None, **kwargs):
            index = p.loc[pd.Timestamp(evaluation_start_date):].index
            received.append((p.index[-1], p.iloc[-1, 0]))
            score = float(p.iloc[-1, 0]) + (training_window_days or 1000) / 1000
            history = pd.DataFrame({'Annual volatility': [score], 'CAGR': [.1], 'Sharpe': [1.]}, index=['Minimum variance'])
            return {'portfolio_returns': pd.DataFrame({'Minimum variance': .001}, index=index),
                    'historical': history, 'weight_history': pd.DataFrame({'A': [1.]}, index=index[:1]),
                    'training_window_days': training_window_days, 'covariance_estimator': covariance_estimator}

        with patch('research_validation.analyze', side_effect=oracle):
            baseline = run_research_experiments(prices)
            changed = prices.copy(); changed.loc['2024-01-01':] *= 10
            amended = run_research_experiments(changed)
        pd.testing.assert_frame_equal(baseline['registry'], amended['registry'])
        self.assertEqual(baseline['selected'], amended['selected'])
        self.assertTrue(all(d < pd.Timestamp('2024-01-01') for d, _ in received[:4]))

    def test_prior_only_confidence_grid_is_explicitly_not_estimable(self):
        table = view_confidence_sensitivity(None, {'view_register': []})
        self.assertEqual(len(table), 3)
        self.assertTrue(table.CAGR.isna().all())
        self.assertTrue(table.Status.str.contains('Not estimable').all())


if __name__ == '__main__':
    unittest.main()
