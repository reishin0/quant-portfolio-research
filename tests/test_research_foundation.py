"""Analytical and failure-mode checks for the stages 1–3 research contract."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from data_tools import audit_prices, load_price_snapshot, load_sofr_cash_returns
from portfolio_tools import (ASSETS, BENCHMARK, analyze, black_litterman,
                             historical_metrics, load_prices, optimize_weights,
                             portfolio_step)
from research_diagnostics import evaluate_targets, mean_variance_weights
from research_extensions import fractional_kelly_weights, higher_moment_weights

ROOT = Path(__file__).resolve().parents[1]


class AnalyticalChecks(unittest.TestCase):
    def test_two_asset_optima_match_closed_forms(self):
        names = ['A', 'B']
        covariance = pd.DataFrame(np.diag([.04, .09]), index=names, columns=names)
        mu = pd.Series([.08, .09], index=names)
        rng = np.random.default_rng(5)
        history = pd.DataFrame(rng.normal(0, .02, (500, 2)), columns=names)
        weights = optimize_weights(mu, covariance, history, history @ [.3, .7], cap=1)
        inverse_var = np.array([1 / .04, 1 / .09])
        np.testing.assert_allclose(weights['Minimum variance'], inverse_var / inverse_var.sum(), atol=2e-6)
        tangency = np.linalg.solve(covariance, mu)
        np.testing.assert_allclose(weights['BL maximum Sharpe'], tangency / tangency.sum(), atol=2e-6)
        np.testing.assert_allclose(weights['Minimum tracking error'], [.3, .7], atol=2e-6)
        with self.assertRaisesRegex(ValueError, 'positive definite'):
            optimize_weights(mu, covariance * 0, history, history.A, cap=1)

    def test_two_asset_bl_gain_and_uncertainty_match_scalar_update(self):
        sigma = pd.DataFrame(np.diag([.04, .09]), index=['A', 'B'], columns=['A', 'B'])
        d = black_litterman(sigma, tau=.2, risk_aversion=2, views=[('A', 'B', .1, .8)], return_details=True)
        prior = np.array([.04, .09])
        projected = .2 * (.04 + .09)
        omega = projected * .2 / .8
        gain = .2 * np.array([.04, -.09]) / (projected + omega)
        np.testing.assert_allclose(d['posterior'], prior + gain * (.1 - (prior[0] - prior[1])))
        np.testing.assert_allclose(d['mean_covariance'], .2 * sigma - np.outer(gain, .2 * np.array([.04, -.09])))
        p, post, _ = black_litterman(sigma)
        np.testing.assert_array_equal(p, post)

    def test_mean_variance_interior_gradient_is_zero(self):
        covariance = pd.DataFrame([[.04, .01], [.01, .09]], index=['A', 'B'], columns=['A', 'B'])
        mu = pd.Series([.01, .02], index=covariance.index)
        w = mean_variance_weights(mu, covariance, risk_aversion=2, cap=1)
        np.testing.assert_allclose(mu - 2 * covariance @ w, 0, atol=2e-7)

    def test_monthly_kelly_matches_binary_bet_solution(self):
        dates = pd.bdate_range('2020-01-01', '2022-08-31')
        returns = pd.DataFrame(0., index=dates, columns=['A'])
        last = returns.groupby(returns.index.to_period('M')).tail(1).index
        # 30 interior months: probability .6 of doubling, .4 of losing half.
        # d/df [.6 log(1+f)+.4 log(1-.5f)] = 0 at f=.8.
        returns.loc[last[1:-1], 'A'] = np.r_[np.ones(18), np.full(12, -.5)]
        full = fractional_kelly_weights(returns, annual_rf=0, fraction=1, cap=1)
        half = fractional_kelly_weights(returns, annual_rf=0, fraction=.5, cap=1)
        self.assertAlmostEqual(full.A, .8, places=5)
        self.assertAlmostEqual(half.A, .4, places=5)
        returns.loc[last[[0, -1]], 'A'] = 5
        np.testing.assert_allclose(full, fractional_kelly_weights(returns, 0, 1, 1))

    def test_higher_moment_rejects_infeasible_solver_success(self):
        r = pd.DataFrame(np.random.default_rng(3).normal(0, .01, (300, 4)))
        invalid = SimpleNamespace(success=True, x=np.array([1., 0, 0, 0]), fun=-.1, message='claimed success')
        with patch('research_extensions.minimize', return_value=invalid) as solver:
            with self.assertRaisesRegex(RuntimeError, 'no feasible solution'):
                higher_moment_weights(r, cap=.35)
            self.assertEqual(solver.call_count, 4)
        actual = higher_moment_weights(r, cap=.35)
        self.assertTrue(all(x['Valid'] for x in actual.attrs['solver_attempts']))
        self.assertAlmostEqual(actual.sum(), 1)
        self.assertLessEqual(actual.max(), .35 + 1e-7)

    def test_variable_cash_sharpe_uses_excess_volatility(self):
        r = pd.Series([.01, -.02, .005])
        cash = pd.Series([.001, .002, .003])
        metrics = historical_metrics(r, cash_returns=cash)
        excess = r - cash
        self.assertAlmostEqual(metrics['Sharpe'], excess.mean() / excess.std() * np.sqrt(252))
        self.assertTrue(np.isnan(historical_metrics(cash, cash_returns=cash)['Sharpe']))

    def test_signed_holdings_ledger_matches_currency_account(self):
        w = np.array([.8, -.3])
        cash = .5
        r = np.array([.1, -.2])
        net, closing, balance, fee = portfolio_step(w, cash, r, .001, .0002, .002)
        assets_dollars = .998 * w * (1 + r)
        cash_dollars = .998 * (cash * 1.001 - .3 * .0002)
        nav = assets_dollars.sum() + cash_dollars
        self.assertAlmostEqual(net, nav - 1)
        np.testing.assert_allclose(closing, assets_dollars / nav)
        self.assertAlmostEqual(balance, cash_dollars / nav)
        self.assertAlmostEqual(fee, .3 * .0002)


class InputChecks(unittest.TestCase):
    def test_frozen_load_is_repeatable_and_rejects_changed_bytes(self):
        source = ROOT / 'data/etf_snapshot_20261009.json'
        args = (ASSETS + [BENCHMARK], '2020-01-01', '2026-10-09')
        a, manifest = load_price_snapshot(source, *args)
        b, _ = load_price_snapshot(source, *args)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in [source.name, manifest['price_file'], manifest['actions_file']]:
                shutil.copyfile(source.parent / name, folder / name)
            with (folder / manifest['price_file']).open('ab') as stream:
                stream.write(b'\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                load_price_snapshot(folder / source.name, *args)

    def test_calendar_distinguishes_missing_session_from_holiday(self):
        # July 4 is a US exchange holiday; July 3 remains a session.
        dates = pd.to_datetime(['2024-07-01', '2024-07-02', '2024-07-03', '2024-07-05'])
        prices = pd.DataFrame({'A': [100, 101, 120, 121]}, index=dates)
        actions = pd.DataFrame({'Date': ['2024-07-03'], 'ETF': ['A'], 'Action': ['Stock Splits'], 'Value': [2.]})
        _, flags = audit_prices(prices, '2024-07-01', '2024-07-06', actions)
        self.assertEqual(len(flags), 1)
        self.assertIn('Stock Splits', flags.iloc[0]['Corporate action'])
        with self.assertRaisesRegex(ValueError, 'missing='):
            audit_prices(prices.drop(index=dates[1]), '2024-07-01', '2024-07-06')

    def test_sofr_weekend_simple_accrual_then_compounding(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            csv = folder / 'cash.csv'
            csv.write_text('observation_date,SOFR\n2024-07-05,5\n2024-07-08,6\n2024-07-09,6\n')
            manifest = folder / 'manifest.json'
            manifest.write_text(json.dumps({'file': csv.name, 'sha256': hashlib.sha256(csv.read_bytes()).hexdigest()}))
            dates = pd.to_datetime(['2024-07-05', '2024-07-08', '2024-07-09'])
            returns, _ = load_sofr_cash_returns(dates, manifest)
            np.testing.assert_allclose(returns, [.05 * 3 / 360, .06 / 360], atol=1e-15)
            self.assertAlmostEqual((1 + returns).prod(), (1 + .05 * 3 / 360) * (1 + .06 / 360))
            with self.assertRaisesRegex(ValueError, 'coverage'):
                load_sofr_cash_returns(pd.to_datetime(['2024-07-05', '2024-07-20']), manifest)


class TimingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prices, _ = load_prices(mode='synthetic')
        cls.prices = cls.prices.iloc[:550]
        cls.cash = pd.Series(np.linspace(.00001, .0002, len(cls.prices) - 1), index=cls.prices.index[1:])
        cls.result = analyze(cls.prices, cash_returns=cls.cash)

    def test_execution_close_cannot_enter_target_fit(self):
        first = self.result['view_history'].iloc[0]
        effective = self.result['evaluation_start']
        self.assertLess(first['Decision close'], first['Execution close'])
        self.assertLess(first['Execution close'], effective)
        changed = self.prices.copy()
        changed.loc[first['Execution close'], ASSETS] *= np.linspace(.9, 1.1, len(ASSETS))
        result = analyze(changed, cash_returns=self.cash)
        pd.testing.assert_frame_equal(self.result['weight_history'].loc[effective], result['weight_history'].loc[effective])
        self.assertFalse(np.allclose(self.result['portfolio_returns'].loc[effective], result['portfolio_returns'].loc[effective]))

    def test_replay_matches_main_cash_and_cost_accounting(self):
        result = self.result
        dates = result['portfolio_returns'].index
        for name in ['Fractional Kelly', 'BAB beta-neutral']:
            returns, _ = evaluate_targets(result['returns'].loc[dates, ASSETS],
                result['weight_history'].xs(name, level='Portfolio'), cash_returns=self.cash.loc[dates])
            np.testing.assert_allclose(returns, result['portfolio_returns'][name], atol=1e-14)
        np.testing.assert_array_equal(result['portfolio_returns']['Cash proxy'], self.cash.loc[dates])


if __name__ == '__main__':
    unittest.main()
