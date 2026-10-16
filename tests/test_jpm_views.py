"""Independent absolute-view math and dated reconstruction regression checks."""
import copy
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from portfolio_tools import ASSETS, analyze, black_litterman, load_prices
from jpm_views import mapped_price_target, run_jpm_view_study, stable_allocation, limit_execution


class AbsoluteViewChecks(unittest.TestCase):
    def test_absolute_posterior_matches_scalar_bayesian_update(self):
        covariance = pd.DataFrame(np.diag([.04, .09]), index=['A', 'B'], columns=['A', 'B'])
        result = black_litterman(covariance, views=[('A', None, .15, .25)], return_details=True)
        np.testing.assert_array_equal(result['P'], [[1, 0]])
        self.assertAlmostEqual(result['posterior']['A'], .75 * result['prior']['A'] + .25 * .15)
        self.assertAlmostEqual(result['posterior']['B'], result['prior']['B'])
        self.assertAlmostEqual(result['Omega'].iloc[0, 0], .1 * .04 * 3)
        self.assertGreater(np.linalg.eigvalsh(result['mean_covariance']).min(), 0)

    def test_mixed_absolute_and_relative_views_have_distinct_rows(self):
        cov = pd.DataFrame([[.04, .01], [.01, .09]], index=['A', 'B'], columns=['A', 'B'])
        result = black_litterman(cov, views=[('A', None, .1, .25), ('A', 'B', .02, .5)], return_details=True)
        np.testing.assert_array_equal(result['P'], [[1, 0], [1, -1]])
        self.assertTrue(np.isfinite(result['posterior']).all())


class MappingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecast = json.loads((Path(__file__).resolve().parents[1] / 'data/jpm_research_views_20261009.json').read_text())['forecast']
        cls.index = pd.bdate_range('2026-07-01','2026-12-31')
        cls.prices = pd.DataFrame({'GLD':400.},index=cls.index)
        cls.valuations = pd.DataFrame({'Ounces per share':.1,'NAV per share':400.},index=cls.index)

    def mapping(self, day='2026-08-03', **kwargs):
        return mapped_price_target(self.forecast,self.prices,day,valuations=self.valuations,**kwargs)

    def test_quarter_average_and_variance_independent_math(self):
        r=self.mapping()
        times=(pd.bdate_range('2026-10-01','2026-12-31')-pd.Timestamp('2026-08-03')).days.to_numpy()/365
        h=times.mean();conversion=.1*.996**h
        self.assertAlmostEqual(r['Mapped mean future ETF price'],conversion*4500)
        self.assertAlmostEqual(r['Annual excess Q'],(conversion*4500/400-1-(1.03**h-1))/h)
        self.assertAlmostEqual(r['Omega annual variance'],(conversion/400/h*450)**2+(.02/h)**2)

    def test_condition_on_observed_quarter_prices(self):
        r=self.mapping('2026-10-08')
        n=len(pd.bdate_range('2026-10-01','2026-12-31'));k=len(pd.bdate_range('2026-10-01','2026-10-08'))
        needed=(4500*n-4000*k)/(n-k)
        self.assertAlmostEqual(r['Mapped mean future ETF price'],.1*.996**r['Mean remaining years']*needed)
        self.assertGreater(r['Omega annual variance'],self.mapping()['Omega annual variance'])

    def test_no_prepublication_or_future_dependency(self):
        self.assertIsNone(self.mapping('2026-07-03'))
        a=self.mapping()
        v=self.valuations.copy();v.loc['2026-08-04':]*=2
        p=self.prices.copy();p.loc['2026-08-04':]*=2
        self.assertEqual(a,mapped_price_target(self.forecast,p,'2026-08-03',valuations=v))

    def test_expiry_and_missing_pair_fail(self):
        self.assertIsNone(self.mapping('2026-12-03'))
        with self.assertRaisesRegex(ValueError,'same-date'):
            mapped_price_target(self.forecast,self.prices,'2026-08-03',valuations=self.valuations.drop(pd.Timestamp('2026-08-03')))
        with self.assertRaisesRegex(ValueError,'observed price session'):
            mapped_price_target(self.forecast,self.prices,'2026-10-08',valuations=self.valuations.drop(pd.Timestamp('2026-10-02')))
        with self.assertRaises(ValueError):self.mapping(error_scale=0)


class StableAllocationChecks(unittest.TestCase):
    def test_explicit_omega_controls_bayesian_weight(self):
        cov=pd.DataFrame(np.diag([.04,.09]),index=['A','B'],columns=['A','B'])
        r=black_litterman(cov,views=[('A',None,.15,1.)],omega=[[.016]],return_details=True)
        self.assertAlmostEqual(r['posterior']['A'],.8*r['prior']['A']+.2*.15)
        self.assertAlmostEqual(r['views']['Effective marginal weight'].iloc[0],.2)
        for omega in [[[-1]],[[float('nan')]],[[0]],[[1,0]]]:
            with self.assertRaises(ValueError):black_litterman(cov,views=[('A',None,.15,1.)],omega=omega)

    def test_cost_penalty_reduces_trading_and_target_bounds_hold(self):
        cov=pd.DataFrame(np.eye(8)*.04,index=ASSETS,columns=ASSETS)
        mu=pd.Series(.03,index=ASSETS);mu['GLD']=.15
        old=pd.Series(.125,index=ASSETS)
        cheap=stable_allocation(mu,cov,old,transaction_cost_bps=0)
        costly=stable_allocation(mu,cov,old,transaction_cost_bps=100)
        self.assertLess(np.abs(costly-old).sum(),np.abs(cheap-old).sum())
        self.assertLessEqual(cheap.max(),.275+1e-8)
        self.assertAlmostEqual(cheap.sum(),1.)

    def test_execution_turnover_including_cash_and_initial_exception(self):
        old=pd.Series([.5,.5,0.],index=['A','B','Cash']);target=pd.Series([0.,1.,0.],index=old.index)
        filled,fraction=limit_execution(target,old,.1)
        np.testing.assert_allclose(filled,[.4,.6,0.]);self.assertAlmostEqual(fraction,.2)
        initial=pd.Series([0.,0.,1.],index=old.index)
        np.testing.assert_allclose(limit_execution(target,initial,.1,True)[0],target)
        with self.assertRaises(ValueError):limit_execution(target,old,.1,True)


class ReconstructionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prices,_=load_prices(end='2022-05-01')
        cls.base=analyze(cls.prices,bab_failure_policy='cash')
        cls.forecast=json.loads((Path(__file__).resolve().parents[1]/'data/jpm_research_views_20261009.json').read_text())['forecast']
        cls.forecast.update(published_on='2022-01-06',period_start='2022-02-01',period_end='2022-04-30')
        cls.valuations=pd.DataFrame({'Ounces per share':.1,'NAV per share':cls.prices.GLD},index=cls.prices.index)
        cls.forecast['target_usd_per_ounce']=float(cls.prices.GLD.loc['2022-01-06'])*11
        cls.study=run_jpm_view_study(cls.prices,cls.base,cls.forecast,valuations=cls.valuations)

    def test_timing_costs_and_turnover_have_independent_ledger_agreement(self):
        r=self.study;a=r['audit']
        self.assertTrue((a.loc[a.Active,'Decision close']>pd.Timestamp('2022-01-06')).all())
        self.assertTrue((a['Mapping recorded']=='2026-10-09').all())
        for label,t in r['targets'].items():
            np.testing.assert_allclose(t.sum(axis=1),1.)
            ledger=r['ledgers'][label]
            self.assertTrue((ledger['One-way turnover'].iloc[1:]<=.1+1e-8).all())
            np.testing.assert_allclose(ledger['One-way turnover'],r['control_audit'].xs(label,level='Strategy')['One-way turnover'],atol=1e-9)
        expired=a['Execution close']>=r['expiry_execution_boundary']
        self.assertTrue(expired.any());self.assertFalse(a.loc[expired,'Active'].any())
        # Trading costs and turnover limits can keep distinct holdings after expiry.

    def test_pre_activation_and_control_exposures(self):
        first=self.study['audit'].index[self.study['audit'].Active][0]
        p=self.study['returns'].loc[:first].iloc[:-1]
        np.testing.assert_allclose(p.iloc[:,0],p.iloc[:,1])
        a=self.study['control_audit']
        self.assertIn('Risk difference vs strategy',a)
        self.assertEqual(len(self.study['targets']),5)

    def test_future_changes_do_not_change_previous_targets(self):
        changed=self.prices.copy();changed.loc['2022-03-10':]*=1.1
        base=copy.deepcopy(self.base);base['returns']=changed.pct_change(fill_method=None).dropna()
        vals=self.valuations.copy();vals.loc['2022-03-10':,'NAV per share']*=1.1
        other=run_jpm_view_study(changed,base,self.forecast,valuations=vals)
        for name,t in self.study['targets'].items():
            pd.testing.assert_frame_equal(t.loc[:'2022-03-09'],other['targets'][name].loc[:'2022-03-09'])

    def test_forward_gate_rejects_reconstruction_as_forward(self):
        with self.assertRaisesRegex(ValueError,'subsequent'):
            run_jpm_view_study(self.prices,self.base,self.forecast,valuations=self.valuations,prospective_after='2026-10-09')


if __name__ == '__main__':
    unittest.main()
