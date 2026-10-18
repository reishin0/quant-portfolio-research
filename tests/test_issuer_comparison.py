"""Economic/data boundary tests for the new study; no frozen model changes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from research.credit_funding.issuer_comparison import (
    prepare_bonds, forward_outcomes, disclosure_events, crash_audit,
    validate_prices, load_study, run_study, summarize_arm, disclosure_price_context, WARNING,
)

ROOT = Path(__file__).resolve().parents[1]


class ComparisonTests(unittest.TestCase):
    def prices(self, values):
        return pd.DataFrame({'X':values,'SPY':100.}, index=pd.bdate_range('2026-01-02', periods=len(values)))

    def test_zero_price_invalidates_both_fields_without_mutating_raw(self):
        raw=pd.DataFrame(dict(cusip=['123456789']*2,tradeDate=['2026-01-02','2026-01-05'],lastSalePrice=[0,100],lastSaleYield=[8,5]))
        clean,n=prepare_bonds(raw)
        self.assertEqual(n,1)
        self.assertTrue(clean.iloc[0][['lastSalePrice','lastSaleYield']].isna().all())
        self.assertEqual(raw.iloc[0].lastSaleYield,8)

    def test_missing_yield_also_invalidates_price(self):
        f=pd.DataFrame(dict(cusip=['123456789'],tradeDate=['2026-01-02'],lastSalePrice=[100],lastSaleYield=[np.nan]))
        clean,n=prepare_bonds(f)
        self.assertEqual(n,1)
        self.assertTrue(pd.isna(clean.lastSalePrice.iloc[0]))

    def test_boolean_bond_rejected(self):
        f=pd.DataFrame(dict(cusip=['123456789'],tradeDate=['2026-01-02'],lastSalePrice=[True],lastSaleYield=[5]))
        with self.assertRaises(ValueError):prepare_bonds(f)

    def test_no_same_day_loss_prediction(self):
        p=self.prices([100,80,88,90])
        o=forward_outcomes(p,[p.index[1]],'X',(2,)).iloc[0]
        self.assertAlmostEqual(o.close_return_pct,12.5)
        self.assertFalse(o.loss_hit)

    def test_incomplete_horizon_is_censored_even_when_loss_already_seen(self):
        p=self.prices([100,80,85])
        o=forward_outcomes(p,[p.index[0]],'X',(5,)).iloc[0]
        self.assertFalse(o.complete)
        self.assertTrue(pd.isna(o.loss_hit))
        self.assertTrue(pd.isna(o.minimum_close_pct))

    def test_path_loss_can_coexist_with_positive_final_return(self):
        p=self.prices([100,80,130])
        o=forward_outcomes(p,[p.index[0]],'X',(2,)).iloc[0]
        self.assertTrue(o.loss_hit)
        self.assertAlmostEqual(o.minimum_close_pct,-20)
        self.assertAlmostEqual(o.close_return_pct,30)

    def test_prior_prices_do_not_affect_forward_outcome(self):
        p=self.prices([10,100,90,110]);q=p.copy();q.iloc[0,0]=1000
        pd.testing.assert_frame_equal(forward_outcomes(p,[p.index[1]],'X',(2,)),forward_outcomes(q,[q.index[1]],'X',(2,)))

    def test_missing_equity_rejected(self):
        p=self.prices([100,np.nan,99])
        with self.assertRaises(ValueError):validate_prices(p)

    def test_unordered_and_duplicate_dates_rejected(self):
        p=self.prices([100,101,99])
        with self.assertRaises(ValueError):validate_prices(p.iloc[::-1])
        p.index=[p.index[0]]*3
        with self.assertRaises(ValueError):validate_prices(p)

    def record(self):
        return dict(issuer='X',published_on='2026-01-02',period_start='2025-01-01',period_end='2025-12-31',
                    units='USD millions',operating_cash_flow=-10,cash_capex=20,reported_debt=100,
                    debt_basis='book value only',source_url='https://example.com/filing')

    def test_friday_disclosure_enters_next_observed_monday_close(self):
        p=self.prices([100,90,80]);r=disclosure_events([self.record()],p).iloc[0]
        self.assertEqual(r.event_close,p.index[1]);self.assertEqual(r.historical_gap_usdm,30)

    def test_future_disclosure_not_backdated(self):
        p=self.prices([100,90]);r=self.record();r['published_on']='2026-10-18'
        self.assertTrue(pd.isna(disclosure_events([r],p).event_close.iloc[0]))

    def test_duplicate_disclosures_rejected(self):
        with self.assertRaises(ValueError):disclosure_events([self.record(),self.record()],self.prices([100,90]))

    def test_debt_free_cash_surplus_not_flagged(self):
        r=self.record();r['operating_cash_flow']=30
        self.assertEqual(disclosure_events([r],self.prices([100,90])).state.iloc[0],'NO_FLAG')
        r['operating_cash_flow']=-10;r['reported_debt']=0
        self.assertEqual(disclosure_events([r],self.prices([100,90])).state.iloc[0],'NO_FLAG')

    def test_negative_debt_boolean_and_bad_period_rejected(self):
        for key,value in [('reported_debt',-1),('cash_capex',True),('period_end','2026-02-01')]:
            r=self.record();r[key]=value
            with self.assertRaises(ValueError):disclosure_events([r],self.prices([100,90]))

    def test_same_day_warning_not_counted_as_early(self):
        p=self.prices([100]*22+[80]);t=pd.DataFrame({'date':p.index,'state':['NO_QUORUM']*22+[WARNING]})
        self.assertEqual(crash_audit(p,'X',t).bond_prior_status.iloc[0],'NO_PRIOR_WARNING')

    def test_unknown_prior_coverage_is_not_failure(self):
        p=self.prices([100]*22+[80]);t=pd.DataFrame({'date':p.index,'state':['NO_QUORUM']*23});t.loc[10,'state']='UNKNOWN'
        self.assertEqual(crash_audit(p,'X',t).bond_prior_status.iloc[0],'UNKNOWN_PRIOR_COVERAGE')

    def test_actual_prior_warning_and_lead(self):
        p=self.prices([100]*22+[80]);t=pd.DataFrame({'date':p.index,'state':['NO_QUORUM']*23});t.loc[20,'state']=WARNING
        r=crash_audit(p,'X',t).iloc[0]
        self.assertEqual(r.bond_prior_status,'PRIOR_WARNING');self.assertEqual(r.latest_warning_lead_sessions,2)

    def test_no_bond_panel_stays_not_evaluable(self):
        r=crash_audit(self.prices([100,80]),'X').iloc[0]
        self.assertEqual(r.bond_prior_status,'NOT_EVALUABLE')

    def test_disclosure_context_does_not_count_anchor_crash_as_prior(self):
        p=self.prices([100,80,60]);d=pd.DataFrame([dict(issuer='X',event_close=p.index[2])])
        r=disclosure_price_context(p,d).iloc[0]
        self.assertEqual(r.earlier_daily_10pct_falls_in_20_sessions,1)
        self.assertTrue(pd.isna(r.change_to_anchor_over_previous_5_sessions_pct))

    def test_disclosure_context_ignores_future_prices(self):
        p=self.prices([100,80,100]);q=p.copy();q.iloc[2,0]=1
        d=pd.DataFrame([dict(issuer='X',event_close=p.index[1])])
        pd.testing.assert_frame_equal(disclosure_price_context(p,d),disclosure_price_context(q,d))

    def test_disclosure_context_future_date_unavailable(self):
        self.assertTrue(disclosure_price_context(self.prices([100,90]),pd.DataFrame([dict(issuer='X',event_close=pd.NaT)])).empty)

    def test_empty_events_have_no_fake_zero_success_rate(self):
        o=forward_outcomes(self.prices([100,90]),[],'X')
        r=summarize_arm(o,'X','test')[0]
        self.assertEqual(r['events'],0);self.assertTrue(np.isnan(r['loss_frequency_pct']))

    def test_manifest_pin_checked_before_calculation(self):
        with self.assertRaisesRegex(ValueError,'manifest changed'):load_study(ROOT,'0'*64)

    def test_real_snapshot_retains_all_candidates_and_no_pooled_quorum(self):
        r=run_study(ROOT)
        self.assertEqual(set(r['coverage'].issuer),{'APLD','IREN','NBIS','CORZ','ORCL','EQIX'})
        self.assertEqual(set(r['timelines']),{'ORCL','EQIX'})
        self.assertEqual(len(r['prices']),199)
        self.assertEqual(r['coverage'].bond_rows.sum(),1977)
        near=r['coverage'].loc[r['coverage'].issuer.isin(['APLD','IREN','NBIS','CORZ'])]
        self.assertTrue(near.warning_onsets.isna().all())
        self.assertTrue(r['events'].complete.all())


if __name__ == '__main__':
    unittest.main()
