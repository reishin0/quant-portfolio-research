import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from portfolio_amendments import (feasible_cash_scale,common_risk_pair,basis_walkforward,
    forecast_calibration,horizon_status,append_paper_decision,verify_decision_journal,evaluate_paper_interval,replay_common_risk)


class CommonRiskTests(unittest.TestCase):
    def test_future_price_changes_cannot_change_earlier_rebalance_targets(self):
        root=Path(__file__).resolve().parents[1];inputs=root/'data/refresh_20261016'
        prices=pd.read_csv(inputs/'etf_adjusted.csv',index_col='Date',parse_dates=True)
        cash=pd.read_csv(inputs/'cash_returns.csv',index_col='Date',parse_dates=True)['Cash return']
        doc=json.loads((inputs/'jpm_research_views.json').read_text(encoding='utf-8'))
        schedule=pd.to_datetime(['2026-08-03','2026-09-01','2026-10-01'])
        first=replay_common_risk(prices,cash,doc['forecast'],doc['allocation_policy'],schedule)
        changed=prices.copy();changed.loc['2026-10-02':,'VUG']*=1.2
        second=replay_common_risk(changed,cash,doc['forecast'],doc['allocation_policy'],schedule)
        for key in first['targets']:pd.testing.assert_frame_equal(first['targets'][key],second['targets'][key])
        self.assertTrue(first['audit'].Status.eq('MATCHED').all())
        self.assertLess(first['audit']['Risk gap'].abs().max(),1e-8)

    def test_closed_form_initial_scales(self):
        sigma=pd.DataFrame(np.diag([.04,.09]),index=['A','B'],columns=['A','B'])
        directions={'one':pd.Series([1.,0.],index=sigma.index),'two':pd.Series([0.,1.],index=sigma.index)}
        currents={k:pd.Series([0.,0.,1.],index=['A','B','Cash']) for k in directions}
        targets,audit=common_risk_pair(directions,currents,sigma,cap=1.,initial=True)
        np.testing.assert_allclose(targets['one'],[1,0,0],atol=1e-8)
        np.testing.assert_allclose(targets['two'],[0,2/3,1/3],atol=1e-8)
        np.testing.assert_allclose(audit['Actual ex ante volatility'],.2,atol=1e-8)

    def test_cash_is_in_turnover(self):
        lo,hi=feasible_cash_scale([.5,.5],[0,0,1],cap=1,turnover_limit=.1)
        self.assertAlmostEqual(lo,0);self.assertAlmostEqual(hi,.1)

    def test_no_shared_risk_is_exposed_without_forced_trade(self):
        cov=pd.DataFrame(np.diag([.04,.09]),index=['A','B'],columns=['A','B'])
        d={'one':pd.Series([1.,0.],index=cov.index),'two':pd.Series([0.,1.],index=cov.index)}
        current={'one':pd.Series([1.,0.,0.],index=['A','B','Cash']),'two':pd.Series([0.,0.,1.],index=['A','B','Cash'])}
        targets,audit=common_risk_pair(d,current,cov,cap=1.,turnover_limit=.1)
        self.assertTrue(audit.Status.eq('INFEASIBLE_HOLD_BOTH').all())
        for k in targets:pd.testing.assert_series_equal(targets[k],current[k])

    def test_asset_cap_and_initial_exception(self):
        self.assertAlmostEqual(feasible_cash_scale([.8,.2],[0,0,1],cap=.4,initial=True)[1],.5)
        with self.assertRaises(ValueError):feasible_cash_scale([.5,.5],[.1,0,.9],initial=True)


class CalibrationTests(unittest.TestCase):
    def test_future_basis_does_not_change_past_estimates(self):
        dates=pd.bdate_range('2026-01-01',periods=70)
        prices=pd.DataFrame({'GLD':100+np.sin(np.arange(70))},index=dates)
        nav=pd.DataFrame({'NAV per share':100.},index=dates)
        _,a=basis_walkforward(prices,nav);changed=prices.copy();changed.iloc[60:]*=2
        _,b=basis_walkforward(changed,nav)
        pd.testing.assert_frame_equal(a.iloc[:20],b.iloc[:20])
        self.assertTrue((a['Training end']<a.Date).all())

    def test_forecast_insufficient_cycles_retain_default(self):
        record={'id':'Q','period_start':'2026-07-01','period_end':'2026-09-30','published_on':'2026-07-03',
                'available_at_utc':'2026-10-09T00:00:00Z','actual':4400.,'target':4300.,'outcome_definition_verified':False}
        result=forecast_calibration([record],'2026-10-16T00:00:00Z')
        self.assertEqual(result['eligible_cycles'],0);self.assertEqual(result['forecast_sigma'],.1)
        self.assertIn('lead horizon',result['audit'][0]['reason'])

    def test_shrinkage_math_and_duplicate_cycle_exclusion(self):
        rows=[]
        for i in range(8):
            q=pd.Period('2023Q1',freq='Q')+i
            rows.append({'id':str(q),'period_start':str(q.start_time.date()),'period_end':str(q.end_time.date()),
                'published_on':str((q.start_time-pd.Timedelta(days=1)).date()),'available_at_utc':(q.end_time.tz_localize('UTC')+pd.Timedelta(days=2)).isoformat(),
                'actual':120.,'target':100.,'outcome_definition_verified':True})
        result=forecast_calibration(rows+[rows[-1]],'2026-10-16T00:00:00Z')
        self.assertEqual(result['eligible_cycles'],8)
        self.assertAlmostEqual(result['forecast_sigma'],np.sqrt((8*.04+8*.01)/16))
        future=copy.deepcopy(rows);future[0]['available_at_utc']='2030-01-01T00:00:00Z'
        self.assertEqual(forecast_calibration(future,'2026-10-16T00:00:00Z')['eligible_cycles'],7)

    def test_horizons_skip_weekend_and_quarter_stays_pending(self):
        r=horizon_status({'period_end':'2026-12-31','minimum_remaining_days':30},'2026-10-16T06:00:00Z')
        self.assertTrue(r['next_execution_close_utc'].startswith('2026-10-16'))
        self.assertTrue(r['first_return_close_utc'].startswith('2026-10-19'))
        self.assertLess(r['remaining_active_return_sessions'],60)
        self.assertFalse(r['completed_quarter_score_admitted']);self.assertFalse(r['strategy_inference_admitted'])


class JournalTests(unittest.TestCase):
    def payload(self):
        now=pd.Timestamp.now(tz='UTC')
        return {'decision_id':'test','inputs_available_at_utc':(now-pd.Timedelta(hours=1)).isoformat(),
            'execution_close_utc':(now+pd.Timedelta(days=1)).isoformat(),'first_return_close_utc':(now+pd.Timedelta(days=2)).isoformat(),
            'solver_status':'MATCHED','targets':{'one':{'A':.5,'Cash':.5}},'transaction_cost_bps':10.,'starting_state':'ALL_CASH_NEW_PAPER_ACCOUNT'}

    def test_append_duplicate_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.payload();entry=append_paper_decision(d,p)
            self.assertEqual(verify_decision_journal(d)[0],entry)
            with self.assertRaisesRegex(ValueError,'Duplicate'):append_paper_decision(d,p)
            file=Path(d)/'000001.json';doc=json.loads(file.read_text());doc['targets']['one']['A']=.7;file.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'tamper'):verify_decision_journal(d)

    def test_no_backdating_or_unavailable_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.payload();p['recorded_at_utc']='2000-01-01T00:00:00Z'
            with self.assertRaises(ValueError):append_paper_decision(d,p)
            p=self.payload();p['inputs_available_at_utc']=p['execution_close_utc']
            with self.assertRaises(ValueError):append_paper_decision(d,p)

    def test_independent_outcome_math_and_early_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            entry=append_paper_decision(d,self.payload())
            times=[pd.Timestamp(entry[k]).tz_convert('America/New_York').tz_localize(None).normalize() for k in ['execution_close_utc','first_return_close_utc']]
            prices=pd.DataFrame({'A':[100.,110.]},index=times)
            with self.assertRaises(ValueError):evaluate_paper_interval(entry,prices,.001)
            result=evaluate_paper_interval(entry,prices,.001,now=entry['first_return_close_utc'])
            self.assertAlmostEqual(result.iloc[0]['Net interval return'],(1-.0005)*(1+.5*.1+.5*.001)-1)


class AmendedNotebookTests(unittest.TestCase):
    def test_baseline_cells_unchanged_and_new_functions_inline(self):
        import ast
        from run_amended_analysis import build_amended_notebook
        from run_updated_analysis import build_updated_notebook,ROOT
        old,_=build_updated_notebook(ROOT/'data/refresh_20261016');new,_=build_amended_notebook()
        sources={c.id:c.source for c in new.cells if c.cell_type=='code'}
        for c in old.cells:
            if c.cell_type=='code':self.assertEqual(c.source,sources[c.id])
        self.assertEqual(len(sources),58)
        module=ast.parse((ROOT/'portfolio_amendments.py').read_text(encoding='utf-8'))
        inline=ast.parse(sources['amended-methodology-implementation'])
        module_functions={n.name:ast.dump(n) for n in module.body if isinstance(n,ast.FunctionDef)}
        inline_functions={n.name:ast.dump(n) for n in inline.body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(module_functions,inline_functions)
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module in ['portfolio_tools','jpm_views','portfolio_amendments'] for n in inline.body))


if __name__=='__main__':unittest.main()
