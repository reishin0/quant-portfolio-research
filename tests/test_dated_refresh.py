import hashlib
import unittest
from pathlib import Path
import pandas as pd
from forward_evaluation import check_extension, verify_protocol
from run_updated_analysis import build_updated_notebook,append_research_review

ROOT=Path(__file__).resolve().parents[1]


class DatedRefreshTests(unittest.TestCase):
    def test_derivative_preserves_frozen_source_and_provenance(self):
        path=ROOT/'portfolio_construction.ipynb'
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        nb,amendment=build_updated_notebook(ROOT/'data/refresh_20261016')
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
        verify_protocol(ROOT/'data/forward_protocol_20261009.json')
        self.assertEqual(sum(c.cell_type=='code' for c in nb.cells),54)
        self.assertEqual(amendment['end_exclusive'],'2026-10-16')
        code='\n'.join(c.source for c in nb.cells if c.cell_type=='code')
        self.assertIn('DATED REFRESH - adjusted ETF prices retrieved 16 October 2026',code)
        self.assertNotIn('data/etf_snapshot_20261009.json',code)
        self.assertIn('factor_path.name == "ff5_monthly.csv"',code)
        self.assertTrue(all(not c.outputs and c.execution_count is None for c in nb.cells if c.cell_type=='code'))

    def test_new_price_vintage_is_rejected_by_original_contract(self):
        old=pd.read_csv(ROOT/'data/etf_adjusted_20261009.csv',index_col='Date',parse_dates=True)
        new=pd.read_csv(ROOT/'data/refresh_20261016/etf_adjusted.csv',index_col='Date',parse_dates=True)
        with self.assertRaisesRegex(ValueError,'revised previously frozen'):
            check_extension(old,new,'Prices')

    def test_review_is_embedded_without_changing_executed_code(self):
        nb,_=build_updated_notebook(ROOT/'data/refresh_20261016')
        code=[c.source for c in nb.cells if c.cell_type=='code']
        append_research_review(nb);append_research_review(nb)
        self.assertEqual(code,[c.source for c in nb.cells if c.cell_type=='code'])
        self.assertEqual(sum(c.id=='dated-refresh-results' for c in nb.cells),1)
        self.assertEqual(sum(c.id=='intraday-investigation-results' for c in nb.cells),1)
        self.assertEqual(len(nb.metadata['dated_review_sha256']),2)


if __name__=='__main__':unittest.main()
