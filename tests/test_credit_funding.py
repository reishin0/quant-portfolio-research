import copy
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from research.credit_funding.model import (FundingScenario, CASH_COLUMNS, funding_path,
    funding_assessment, credit_assessment, combine_assessments)

ROOT = Path(__file__).resolve().parents[1]


def cash_forecast():
    frame = pd.DataFrame(0., index=pd.date_range('2026-01-31',periods=3,freq='ME'), columns=CASH_COLUMNS)
    frame['operating_cash_flow'] = 10.
    frame['mandatory_capex'] = 30.
    return frame


def credit_rows():
    rows=[]
    for i,date in enumerate(pd.bdate_range('2026-08-03',periods=23)):
        observed=date.tz_localize('America/New_York')+pd.Timedelta(hours=16)
        rows.append(dict(observed_at=observed.isoformat(),eligible_at=(observed+pd.Timedelta(hours=1)).isoformat(),
            spread_bp=400. if i<20 else 510.,peer_spread_bp=300.,qualified=True,
            spread_kind='OAS_BP',comparison_id='fixed_issuer_curve_and_peer_basket'))
    return rows


class CreditAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.rows=credit_rows()
        self.now=pd.Timestamp(self.rows[-1]['eligible_at'])+pd.Timedelta(minutes=1)

    def test_persistent_issuer_widening_requires_no_equity_decline(self):
        self.assertEqual(credit_assessment(self.rows,self.now)['state'],'ACTIVE_ISSUER_STRESS')

    def test_combination_rejects_different_decision_time(self):
        future=credit_assessment(self.rows,self.now+pd.Timedelta(hours=1))
        funding={'funding_state':'NO_RULE_FLAG','asof_utc':self.now.isoformat()}
        result=combine_assessments(funding,future,{'state':'UNKNOWN'})
        self.assertEqual(result['issuer_credit_state'],'UNKNOWN')
        self.assertNotEqual(result['research_action'],'REVIEW_ISSUER_EXPOSURE')

    def test_unstamped_sector_states_are_not_current_evidence(self):
        funding={'funding_state':'NO_RULE_FLAG','asof_utc':self.now.isoformat()}
        result=combine_assessments(funding,{'state':'UNKNOWN'},{'state':'UNKNOWN'},
            sector_states={str(i):'ACTIVE_ISSUER_STRESS' for i in range(3)})
        self.assertEqual(result['sector_state'],'UNKNOWN')

    def test_sector_stress_requires_all_current_component_assessments(self):
        funding={'funding_state':'NO_RULE_FLAG','asof_utc':self.now.isoformat()}
        current=credit_assessment(self.rows,self.now)
        sector={str(i):copy.deepcopy(current) for i in range(3)}
        self.assertEqual(combine_assessments(funding,current,{'state':'UNKNOWN'},sector_states=sector)['sector_state'],'SECTOR_STRESS')
        sector['0']=credit_assessment(self.rows,self.now-pd.Timedelta(minutes=1))
        self.assertEqual(combine_assessments(funding,current,{'state':'UNKNOWN'},sector_states=sector)['sector_state'],'UNKNOWN')

    def test_invalid_window_and_breadth_thresholds_rejected(self):
        for history in [2.5,True,0]:
            with self.assertRaises(ValueError):credit_assessment(self.rows,self.now,history=history)
        funding={'funding_state':'NO_RULE_FLAG','asof_utc':self.now.isoformat()}
        with self.assertRaises(ValueError):combine_assessments(funding,{}, {},sector_min=0)

    def test_one_outlier_does_not_meet_persistence(self):
        rows=copy.deepcopy(self.rows);rows[-2]['spread_bp']=400.
        self.assertEqual(credit_assessment(rows,self.now)['state'],'NO_RULE_FLAG')

    def test_peer_widening_does_not_become_issuer_specific_signal(self):
        rows=copy.deepcopy(self.rows)
        for r in rows[-3:]:r['peer_spread_bp']=410.
        self.assertEqual(credit_assessment(rows,self.now)['state'],'NO_RULE_FLAG')

    def test_future_rows_do_not_change_earlier_result(self):
        now=pd.Timestamp(self.rows[-2]['eligible_at'])
        future=copy.deepcopy(self.rows);future[-1]['spread_bp']=99999.
        self.assertEqual(credit_assessment(self.rows,now),credit_assessment(future,now))
        self.assertEqual(credit_assessment(self.rows,now)['state'],'UNKNOWN')

    def test_duplicate_day_and_naive_timestamps_rejected(self):
        with self.assertRaises(ValueError):credit_assessment(self.rows+[self.rows[-1]],self.now)
        with self.assertRaises(ValueError):credit_assessment(self.rows,'2026-09-10')

    def test_stale_discontinuous_and_incompatible_inputs_unknown(self):
        self.assertEqual(credit_assessment(self.rows,self.now+pd.Timedelta(days=5))['state'],'UNKNOWN')
        rows=copy.deepcopy(self.rows);rows[-1]['spread_kind']='YIELD_PCT'
        self.assertEqual(credit_assessment(rows,self.now)['state'],'UNKNOWN')
        rows=copy.deepcopy(self.rows);rows[-1]['comparison_id']='different_seniority'
        self.assertEqual(credit_assessment(rows,self.now)['state'],'UNKNOWN')
        rows=copy.deepcopy(self.rows)
        for r in rows[-3:]:
            for key in ['observed_at','eligible_at']:r[key]=(pd.Timestamp(r[key])+pd.Timedelta(days=10)).isoformat()
        self.assertEqual(credit_assessment(rows,self.now+pd.Timedelta(days=10))['state'],'UNKNOWN')

    def test_issuer_stress_alone_cannot_trigger_spy(self):
        funding={'funding_state':'FUNDING_VULNERABILITY','asof_utc':self.now.isoformat()}
        result=combine_assessments(funding,credit_assessment(self.rows,self.now),credit_assessment([],self.now,kind='broad'))
        self.assertEqual(result['broad_market_state'],'UNKNOWN')
        self.assertEqual(result['research_action'],'REVIEW_ISSUER_EXPOSURE')
        self.assertEqual(result['trading_permission'],'NOT_CONNECTED')

    def test_future_or_stale_breadth_cannot_trigger_broad_stress(self):
        funding={'funding_state':'NO_RULE_FLAG','asof_utc':self.now.isoformat()}
        breadth=dict(observed_at=(self.now-pd.Timedelta(minutes=10)).isoformat(),eligible_at=self.now.isoformat(),qualified=True,weak_fraction=.8)
        broad=credit_assessment(self.rows,self.now,kind='broad')
        result=combine_assessments(funding,{'state':'NO_RULE_FLAG'},broad,equity_breadth=breadth)
        self.assertEqual(result['broad_market_state'],'BROAD_MARKET_STRESS')
        breadth['eligible_at']=(self.now+pd.Timedelta(minutes=1)).isoformat()
        self.assertEqual(combine_assessments(funding,{'state':'NO_RULE_FLAG'},broad,equity_breadth=breadth)['broad_market_state'],'UNKNOWN')


class FundingDisclosureTests(unittest.TestCase):
    def setUp(self):
        self.document=json.loads((ROOT/'data/credit_funding_20261017/source_observations.json').read_text(encoding='utf-8'))

    def test_june_financials_cannot_enter_june_backtest(self):
        result=funding_assessment(self.document,'2026-06-30T20:00:00Z')
        self.assertEqual(result['funding_state'],'UNKNOWN')
        self.assertIsNone(result['historical_investment_gap_usdm'])

    def test_late_older_filing_cannot_replace_newer_period(self):
        old=copy.deepcopy(self.document['fundamentals'][0])
        old.update(period_end='2026-03-31',published_on='2026-10-01',eligible_at='2026-10-02T00:00:00-04:00',cash_capex_h1=0.)
        self.document['fundamentals'].append(old)
        result=funding_assessment(self.document,'2026-10-16T23:30:00Z')
        self.assertEqual(result['historical_investment_gap_usdm'],10454.)

    def test_same_period_revision_takes_effect_only_when_available(self):
        revision=copy.deepcopy(self.document['fundamentals'][0])
        revision.update(published_on='2026-10-18',eligible_at='2026-10-19T00:00:00-04:00',cash_capex_h1=15000.)
        self.document['fundamentals'].append(revision)
        self.assertEqual(funding_assessment(self.document,'2026-10-16T23:30:00Z')['historical_investment_gap_usdm'],10454.)
        self.assertEqual(funding_assessment(self.document,'2026-10-20T00:00:00Z')['historical_investment_gap_usdm'],11337.)

    def test_disclosure_diagnostics_and_favourable_event_both_retained(self):
        result=funding_assessment(self.document,'2026-10-16T23:30:00Z')
        self.assertEqual(result['historical_investment_gap_usdm'],10454.)
        self.assertEqual(result['financing_access'],'RECENT_COMPLETED_FINANCING')
        self.assertEqual(result['funding_state'],'FUNDING_VULNERABILITY')
        self.assertIsNone(result['current_usable_cash']);self.assertIsNone(result['forward_funding_gap'])

    def test_future_financing_cannot_enter_prior_assessment(self):
        result=funding_assessment(self.document,'2026-09-21T20:00:00Z')
        self.assertNotIn('convertible_2033',result['event_ids'])

    def test_stale_financials_not_carried_forever(self):
        result=funding_assessment(self.document,'2027-10-17T00:00:00Z')
        self.assertEqual(result['funding_state'],'UNKNOWN')

    def test_company_disclosures_cannot_be_mixed(self):
        self.document['financing_events'][0]['issuer']='OTHER'
        with self.assertRaises(ValueError):funding_assessment(self.document,'2026-10-16T23:30:00Z')

    def test_current_vintage_broad_data_not_backdated(self):
        rows=credit_rows()
        retrieved=pd.Timestamp(rows[-1]['eligible_at'])
        for row in rows:row['eligible_at']=retrieved.isoformat()
        result=credit_assessment(rows,retrieved-pd.Timedelta(minutes=1),kind='broad')
        self.assertEqual(result['observations'],0)
        self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(credit_assessment(rows,retrieved,kind='broad')['state'],'BROAD_CREDIT_STRESS')


class CashAccountingTests(unittest.TestCase):
    def test_facility_order_does_not_create_avoidable_shortfall(self):
        facilities=[dict(id='long',cash_pool='test',capacity=20.,qualified_drawable=True,drawable_from='2026-01-01',expires_on='2026-12-31'),
                    dict(id='short',cash_pool='test',capacity=20.,qualified_drawable=True,drawable_from='2026-01-01',expires_on='2026-01-31')]
        one=funding_path(cash_forecast(),0.,facilities,cash_pool='test')
        two=funding_path(cash_forecast(),0.,facilities[::-1],cash_pool='test')
        pd.testing.assert_frame_equal(one,two)
        np.testing.assert_allclose(one.closing_cash,[0.,0.,-20.])

    def test_expired_capacity_not_reported_as_drawable(self):
        facility=dict(id='line',cash_pool='test',capacity=100.,qualified_drawable=True,drawable_from='2026-01-01',expires_on='2026-01-31')
        result=funding_path(cash_forecast(),100.,[facility],cash_pool='test')
        self.assertEqual(result.loc['2026-02-28','drawable_capacity'],0.)

    def test_missing_facility_dates_rejected(self):
        facility=dict(id='line',cash_pool='test',capacity=25.,qualified_drawable=True,drawable_from=None,expires_on='2026-12-31')
        with self.assertRaises(ValueError):funding_path(cash_forecast(),0.,[facility],cash_pool='test')

    def test_non_numeric_and_boolean_cash_cells_rejected(self):
        for value in [True,'10']:
            frame=cash_forecast().astype(object);frame.iloc[0,0]=value
            with self.assertRaises(ValueError):funding_path(frame,0.,[],cash_pool='test')

    def test_capex_and_ocf_are_counted_once(self):
        result=funding_path(cash_forecast(),50.,[],cash_pool='test')
        np.testing.assert_allclose(result.closing_cash,[30.,10.,-10.])
        self.assertEqual(result.attrs['peak_funding_gap'],10.)

    def test_facility_capacity_consumed_once(self):
        facility=dict(id='line',cash_pool='test',capacity=25.,qualified_drawable=True,drawable_from='2026-01-01',expires_on='2026-12-31')
        result=funding_path(cash_forecast(),0.,[facility],cash_pool='test')
        np.testing.assert_allclose(result.committed_draw,[20.,5.,0.])
        self.assertEqual(result.iloc[-1].closing_cash,-35.)

    def test_unverified_or_other_pool_facility_rejected(self):
        facility=dict(id='line',cash_pool='subsidiary',capacity=25.,qualified_drawable=True,drawable_from='2026-01-01',expires_on='2026-12-31')
        with self.assertRaises(ValueError):funding_path(cash_forecast(),0.,[facility],cash_pool='parent')
        facility['cash_pool']='parent';facility['qualified_drawable']=False
        with self.assertRaises(ValueError):funding_path(cash_forecast(),0.,[facility],cash_pool='parent')

    def test_fixed_existing_debt_is_not_repriced(self):
        baseline=funding_path(cash_forecast(),50.,[],cash_pool='test')
        shocked=funding_path(cash_forecast(),50.,[],FundingScenario(floating_rate_shock_bp=500,refinancing_rate_shock_bp=500),cash_pool='test')
        pd.testing.assert_frame_equal(baseline,shocked)
        frame=cash_forecast();frame['unhedged_floating_balance']=100.
        result=funding_path(frame,50.,[],FundingScenario(floating_rate_shock_bp=500),cash_pool='test')
        self.assertAlmostEqual(result.iloc[0].incremental_interest,100*.05*31/365)

    def test_hedge_expiry_and_refinancing_exposure_are_month_specific(self):
        frame=cash_forecast();frame['unhedged_floating_balance']=[0.,100.,100.]
        frame['refinanced_fixed_balance']=[0.,0.,50.]
        result=funding_path(frame,50.,[],FundingScenario(floating_rate_shock_bp=100,refinancing_rate_shock_bp=200),cash_pool='test')
        np.testing.assert_allclose(result.incremental_interest,[0.,100*.01*28/365,(100*.01+50*.02)*31/365])

    def test_monthly_gap_not_hidden_by_year_end_recovery(self):
        frame=cash_forecast();frame['operating_cash_flow']=[0.,0.,200.]
        result=funding_path(frame,0.,[],cash_pool='test')
        self.assertGreater(result.iloc[-1].closing_cash,0)
        self.assertEqual(result.attrs['peak_funding_gap'],60.)

    def test_capacity_haircut_and_expiry(self):
        facility=dict(id='line',cash_pool='test',capacity=100.,qualified_drawable=True,drawable_from='2026-01-01',expires_on='2026-01-31')
        result=funding_path(cash_forecast(),0.,[facility],FundingScenario(collateral_capacity_fraction=.1),cash_pool='test')
        np.testing.assert_allclose(result.committed_draw,[10.,0.,0.])

    def test_invalid_schema_or_double_interest_convention_rejected(self):
        with self.assertRaises(ValueError):funding_path(cash_forecast().iloc[[0,2]],50.,[],cash_pool='test')
        with self.assertRaises(ValueError):funding_path(cash_forecast(),50.,[],cash_pool='test',ocf_includes_interest_and_operating_leases=False)
        frame=cash_forecast();frame.iloc[0,1]=np.nan
        with self.assertRaises(ValueError):funding_path(frame,50.,[],cash_pool='test')


if __name__=='__main__':unittest.main()
