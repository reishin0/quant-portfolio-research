"""Checks against the actual submission and malformed-input regressions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from portfolio_tools import ASSETS, BENCHMARK, aligned_returns, load_prices
from research_extensions import (FACTOR_COLUMNS, factor_regression,
                                 load_fama_french_csv, monthly_compound)
from submission_data import (DATA_DIR, load_inflation, load_liquidity,
                             load_submission_prices, verify_submission_files)


class SubmissionChecks(unittest.TestCase):
    def test_manifest_and_original_coverage(self):
        self.assertEqual(len(verify_submission_files()['files']), 7)
        prices = load_submission_prices()
        self.assertEqual(prices.shape, (1166, 21))
        self.assertEqual(str(prices.index[-1].date()), '2024-08-20')
        self.assertFalse(prices.isna().any().any())

    def test_submission_mode_uses_adjusted_closes_and_end_exclusive(self):
        prices, info = load_prices('submission', end='2024-08-20')
        raw = pd.read_csv(DATA_DIR / 'efts_dataset.csv')
        first = raw.loc[raw.ETF.eq('SPY')].iloc[0]
        self.assertAlmostEqual(prices.iloc[0]['SPY'], first['Adj Close'])
        self.assertNotAlmostEqual(prices.iloc[0]['SPY'], first['Close'])
        self.assertEqual(list(prices), ASSETS + [BENCHMARK])
        self.assertEqual(str(prices.index[-1].date()), '2024-08-19')
        self.assertFalse(info['aum_used'])
        self.assertEqual(len(info['source_file_sha256']), 64)

    def test_duplicate_keys_and_invalid_prices_are_rejected(self):
        row = {'Date':'2020-01-02','ETF':'SPY','Adj Close':100}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'prices.csv'
            pd.DataFrame([row, row]).to_csv(path,index=False)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                load_submission_prices(path)
            pd.DataFrame([{**row,'Adj Close':0}]).to_csv(path,index=False)
            with self.assertRaisesRegex(ValueError, 'positive'):
                load_submission_prices(path)

    def test_missing_symbol_is_not_substituted(self):
        with self.assertRaisesRegex(ValueError, 'missing symbols'):
            load_submission_prices(symbols=['ABSENT'])

    def test_inflation_named_series_survive_row_reordering(self):
        raw = pd.read_excel(DATA_DIR/'Inflation-data.xlsx',sheet_name='Aggregate')
        baseline = load_inflation()
        with patch('submission_data.pd.read_excel', return_value=raw.iloc[::-1]):
            shuffled = load_inflation()
        pd.testing.assert_frame_equal(baseline.sort_index(axis=1),shuffled.sort_index(axis=1))
        self.assertEqual(list(baseline.index[[0,-1]]), [1970,2023])
        self.assertAlmostEqual(baseline.loc[1970,'Median'], 4.37)

    def test_bis_series_survives_reordering_and_rejects_ambiguity(self):
        raw = pd.read_csv(DATA_DIR/'WS_GLI_csv_col.csv',dtype=str)
        expected = load_liquidity()
        with patch('submission_data.pd.read_csv', return_value=raw.iloc[::-1].reset_index(drop=True)):
            pd.testing.assert_series_equal(expected,load_liquidity())
        with patch('submission_data.pd.read_csv', return_value=pd.concat([raw,raw])):
            with self.assertRaisesRegex(ValueError,'exactly one'):
                load_liquidity()
        self.assertAlmostEqual(expected.loc['2023Q2'],41.279)

    def test_real_factors_have_declared_units_and_vintage(self):
        factors=load_fama_french_csv(DATA_DIR/'F-F_Research_Data_5_Factors_2x3_monthly.csv')
        self.assertEqual(len(factors),732)
        self.assertEqual(str(factors.index[-1].date()),'2024-06-30')
        self.assertAlmostEqual(factors.iloc[-1]['Mkt-RF'],.0278)

    def test_partial_boundary_months_are_not_fitted(self):
        prices,_=load_prices('submission')
        daily=aligned_returns(prices).loc['2022-01-03':]
        monthly=monthly_compound(daily)
        self.assertEqual(str(monthly.index[0].date()),'2022-02-28')
        self.assertEqual(str(monthly.index[-1].date()),'2024-07-31')
        factors=load_fama_french_csv(DATA_DIR/'F-F_Research_Data_5_Factors_2x3_monthly.csv')
        fitted=factor_regression(monthly,factors)
        self.assertTrue(fitted['Observations'].eq(29).all())
        self.assertTrue(fitted['Last month'].eq('2024-06-30').all())

    def test_regression_rejects_short_overlap_and_rank_deficiency(self):
        rng=np.random.default_rng(8)
        dates=pd.date_range('2020-01-31',periods=60,freq='ME')
        factors=pd.DataFrame(rng.normal(0,.01,(60,6)),index=dates,columns=FACTOR_COLUMNS+['RF'])
        assets=pd.DataFrame({'A':rng.normal(0,.02,60)},index=dates+pd.offsets.MonthEnd(40))
        with self.assertRaisesRegex(ValueError,'aligned months'):
            factor_regression(assets,factors)
        factors['SMB']=factors['HML']
        assets.index=dates
        with self.assertRaisesRegex(ValueError,'rank deficient'):
            factor_regression(assets,factors)


if __name__=='__main__':
    unittest.main()
