"""Economic identities and source-coverage checks for restored notebook analyses."""
import ast
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

from portfolio_tools import ASSETS, aligned_returns, black_litterman, portfolio_step
from research_extensions import FACTOR_COLUMNS, fractional_kelly_weights
from research_diagnostics import (capm_diagnostics, capped_proportional_weights,
                                  evaluate_targets, factor_fit_diagnostics, factor_tilt,
                                  higher_moment_diagnostics, mean_variance_weights,
                                  normalize_context, performance_table,
                                  rolling_market_model, select_rolling_window)

ROOT = Path(__file__).resolve().parents[1]


class RestoredResearchChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(102)
        cls.index = pd.bdate_range('2020-01-01', periods=600)
        cls.market = pd.Series(rng.normal(.0002, .01, 600), index=cls.index)
        cls.returns = pd.DataFrame(cls.market.to_numpy()[:, None] * np.arange(1, 9)[None, :] / 5
                                   + rng.normal(.0001, .004, (600, 8)), index=cls.index, columns=ASSETS)

    def test_missing_quote_cannot_erase_another_asset_gain(self):
        prices = pd.DataFrame(100., index=self.index, columns=['A', 'B'])
        prices.loc[self.index[300]:, 'B'] = 110.
        self.assertAlmostEqual((1 + aligned_returns(prices).B).prod(), 1.1)
        prices.loc[self.index[300], 'A'] = np.nan
        with self.assertRaisesRegex(ValueError, 'Internal missing prices'):
            aligned_returns(prices)

    def test_common_endpoints_trim_without_losing_internal_moves(self):
        prices = pd.DataFrame(100., index=self.index, columns=['A', 'B'])
        prices.loc[self.index[:5], 'A'] = np.nan
        prices.loc[self.index[-5:], 'B'] = np.nan
        result = aligned_returns(prices)
        self.assertEqual(result.index[0], self.index[6])
        self.assertEqual(result.index[-1], self.index[-6])

    def test_borrow_fees_debit_cash_without_changing_share_counts(self):
        w, cash, nav = np.array([1., -.5]), .5, 1.
        for day in range(2):
            net, w, cash, fee = portfolio_step(w, cash, [0., 0.], 0, .01)
            nav *= 1 + net
            np.testing.assert_allclose(w * nav, [1., -.5])
            self.assertAlmostEqual(cash * nav, .5 - .005 * (day + 1))
        self.assertAlmostEqual(nav, .99)

    def test_target_evaluation_matches_two_day_cash_ledger(self):
        daily = pd.DataFrame(0., index=self.index[:2], columns=['A', 'B'])
        targets = pd.DataFrame([[1., -.5, .5]], index=daily.index[:1], columns=['A', 'B', 'Cash'])
        net, _ = evaluate_targets(daily, targets, annual_rf=0, transaction_cost_bps=0,
                                   annual_short_borrow_bps=25200)
        self.assertAlmostEqual((1 + net).prod(), .99)

    def test_kelly_can_choose_cash_and_fractions_scale_one_optimum(self):
        negative = self.returns * 0 - .001
        np.testing.assert_allclose(fractional_kelly_weights(negative, annual_rf=0), 0, atol=1e-7)
        full = fractional_kelly_weights(self.returns, fraction=1)
        for fraction in [.5, .66]:
            np.testing.assert_allclose(fractional_kelly_weights(self.returns, fraction=fraction), full * fraction)

    def test_rolling_coefficients_do_not_see_current_or_later_returns(self):
        baseline = rolling_market_model(self.returns, self.market, 30)
        changed = self.returns.copy()
        changed.iloc[300:] += .20
        other = rolling_market_model(changed, self.market, 30)
        pd.testing.assert_frame_equal(baseline['beta'].iloc[:301], other['beta'].iloc[:301])
        pd.testing.assert_frame_equal(baseline['annual_alpha'].iloc[:301], other['annual_alpha'].iloc[:301])

    def test_window_selection_scores_conditional_returns_on_common_dates(self):
        exact = pd.DataFrame({'A': .001 + 1.5 * self.market})
        selected, scores = select_rolling_window(exact.iloc[:252], self.market.iloc[:252], annual_rf=0)
        self.assertIn(selected, [30, 60, 90])
        self.assertTrue((scores['Conditional return MSE'] < 1e-20).all())
        self.assertTrue((scores['Dates'] == 162).all())

    def test_capm_uses_its_own_benchmark(self):
        table = capm_diagnostics(pd.DataFrame({'M': self.market, 'Levered': 2 * self.market}), self.market, 0)
        self.assertAlmostEqual(table.loc['M', 'Beta'], 1)
        self.assertAlmostEqual(table.loc['Levered', 'Beta'], 2)
        self.assertAlmostEqual(table.loc['Levered', 'CAPM annual excess'], 2 * self.market.mean() * 252)

    def test_capping_redistributes_until_every_bound_is_satisfied(self):
        aum = pd.Series([1000000.] + [1.] * 19)
        w = capped_proportional_weights(aum, .1)
        self.assertAlmostEqual(w.sum(), 1)
        self.assertLessEqual(w.max(), .1 + 1e-10)
        with self.assertRaisesRegex(ValueError, 'feasible cap'):
            capped_proportional_weights(pd.Series(np.ones(8)), .1)

    def test_mean_variance_cash_solution_matches_scalar_optimum(self):
        mu, covariance = pd.Series({'A': .02}), pd.DataFrame([[.04]], index=['A'], columns=['A'])
        for risk in [1., 2., 4.]:
            w = mean_variance_weights(mu, covariance, risk, cap=1)
            self.assertAlmostEqual(w.A, .02 / (risk * .04), places=5)

    def test_tensor_contraction_matches_direct_portfolio_moments(self):
        weights = pd.Series(np.arange(1, 9) / 36, index=ASSETS)
        result = higher_moment_diagnostics(self.returns, weights.iloc[::-1])
        direct = self.returns @ weights
        self.assertLess(result['checks']['Absolute difference'].max(), 1e-8)
        self.assertAlmostEqual(result['checks'].loc['Skewness', 'Tensor contraction'], skew(direct, bias=True))
        self.assertAlmostEqual(result['checks'].loc['Excess kurtosis', 'Tensor contraction'], kurtosis(direct, bias=True))

    def test_bl_predictive_covariance_adds_posterior_mean_uncertainty(self):
        cov = self.returns.cov() * 252
        details = black_litterman(cov, return_details=True)
        np.testing.assert_allclose(details['predictive_covariance'], cov + details['mean_covariance'])
        self.assertGreaterEqual(np.linalg.eigvalsh(details['mean_covariance']).min(), -1e-10)
        np.testing.assert_allclose(details['P'].sum(axis=1), 0)

    def test_original_views_are_inactive_unless_explicitly_supplied(self):
        covariance = self.returns.cov() * 252
        prior, posterior, views = black_litterman(covariance)
        np.testing.assert_allclose(prior, posterior)
        self.assertTrue(views.empty)
        _, with_view, active = black_litterman(covariance, views=[('GLD', 'MTUM', .15, .9)])
        self.assertEqual(len(active), 1)
        self.assertFalse(np.allclose(prior, with_view))

    def test_current_configuration_does_not_activate_original_inputs(self):
        nb = json.loads((ROOT / 'portfolio_construction.ipynb').read_text(encoding='utf-8'))
        config = ''.join(next(c['source'] for c in nb['cells'] if c['id'] == 'configuration'))
        scope = {}
        exec(compile(config, 'configuration', 'exec'), scope)
        self.assertEqual(scope['DATA_MODE'], 'snapshot')
        self.assertEqual(scope['END_DATE'], '2026-10-09')
        self.assertEqual(scope['FACTOR_FILE'], 'data/F-F_Research_Data_5_Factors_2x3_monthly_20261009.csv')
        self.assertEqual(scope['INVESTOR_VIEWS'], [])
        self.assertFalse(scope['RUN_ORIGINAL_CONTEXT'])
        self.assertIn('# ORIGINAL 2024 SUBMISSION', config)
        self.assertIn('# DATA_MODE = "submission"', config)

    def test_fitted_returns_include_nonmarket_factors(self):
        rng = np.random.default_rng(22)
        factors = pd.DataFrame(rng.normal(0, .02, (60, 5)), index=pd.date_range('2018-01-31', periods=60, freq='ME'), columns=FACTOR_COLUMNS)
        factors['RF'] = .001
        returns = pd.DataFrame({'A': factors.RF + .002 + factors['Mkt-RF'] + 2 * factors.SMB})
        _, actual, fitted = factor_fit_diagnostics(returns, factors)
        np.testing.assert_allclose(actual, fitted, atol=1e-10)

    def test_monthly_metrics_and_factor_tilt_obey_units_and_caps(self):
        monthly = pd.DataFrame({'A': np.tile([.02, -.01], 12)})
        metrics = performance_table(monthly, annual_rf=0, periods_per_year=12)
        self.assertAlmostEqual(metrics.loc['A', 'Annual mean'], .06)
        self.assertAlmostEqual(metrics.loc['A', 'Sortino'], monthly.A.mean() * 12 / np.sqrt(np.mean(np.minimum(monthly.A, 0) ** 2) * 12))
        loadings = pd.DataFrame(np.ones((8, 5)), index=ASSETS)
        weights = pd.Series([.9] + [.1 / 7] * 7, index=ASSETS)
        tilted = factor_tilt(weights, loadings, .01, .008)
        self.assertAlmostEqual(tilted.sum(), 1)
        self.assertLessEqual(tilted.max(), .35 + 1e-10)

    def test_source_mapping_covers_all_code_cells_and_existing_destinations(self):
        nb = json.loads((ROOT / 'portfolio_construction.ipynb').read_text(encoding='utf-8'))
        mapping = nb['metadata']['source_reconciliation']
        self.assertEqual(len(mapping['cells']), 127)
        self.assertEqual(len({item['source_cell'] for item in mapping['cells']}), 127)
        ids = {cell['id'] for cell in nb['cells']}
        for item in mapping['cells']:
            self.assertTrue(set(item['target_cells']) <= ids)
            self.assertEqual(len(item['source_code_sha256']), 64)
        positions = {cell['id']: i for i, cell in enumerate(nb['cells'])}
        for appendix in ['aum-snapshot', 'factor-tilt-experiment', 'beta-spread', 'macro-context', 'network-context']:
            self.assertGreater(positions[appendix], positions['next-steps'])

    def test_notebook_contains_matching_calculation_implementations(self):
        nb = json.loads((ROOT / 'portfolio_construction.ipynb').read_text(encoding='utf-8'))
        cells = {c['id']: ''.join(c['source']) for c in nb['cells']}
        implementations = nb['metadata']['inline_implementations']
        self.assertEqual(len(implementations), 35)
        for item in implementations:
            module = ast.parse((ROOT / item['module']).read_text(encoding='utf-8'))
            expected = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == item['name'])
            actual = next(n for n in ast.parse(cells[item['cell_id']]).body
                          if isinstance(n, ast.FunctionDef) and n.name == item['name'])
            if item['name'] == 'load_prices':
                # Its input helpers are defined locally in the notebook instead.
                class RemoveLocalImport(ast.NodeTransformer):
                    def visit_ImportFrom(self, node):
                        return None if node.module == 'submission_data' else node
                expected = RemoveLocalImport().visit(expected)
            self.assertEqual(ast.dump(actual), ast.dump(expected), item['name'])

    def test_notebook_has_no_hidden_project_module_imports(self):
        nb = json.loads((ROOT / 'portfolio_construction.ipynb').read_text(encoding='utf-8'))
        local = {'portfolio_tools', 'research_extensions', 'research_diagnostics', 'submission_data', 'data_tools'}
        for cell in nb['cells']:
            if cell['cell_type'] != 'code':
                continue
            for node in ast.walk(ast.parse(''.join(cell['source']))):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, local, cell['id'])
                elif isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name in local for alias in node.names), cell['id'])

    def test_optional_network_cell_with_mocked_provider(self):
        nb = json.loads((ROOT / 'portfolio_construction.ipynb').read_text(encoding='utf-8'))
        code = ''.join(next(c['source'] for c in nb['cells'] if c['id'] == 'network-context'))
        symbols = ['^GSPC', '^N225', '^HSI', '000001.SS', '^STOXX50E', '^NSEI', 'GLD', '^TNX', '^VIX']
        prices = pd.DataFrame(np.arange(60)[:, None] + np.arange(9)[None, :] + 100.,
                              index=self.index[:60], columns=pd.MultiIndex.from_product([['Close'], symbols]))
        ticker = Mock()
        ticker.get_info.return_value = {'beta3Year': 1.2, 'totalAssets': 123.}
        ticker.history.return_value = pd.DataFrame({'Close': [4.]}, index=self.index[:1])
        scope = dict(RUN_NETWORK_CONTEXT=True, NETWORK_CONTEXT_START='2020-01-01', END_DATE='2020-06-01',
                     pd=pd, np=np, universe_prices=self.returns, capm_spy=pd.DataFrame({'Beta': 1.}, index=ASSETS),
                     diagnostic_tables={}, normalize_context=normalize_context, show_panels=lambda *a, **kw: None,
                     display=lambda *a: None)
        with patch('yfinance.download', return_value=prices), patch('yfinance.Ticker', return_value=ticker):
            exec(compile(code, 'network-context', 'exec'), scope)
        self.assertEqual(scope['network_provenance']['status'], 'downloaded')
        self.assertEqual(len(scope['diagnostic_tables']['optional_current_metadata']), 8)
        self.assertEqual(len(scope['network_provenance']['context_prices_csv_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
