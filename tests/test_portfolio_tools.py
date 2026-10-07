"""Offline behavioral checks for the maintained portfolio workflow."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from portfolio_tools import (ASSETS, BENCHMARK, aligned_returns, analyze,
                             historical_metrics, load_prices, save_run)


class PortfolioChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prices, cls.info = load_prices()

    def test_generated_prices_are_repeatable_and_labelled(self):
        other, info = load_prices()
        pd.testing.assert_frame_equal(other, self.prices)
        self.assertIn('not real', info['label'])
        self.assertEqual(info['mode'], 'synthetic')
        self.assertEqual(info['prices_csv_sha256'], self.info['prices_csv_sha256'])

    def test_returns_never_cross_assets_or_fill_gaps(self):
        index = pd.bdate_range('2020-01-01', periods=300)
        prices = pd.DataFrame({'A': 100 * 1.001 ** np.arange(300),
                               'B': 10000 * 0.999 ** np.arange(300)}, index=index)
        prices.loc[index[40], 'A'] = np.nan
        returns = aligned_returns(prices)
        self.assertNotIn(index[40], returns.index)
        self.assertNotIn(index[41], returns.index)
        np.testing.assert_allclose(returns['A'], .001, atol=1e-12)
        np.testing.assert_allclose(returns['B'], -.001, atol=1e-12)

    def test_drawdown_includes_starting_capital(self):
        metrics = historical_metrics(pd.Series([-.2, .1]), annual_rf=0)
        self.assertAlmostEqual(metrics['Max drawdown'], -.2)
        self.assertAlmostEqual(metrics['Annual mean'], -.05 * 252)
        self.assertAlmostEqual(metrics['Annual volatility'], np.std([-.2, .1], ddof=1) * np.sqrt(252))

    def test_annualized_metrics_have_consistent_units(self):
        daily = pd.Series(np.tile([.001, -.0005], 126))
        metrics = historical_metrics(daily, .03)
        expected_sharpe = (daily - ((1.03)**(1/252) - 1)).mean() * np.sqrt(252) / daily.std()
        self.assertAlmostEqual(metrics['Sharpe'], expected_sharpe)
        self.assertAlmostEqual(metrics['CAGR'], (1 + daily).prod() - 1)

    def test_valid_allocations_and_models(self):
        result = analyze(self.prices)
        weights = result['weights']
        np.testing.assert_allclose(weights.sum(), 1, atol=1e-7)
        core = ['Equal weight', 'Minimum variance', 'BL maximum Sharpe',
                'Minimum tracking error', 'Higher-moment utility']
        self.assertTrue((weights.loc[ASSETS, core].to_numpy() >= -1e-7).all())
        self.assertTrue((weights.loc[ASSETS, core].to_numpy() <= .35 + 1e-7).all())
        np.testing.assert_allclose(result['weight_history'].sum(axis=1), 1, atol=1e-7)
        self.assertTrue(np.isfinite(result['historical']).all().all())
        self.assertTrue(np.isfinite(result['model']).all().all())
        sigma = result['covariance'].to_numpy()
        equal = weights.loc[ASSETS, 'Equal weight'].to_numpy()
        minimum = weights.loc[ASSETS, 'Minimum variance'].to_numpy()
        self.assertLessEqual(minimum @ sigma @ minimum, equal @ sigma @ equal + 1e-8)
        self.assertGreaterEqual(result['model'].loc['BL maximum Sharpe', 'Expected Sharpe'],
                                result['model'].loc['Equal weight', 'Expected Sharpe'] - 1e-6)
        self.assertEqual(result['portfolio_returns'].index.min(), result['evaluation_start'])
        self.assertGreater(result['evaluation_start'], result['returns'].index[503])
        self.assertTrue((result['trading']['One-way turnover'] >= 1).all())
        self.assertTrue((result['trading']['Estimated cost'] > 0).all())
        self.assertGreater(result['trading'].loc['BAB beta-neutral',
                                                 'Estimated short-borrow cost'], 0)
        self.assertAlmostEqual(result['trading'].loc['Equal weight',
                                                     'Estimated short-borrow cost'], 0)
        np.testing.assert_allclose(weights.sum(axis=0), 1, atol=1e-7)

    def test_walk_forward_weights_do_not_see_future_prices(self):
        baseline = analyze(self.prices, training_days=504)
        changed = self.prices.copy()
        cutoff = baseline['evaluation_start'] + pd.offsets.MonthBegin(3)
        changed.loc[changed.index >= cutoff, ASSETS] *= np.linspace(1.0, 2.0, len(ASSETS))
        amended = analyze(changed, training_days=504)
        early = baseline['weight_history'].index.get_level_values('Date') < cutoff
        pd.testing.assert_frame_equal(baseline['weight_history'].loc[early],
                                     amended['weight_history'].loc[early])

    def test_transaction_costs_reduce_walk_forward_wealth(self):
        no_cost = analyze(self.prices, transaction_cost_bps=0)
        with_cost = analyze(self.prices, transaction_cost_bps=25)
        for name in no_cost['weights'].columns:
            gross_wealth = (1 + no_cost['portfolio_returns'][name]).prod()
            net_wealth = (1 + with_cost['portfolio_returns'][name]).prod()
            self.assertLess(net_wealth, gross_wealth)

    def test_infeasible_cap_explains_problem(self):
        with self.assertRaisesRegex(ValueError, 'MAX_WEIGHT'):
            analyze(self.prices, max_weight=.10)

    def test_invalid_dates_and_mode_are_explicit_errors(self):
        with self.assertRaisesRegex(ValueError, 'earlier'):
            load_prices(start='2024-01-01', end='2020-01-01')
        with self.assertRaisesRegex(ValueError, 'DATA_MODE'):
            load_prices(mode='typo')

    def test_yahoo_error_does_not_generate_fallback_data(self):
        with patch('yfinance.download', side_effect=ConnectionError('offline')):
            with self.assertRaisesRegex(RuntimeError, 'download failed'):
                load_prices(mode='yahoo')
        with patch('yfinance.download', return_value=pd.DataFrame()):
            with self.assertRaisesRegex(ValueError, 'no usable prices'):
                load_prices(mode='yahoo')

    def test_yahoo_table_keeps_asset_order_and_adjustment_settings(self):
        raw = self.prices.copy()
        raw.columns = pd.MultiIndex.from_product([['Close'], raw.columns])
        with patch('yfinance.download', return_value=raw) as download:
            prices, info = load_prices(mode='yahoo')
        self.assertEqual(list(prices.columns), ASSETS + [BENCHMARK])
        self.assertTrue(download.call_args.kwargs['auto_adjust'])
        self.assertEqual(info['mode'], 'yahoo')
        self.assertNotIn('seed', info)

    def test_export_labels_data_and_never_replaces_a_previous_run(self):
        result = analyze(self.prices)
        with tempfile.TemporaryDirectory() as temp:
            first = save_run(result, self.info, .03, .35, temp)
            before = (first / 'weights.csv').read_bytes()
            second = save_run(result, self.info, .03, .35, temp)
            self.assertNotEqual(first, second)
            self.assertEqual(before, (first / 'weights.csv').read_bytes())
            self.assertIn('SYNTHETIC VALIDATION', before.decode())
            self.assertTrue((second / 'run_info.json').is_file())
            self.assertTrue((second / 'turnover.csv').is_file())
            metadata = (second / 'run_info.json').read_text(encoding='utf-8')
            self.assertIn('walk-forward', metadata)


if __name__ == '__main__':
    unittest.main()
