"""Frozen-design integrity, vintage preservation and chronological admission."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from data_tools import load_sofr_cash_returns
from forward_evaluation import (ROOT, check_extension, evaluate_forward, freeze_protocol,
                                notebook_digest, verify_protocol)

class ForwardChecks(unittest.TestCase):
    def test_freeze_is_exclusive_and_calculations_are_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'protocol.json';f=freeze_protocol(p)
            self.assertEqual(verify_protocol(p),f)
            with self.assertRaises(FileExistsError):freeze_protocol(p)
            f['file_sha256']['jpm_views.py']='0'*64;p.write_text(json.dumps(f))
            with self.assertRaisesRegex(ValueError,'Frozen file changed'):verify_protocol(p)

    def test_notebook_outputs_do_not_change_code_identity(self):
        n=json.loads((ROOT/'portfolio_construction.ipynb').read_text(encoding='utf8'))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'n.ipynb';p.write_text(json.dumps(n));a=notebook_digest(p)
            code=next(c for c in n['cells'] if c['cell_type']=='code');code['outputs']=[];code['execution_count']=99
            p.write_text(json.dumps(n));self.assertEqual(a,notebook_digest(p))
            code['source']='x=123\n';p.write_text(json.dumps(n));self.assertNotEqual(a,notebook_digest(p))

    def test_history_revision_and_inserted_dates_rejected(self):
        old=pd.DataFrame({'A':[1.,2.]},index=pd.to_datetime(['2026-10-01','2026-10-02']))
        new=old.copy();new.loc[pd.Timestamp('2026-10-05')]=3.;check_extension(old,new,'Test')
        changed=new.copy();changed.iloc[0,0]+=.01
        with self.assertRaisesRegex(ValueError,'revised'):check_extension(old,changed,'Test')
        inserted=new.copy();inserted.loc[pd.Timestamp('2026-09-30')]=1.
        with self.assertRaisesRegex(ValueError,'historical date'):check_extension(old,inserted.sort_index(),'Test')

    def test_only_later_complete_decision_execution_return_triplet_admitted(self):
        # Generated extension is a TEST FIXTURE, never exported as evidence.
        prices=pd.read_csv(ROOT/'data/etf_adjusted_20261009.csv',index_col='Date',parse_dates=True)
        valuations=pd.read_csv(ROOT/'data/gld_valuation_20261009.csv',index_col='Date',parse_dates=True)
        cash,_=load_sofr_cash_returns(prices.index)
        f={'prices_file':'data/etf_adjusted_20261009.csv','views_file':'data/jpm_research_views_20261009.json',
           'decision_cutoff_date':'2026-10-09','training_window_days':252,'covariance_estimator':'sample',
           'annual_rf':.03,'max_weight':.35,'transaction_cost_bps':10.,'annual_short_borrow_bps':100.}
        self.assertIsNone(evaluate_forward(f,prices,cash,valuations,now='2026-10-09T12:00:00Z'))
        dates=pd.bdate_range('2026-10-09','2026-10-19')
        price_extension=pd.DataFrame(np.tile(prices.iloc[-1].values,(len(dates),1)),index=dates,columns=prices.columns)
        gold_extension=pd.DataFrame(np.tile(valuations.iloc[-1].values,(len(dates),1)),index=dates,columns=valuations.columns)
        extended=pd.concat([prices,price_extension]);gold=pd.concat([valuations,gold_extension])
        cash=pd.concat([cash,pd.Series(.0001,index=dates)])
        with self.assertRaisesRegex(ValueError,'unfinished'):evaluate_forward(f,extended,cash,gold,now='2026-10-09T12:00:00Z')
        r=evaluate_forward(f,extended,cash,gold,now='2026-10-20T12:00:00Z')
        self.assertEqual(r['returns'].index[0],pd.Timestamp('2026-10-14'))
        self.assertEqual(r['audit'].iloc[0]['Decision close'],pd.Timestamp('2026-10-12'))
        self.assertEqual(r['audit'].iloc[0]['Execution close'],pd.Timestamp('2026-10-13'))
        self.assertTrue(r['audit'].Evidence.str.contains('subsequent').all())
        self.assertEqual(len(r['returns']),4)

if __name__=='__main__':unittest.main()
