import importlib.util
import unittest
import numpy as np
import pandas as pd
from research.macro_regime.prototype import classify_observation,causal_hmm,build_panel


class MacroRegimeTests(unittest.TestCase):
    def setUp(self):
        self.now=pd.Timestamp('2026-10-14 10:00',tz='America/New_York')
        self.obs={s:dict(available_at=self.now,session_move=-.004,move5=-.002) for s in ['SPY','QQQ','DIA']}
        self.obs['IEF']=dict(available_at=self.now,session_move=.002,move5=.001)

    def test_proxy_is_explicit_and_agreement_is_not_probability(self):
        r=classify_observation(self.obs,self.now,allow_proxy=True)
        self.assertEqual(r['state'],'FALLING_YIELD_STRESS_PROXY')
        self.assertIn('not calibrated',r['confidence_kind'])
        self.obs['IEF']['session_move']=-.002
        self.assertEqual(classify_observation(self.obs,self.now,allow_proxy=True)['state'],'RISING_YIELD_STRESS_PROXY')

    def test_direct_yield_changes_and_curve_disagreement(self):
        for k in ['Y2','Y10']:self.obs[k]=dict(available_at=self.now,change_bp=3.)
        self.assertEqual(classify_observation(self.obs,self.now)['state'],'RISING_YIELD_STRESS')
        self.obs['Y10']['change_bp']=-3.
        self.assertEqual(classify_observation(self.obs,self.now)['state'],'MIXED')
        self.obs['Y2']['change_bp']=-3.
        self.assertEqual(classify_observation(self.obs,self.now)['state'],'FALLING_YIELD_STRESS')

    def test_unknown_on_missing_stale_and_future_inputs(self):
        for delta in [-91,1,-86400]:
            self.obs['IEF']['available_at']=self.now+pd.Timedelta(seconds=delta)
            r=classify_observation(self.obs,self.now,allow_proxy=True)
            self.assertEqual(r['state'],'UNKNOWN')
            self.assertEqual(r['research_permission'],'UNKNOWN_NO_NEW_RISK')
            self.assertEqual(r['equity_guard'],'BEARISH')
        del self.obs['IEF']
        self.assertEqual(classify_observation(self.obs,self.now,allow_proxy=True)['state'],'UNKNOWN')

    def test_missing_price_feature_rejected(self):
        del self.obs['SPY']['session_move']
        self.assertEqual(classify_observation(self.obs,self.now,allow_proxy=True)['state'],'UNKNOWN')

    def test_timezone_required(self):
        with self.assertRaises(ValueError):classify_observation(self.obs,self.now.tz_localize(None),allow_proxy=True)

    def test_future_bar_changes_do_not_change_previous_states(self):
        times=pd.date_range('2026-10-14 09:31',periods=60,freq='min')
        bars=pd.DataFrame([dict(symbol=s,market_date='2026-10-14',close_available_ny=str(t),
            open=100.,close=100.-i*.01,volume=1000+i) for s in ['SPY','QQQ','DIA','IEF','SHY'] for i,t in enumerate(times)])
        panel,_,_=build_panel(bars)
        changed=bars.copy();changed.loc[pd.to_datetime(changed.close_available_ny)>times[30],'close']*=1.5
        other,_,_=build_panel(changed)
        cols=['state','equity_guard','SPY_move5','IEF_session_move']
        pd.testing.assert_frame_equal(panel.iloc[:31][cols],other.iloc[:31][cols])
        self.assertTrue(panel.iloc[:5].state.eq('UNKNOWN').all())

    @unittest.skipUnless(importlib.util.find_spec('hmmlearn'),'Optional HMM tested separately in existing research runtime')
    def test_hmm_filter_is_causal_and_scaler_train_only(self):
        rng=np.random.default_rng(8)
        train=pd.DataFrame(rng.normal(size=(400,3)),columns=['return','volatility','volume_change'])
        future=pd.DataFrame(rng.normal(size=(30,3)),columns=train.columns,index=range(400,430))
        original,receipt=causal_hmm(train,future)
        changed=future.copy();changed.iloc[15:]*=100
        alternative,other=causal_hmm(train,changed)
        np.testing.assert_allclose(original.iloc[:15],alternative.iloc[:15],atol=1e-12)
        self.assertEqual(receipt['mean'],other['mean'])
        np.testing.assert_allclose(list(receipt['mean'].values()),train.mean())


if __name__=='__main__':unittest.main()
