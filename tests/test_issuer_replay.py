import copy
import unittest
import json
import hashlib
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
from research.credit_funding.issuer_replay import bond_diagnostics, issuer_timeline, equity_context, funding_timeline
from research.credit_funding.issuer_replay import load_case, verify_preserved
from research.credit_funding.fetch_bond_history import fetch


class IssuerReplayTests(unittest.TestCase):
    def setUp(self):
        self.spec=dict(issuer='EXAMPLE',min_warning_bonds=2,bonds=['A','B'],bond_window=['2026-01-01','2026-12-31'],history=20,persistence=3,
                       widening_bp=100.,max_gap_calendar_days=4)
        self.dates=pd.bdate_range('2026-01-05',periods=23)
        self.frame=pd.DataFrame(dict(cusip='A',tradeDate=self.dates,lastSalePrice=100.,lastSaleYield=[10.]*20+[11.]*3))

    def test_percent_to_bp_and_exact_threshold(self):
        result=bond_diagnostics(self.frame,self.spec)
        self.assertEqual(result.iloc[-1].state,'YIELD_WARNING_DIAGNOSTIC')
        self.assertEqual(result.iloc[-1].minimum_widening_bp,100.)
        self.assertTrue((result.iloc[:-1].state=='UNKNOWN').all())

    def test_three_observations_all_required(self):
        self.frame.loc[21,'lastSaleYield']=10.99
        self.assertEqual(bond_diagnostics(self.frame,self.spec).iloc[-1].state,'NO_FLAG')

    def test_future_observation_does_not_change_prefix(self):
        first=bond_diagnostics(self.frame,self.spec)
        later=pd.concat([self.frame,pd.DataFrame([dict(cusip='A',tradeDate=self.dates[-1]+pd.Timedelta(days=1),lastSalePrice=50.,lastSaleYield=99.)])])
        pd.testing.assert_frame_equal(first,bond_diagnostics(later,self.spec).iloc[:23].reset_index(drop=True))

    def test_duplicates_rejected_missing_values_unknown(self):
        with self.assertRaises(ValueError): bond_diagnostics(pd.concat([self.frame,self.frame.iloc[-1:]]),self.spec)
        self.frame.loc[1,'lastSaleYield']=np.nan
        self.assertEqual(bond_diagnostics(self.frame,self.spec).iloc[-1].state,'UNKNOWN')
        self.frame.loc[1,'lastSaleYield']=np.inf
        with self.assertRaises(ValueError): bond_diagnostics(self.frame,self.spec)

    def test_long_gap_is_unknown(self):
        self.frame.loc[22,'tradeDate']+=pd.Timedelta(days=10)
        self.assertEqual(bond_diagnostics(self.frame,self.spec).iloc[-1].state,'UNKNOWN')

    def test_two_bonds_no_forward_fill(self):
        other=self.frame.assign(cusip='B')
        d=bond_diagnostics(pd.concat([self.frame,other]),self.spec)
        dates=self.dates.append(pd.DatetimeIndex([self.dates[-1]+pd.Timedelta(days=1)]))
        t=issuer_timeline(d,dates,self.spec)
        self.assertEqual(t.iloc[-2].warning_bonds,2)
        self.assertTrue(t.iloc[-2].onset_or_resumption)
        self.assertEqual(t.iloc[-1].state,'UNKNOWN')

    def test_context_incomplete_horizon_is_missing(self):
        dates=pd.bdate_range('2026-02-01',periods=7)
        t=pd.DataFrame(dict(date=[dates[0]],onset_or_resumption=[True]))
        e=pd.DataFrame({'CRWV':[100.,101.,102.,103.,104.,110.,111.]},index=dates)
        r=equity_context(t,e).iloc[0]
        self.assertAlmostEqual(r.CRWV_5_sessions_pct,10.)
        self.assertTrue(np.isnan(r.CRWV_20_sessions_pct))

    def test_funding_conservative_publication_not_period_end(self):
        r=dict(issuer='CRWV',units='USD millions',period_start='2026-01-01',period_end='2026-03-31',
               filed_on='2026-05-08',period_label='Q1',source_url='https://www.sec.gov/example',
               cash_capex=7695,operating_cash_flow=2984,debt_principal=25149)
        result=funding_timeline([r],issuer='CRWV',units='USD millions',reporting_timezone='America/New_York').iloc[0]
        self.assertEqual(result.eligible_at,'2026-05-09T00:00:00-04:00')
        self.assertEqual(result.historical_gap,4711)
        self.assertEqual(result.state,'FUNDING_VULNERABILITY')
        bad=copy.deepcopy(r);bad['filed_on']='2026-02-01'
        with self.assertRaises(ValueError): funding_timeline([bad],issuer='CRWV',units='USD millions',reporting_timezone='America/New_York')

    def test_empty_bond_history_remains_unknown(self):
        d=bond_diagnostics(self.frame.iloc[:0],self.spec)
        t=issuer_timeline(d,self.dates,self.spec)
        self.assertTrue(t.state.eq('UNKNOWN').all())
        c=equity_context(t,pd.DataFrame({'EXAMPLE':100.},index=self.dates))
        self.assertEqual(list(c),['date','EXAMPLE_5_sessions_pct','EXAMPLE_20_sessions_pct'])
        self.assertTrue(c.empty)
        self.assertTrue(issuer_timeline(d,[],self.spec).empty)

    def test_duplicate_diagnostic_cannot_manufacture_quorum(self):
        d=bond_diagnostics(self.frame,self.spec)
        with self.assertRaisesRegex(ValueError,'Duplicate diagnostic'):
            issuer_timeline(pd.concat([d,d]),self.dates,self.spec)

    def test_mixed_issuers_and_invalid_states_rejected(self):
        d=bond_diagnostics(self.frame,self.spec)
        bad=d.copy();bad.loc[0,'issuer']='OTHER'
        with self.assertRaises(ValueError):issuer_timeline(bad,self.dates,self.spec)
        for state in ['TYPO',None]:
            bad=d.copy();bad.loc[0,'state']=state
            with self.assertRaises(ValueError):issuer_timeline(bad,self.dates,self.spec)
        with self.assertRaises(ValueError):bond_diagnostics(self.frame.assign(issuer='OTHER'),self.spec)

    def test_bad_rules_rejected_before_calculation(self):
        for key,value in [('history',0),('persistence',True),('widening_bp',float('nan')),
                          ('max_gap_calendar_days',-1),('min_warning_bonds',3),('bonds',['A','A'])]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                bond_diagnostics(self.frame,dict(self.spec,**{key:value}))

    def test_boolean_numeric_and_intraday_dates_rejected(self):
        for field in ['lastSalePrice','lastSaleYield']:
            bad=self.frame.copy();bad[field]=bad[field].astype(object);bad.loc[0,field]=True
            with self.assertRaises(ValueError):bond_diagnostics(bad,self.spec)
        bad=self.frame.copy();bad.loc[0,'tradeDate']=pd.Timestamp('2026-01-05 12:00')
        with self.assertRaises(ValueError):bond_diagnostics(bad,self.spec)

    def test_context_rejects_duplicate_dates_and_invalid_horizons(self):
        t=pd.DataFrame({'date':[self.dates[0]],'onset_or_resumption':[True]})
        e=pd.DataFrame({'EXAMPLE':100.},index=self.dates)
        with self.assertRaises(ValueError):equity_context(t,pd.concat([e,e]))
        for h in [(0,),(-1,),(True,),(5,5)]:
            with self.assertRaises(ValueError):equity_context(t,e,h)
        t['onset_or_resumption']='yes'
        with self.assertRaises(ValueError):equity_context(t,e)

    def test_funding_different_periods_and_revisions_preserved(self):
        r=dict(issuer='EXAMPLE',units='EUR millions',period_start='2025-01-01',period_end='2025-12-31',
               filed_on='2026-02-01',period_label='FY',source_url='https://example.org/filing',
               cash_capex=20,operating_cash_flow=10,debt_principal=30)
        records=[r,dict(r,period_start='2025-10-01',period_label='Q4'),dict(r,filed_on='2026-03-01',cash_capex=21)]
        out=funding_timeline(records,issuer='EXAMPLE',units='EUR millions',reporting_timezone='Europe/London')
        self.assertEqual(len(out),3)
        self.assertEqual(out.iloc[0].eligible_at,'2026-02-02T00:00:00+00:00')
        self.assertEqual(out.iloc[-1].historical_gap,11)
        for records in [[r,r],[dict(r,issuer='OTHER')],[dict(r,units='USD millions')],[dict(r,filed_on='2026-02-01T12:00:00')]]:
            with self.assertRaises(ValueError):funding_timeline(records,issuer='EXAMPLE',units='EUR millions',reporting_timezone='Europe/London')

    def test_second_issuer_case_end_to_end_and_tamper_detection(self):
        # Fictional contract fixture, not evidence of performance on another real issuer.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data';data.mkdir()
            frame=pd.concat([self.frame,self.frame.assign(cusip='B')])
            frame.to_csv(data/'bond_daily.csv',index=False)
            pd.DataFrame({'EXAMPLE':100.,'BENCH':50.},index=self.dates).to_csv(data/'equity_adjusted.csv')
            (data/'instruments.json').write_text(json.dumps([dict(cusip=x,issuerName='Example issuer') for x in ['A','B']]))
            (data/'funding_disclosures.json').write_text(json.dumps({'records':[dict(issuer='EXAMPLE',units='EUR millions',
                period_start='2025-01-01',period_end='2025-12-31',filed_on='2026-01-04',period_label='FY',
                source_url='https://example.org/filing',cash_capex=20,operating_cash_flow=10,debt_principal=30)]}))
            manifest={'created_at':'2026-10-18T00:00:00Z','file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir()}}
            (data/'manifest.json').write_text(json.dumps(manifest))
            case=dict(case_id='fictional',issuer='EXAMPLE',issuer_name='Example issuer',bond_issuer_name='Example issuer',
                      units='EUR millions',bond_currency='EUR',reporting_timezone='Europe/London',evidence_dir='data',
                      evidence_manifest_sha256=hashlib.sha256((data/'manifest.json').read_bytes()).hexdigest(),
                      rules={k:v for k,v in self.spec.items() if k not in ['issuer','bonds','bond_window']},
                      bonds=['A','B'],bond_window=self.spec['bond_window'],equity_symbols=['EXAMPLE','BENCH'],horizons=[5,20])
            (root/'case.json').write_text(json.dumps(case))
            c,s,m,i,b,e,f=load_case(root,'case.json')
            d=bond_diagnostics(b,s);t=issuer_timeline(d,e.index,s)
            self.assertEqual(t.iloc[-1].warning_bonds,2)
            self.assertEqual(funding_timeline(f['records'],issuer=c['issuer'],units=c['units'],reporting_timezone=c['reporting_timezone']).iloc[0].historical_gap,10)
            self.assertTrue(pd.isna(equity_context(t,e).iloc[0].EXAMPLE_5_sessions_pct))
            bad=dict(case,bond_issuer_name='Other issuer');(root/'bad.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'ownership'):load_case(root,'bad.json')
            (data/'bond_daily.csv').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'Evidence changed'):load_case(root,'case.json')

    def test_retained_case_matches_previous_results(self):
        root=Path(__file__).resolve().parents[1]
        case,spec,_,_,b,e,f=load_case(root,'research/credit_funding/cases/coreweave_20261017.json')
        t=issuer_timeline(bond_diagnostics(b,spec),e.index,spec)
        saved=json.loads((root/'research/credit_funding/coreweave_validation_20261018.json').read_text())
        self.assertEqual(t.loc[t.onset_or_resumption,'date'].dt.strftime('%Y-%m-%d').tolist(),saved['diagnostic_onsets'])
        result=equity_context(t,e)
        for actual,expected in zip(result.to_dict('records'),saved['equity_context']):
            for key,value in expected.items():
                if key=='date':continue
                if value is None:self.assertTrue(pd.isna(actual[key]))
                else:self.assertAlmostEqual(actual[key],value,places=8)

    def test_fetch_never_overwrites_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp,patch('requests.Session') as session:
            with self.assertRaises(FileExistsError):fetch(tmp,['21873SAB4'],'2026-01-01','2026-10-16')
            session.assert_not_called()

    def test_checkout_line_endings_only_for_declared_supporting_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'guide.md').write_bytes(b'Guide\n')
            original=hashlib.sha256(b'Guide\r\n').hexdigest()
            manifest={'preserved_project_sha256':{'guide.md':original}}
            case={'preserved_text_lf_sha256':{'guide.md':hashlib.sha256(b'Guide\n').hexdigest()}}
            verify_preserved(root,manifest,case)
            (root/'guide.md').write_bytes(b'Changed guide\n')
            with self.assertRaises(ValueError):verify_preserved(root,manifest,case)
            with self.assertRaisesRegex(ValueError,'forbidden'):
                verify_preserved(root,{'preserved_project_sha256':{'model.py':'x'}},{'preserved_text_lf_sha256':{'model.py':'x'}})

    def test_fetch_truncation_does_not_write_completed_panel(self):
        with tempfile.TemporaryDirectory() as tmp,patch('requests.Session') as session:
            mock=session.return_value.__enter__.return_value
            mock.cookies.get.return_value='test-token';mock.get.return_value.status_code=400
            body={'status':'success','returnBody':{'data':'[]','headers':{'Record-Total':['2']}}}
            response=MagicMock(status_code=200,content=json.dumps(body).encode());response.json.return_value=body
            mock.post.return_value=response
            target=Path(tmp)/'new'
            with self.assertRaisesRegex(RuntimeError,'truncated'):fetch(target,['21873SAB4'],'2026-01-01','2026-10-16')
            self.assertTrue((target/'finra_response.json').exists())
            self.assertFalse((target/'bond_daily.csv').exists())


if __name__=='__main__': unittest.main()
