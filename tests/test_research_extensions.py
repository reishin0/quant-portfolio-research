"""Behavioral checks for factor, higher-moment, BAB and Kelly methods."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from research_extensions import (FACTOR_COLUMNS, bab_weights, factor_regression,
                                 fractional_kelly_weights, higher_moment_weights,
                                 load_fama_french_csv, monthly_compound)


class ResearchExtensionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(7)
        cls.dates = pd.bdate_range('2018-01-01', periods=900)
        market = rng.normal(.0003, .009, len(cls.dates))
        cls.benchmark = pd.Series(market, index=cls.dates, name='Market')
        betas = np.array([.4, .6, .8, 1.0, 1.2, 1.4, 1.6, 1.8])
        noise = rng.normal(0, .004, (len(cls.dates), len(betas)))
        cls.returns = pd.DataFrame(market[:, None] * betas + noise,
                                   index=cls.dates,
                                   columns=[f'A{i}' for i in range(len(betas))])

    def test_monthly_compounding_is_geometric(self):
        daily = pd.DataFrame({'A': np.tile([.1, -.1], 20)},
                             index=pd.bdate_range('2024-01-02', periods=40))
        result = monthly_compound(daily, trim_boundary_months=False)
        january = daily.loc['2024-01', 'A']
        expected = (1 + january).prod() - 1
        self.assertAlmostEqual(result.iloc[0, 0], expected)

    def test_factor_file_requires_explicit_unit_and_converts_percent(self):
        months = pd.period_range('2020-01', periods=30, freq='M')
        frame = pd.DataFrame({'Date': months.strftime('%Y%m'),
                              **{name: np.full(30, 1.0) for name in FACTOR_COLUMNS},
                              'RF': np.full(30, .2)})
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path = Path(folder) / 'factors.csv'
            frame.to_csv(path, index=False)
            factors = load_fama_french_csv(path, unit='percent')
        self.assertAlmostEqual(factors.iloc[0]['Mkt-RF'], .01)
        self.assertAlmostEqual(factors.iloc[0]['RF'], .002)

    def test_factor_regression_recovers_known_market_loading(self):
        rng = np.random.default_rng(11)
        dates = pd.date_range('2015-01-31', periods=80, freq='ME')
        factors = pd.DataFrame(rng.normal(0, .02, (80, 5)), index=dates,
                               columns=FACTOR_COLUMNS)
        factors['RF'] = .001
        assets = pd.DataFrame({'Known beta': .001 + factors['RF']
                               + 1.5 * factors['Mkt-RF']}, index=dates)
        result = factor_regression(assets, factors)
        self.assertAlmostEqual(result.loc['Known beta', 'Mkt-RF loading'], 1.5, places=8)
        self.assertAlmostEqual(result.loc['Known beta', 'Annual alpha'], .012, places=8)
        self.assertAlmostEqual(result.loc['Known beta', 'R-squared'], 1.0, places=8)

    def test_higher_moment_and_kelly_constraints(self):
        higher = higher_moment_weights(self.returns, cap=.30)
        kelly = fractional_kelly_weights(self.returns, fraction=.5, cap=.30)
        self.assertAlmostEqual(higher.sum(), 1)
        self.assertGreaterEqual(higher.min(), -1e-8)
        self.assertLessEqual(higher.max(), .30 + 1e-8)
        self.assertAlmostEqual(kelly.sum(), .5)
        self.assertGreaterEqual(kelly.min(), -1e-8)
        self.assertLessEqual(kelly.max(), .30 + 1e-8)

    def test_bab_is_beta_neutral_and_gross_bounded(self):
        weights, diagnostics = bab_weights(self.returns, self.benchmark, gross_limit=2)
        self.assertAlmostEqual(weights.abs().sum(), 2)
        self.assertAlmostEqual(diagnostics.attrs['portfolio_beta'], 0, places=10)
        self.assertTrue((weights > 0).any())
        self.assertTrue((weights < 0).any())


if __name__ == '__main__':
    unittest.main()
