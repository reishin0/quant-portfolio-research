"""Isolated causal bar-level macro proxy diagnostics; no broker or strategy imports."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import logsumexp

EQUITIES=['SPY','QQQ','DIA']


def classify_observation(observations, now, max_age=90, allow_proxy=False):
    """Only timestamped current-session observations are eligible; never infer yields."""
    now=pd.Timestamp(now)
    result={'state':'UNKNOWN','equity_guard':'UNKNOWN','early_equity_stress':False,'agreement_score':0.,
            'confidence_kind':'index agreement, not calibrated probability','yield_kind':'UNAVAILABLE',
            'research_permission':'UNKNOWN_NO_NEW_RISK','reason':'','max_input_age_seconds':None}
    if now.tzinfo is None:raise ValueError('Timezone-aware decision timestamp required.')
    ages=[]
    required=EQUITIES+(['IEF'] if allow_proxy else ['Y2','Y10'])
    for name in required:
        # Retain the independently available equity control when the bond input
        # is missing, while the combined state remains UNKNOWN.
        if name==required[3]:
            down=sum(observations[s]['session_move']<=-.003 for s in EQUITIES)
            up=sum(observations[s]['session_move']>=.003 for s in EQUITIES)
            guard='BEARISH' if down>=2 else 'BULLISH' if up>=2 else 'NEUTRAL'
            early=down>=2 or sum(observations[s]['move5']<=-.001 for s in EQUITIES)>=2
            result.update(equity_guard=guard,early_equity_stress=early,agreement_score=max(up,down)/3)
        if name not in observations:result['reason']='missing '+name;return result
        o=observations[name];t=pd.Timestamp(o['available_at'])
        if t.tzinfo is None:raise ValueError('Timezone-aware input availability required.')
        age=(now-t).total_seconds();ages.append(age)
        if age<0 or age>max_age or t.tz_convert('America/New_York').date()!=now.tz_convert('America/New_York').date():
            result['reason']='future/stale/wrong-session '+name;return result
        values=[o.get('change_bp',np.nan)] if name in ['Y2','Y10'] else [o.get('session_move',np.nan),o.get('move5',np.nan)]
        if not np.isfinite(values).all():
            result['reason']='invalid '+name;return result
    down=sum(observations[s]['session_move']<=-.003 for s in EQUITIES)
    up=sum(observations[s]['session_move']>=.003 for s in EQUITIES)
    guard='BEARISH' if down>=2 else 'BULLISH' if up>=2 else 'NEUTRAL'
    early=down>=2 or sum(observations[s]['move5']<=-.001 for s in EQUITIES)>=2
    result.update(equity_guard=guard,early_equity_stress=early,agreement_score=max(up,down)/3,
                  max_input_age_seconds=max(ages),research_permission='RESEARCH_ONLY_OBSERVE')
    if allow_proxy:
        o=observations['IEF'];direction=-1 if o['session_move']>=.001 else 1 if o['session_move']<=-.001 else 0
        result['yield_kind']='BOND_ETF_PRICE_PROXY'
    else:
        changes=[observations[k].get('change_bp') for k in ['Y2','Y10']]
        if not all(x is not None and np.isfinite(x) for x in changes):result['reason']='missing yield changes';return result
        direction=1 if min(changes)>=2 else -1 if max(changes)<=-2 else 0
        result['yield_kind']='MEASURED_TREASURY_YIELDS'
    if early and direction>0:state='RISING_YIELD_STRESS'
    elif early and direction<0:state='FALLING_YIELD_STRESS'
    elif guard=='BULLISH':state='BROAD_RISK_ON'
    else:state='MIXED'
    if allow_proxy:state+='_PROXY'
    result.update(state=state,reason='price co-movement; no causal attribution',
                  research_permission='RESEARCH_ONLY_RESTRICT_NEW_LONGS' if early and direction else 'RESEARCH_ONLY_OBSERVE')
    return result


def causal_hmm(train, test, seed=42):
    """Adapt existing return/volatility/volume features with frozen train scaling.

    GaussianHMM is already installed in the inspected AutoTrade environment.
    No full-panel predict_proba/Viterbi smoothing is used on evaluation data.
    """
    from hmmlearn.hmm import GaussianHMM
    train=train.dropna().tail(1500)
    if len(train)<80:raise ValueError('HMM needs at least 80 prior observations.')
    mean=train.mean();sd=train.std(ddof=0).replace(0,1)
    x=((train-mean)/sd).to_numpy();model=GaussianHMM(n_components=2,covariance_type='diag',n_iter=200,random_state=seed,min_covar=1e-5)
    model.fit(x)
    if not np.isfinite(model.means_).all() or not model.monitor_.converged:raise ValueError('HMM fit unavailable/nonconverged.')
    variance=np.diagonal(model.covars_,axis1=1,axis2=2)
    if (variance<=0).any() or not np.isfinite(variance).all():raise ValueError('Invalid HMM covariance.')
    log_trans=np.log(np.maximum(model.transmat_,1e-300));alpha=np.log(np.maximum(model.startprob_,1e-300))
    def step(value, prior, transition=True):
        emission=-.5*(np.log(2*np.pi*variance)+((value-model.means_)**2)/variance).sum(axis=1)
        post=(logsumexp(prior[:,None]+log_trans,axis=0) if transition else prior)+emission
        return post-logsumexp(post)
    # Train alpha initializes the prior entering the next session.
    for i,value in enumerate(x):alpha=step(value,alpha,transition=i>0)
    bear=int(np.argmin(model.means_[:,0]));out=[]
    for _,row in test.iterrows():
        if row.isna().any():
            # Advance the hidden chain by one elapsed minute without observing
            # an emission. Missing data must not freeze latent time.
            alpha=logsumexp(alpha[:,None]+log_trans,axis=0);alpha-=logsumexp(alpha)
            out.append(np.nan);continue
        alpha=step(((row-mean)/sd).to_numpy(),alpha);out.append(float(np.exp(alpha[bear])))
    return pd.Series(out,index=test.index),{'train_rows':len(train),'train_end':str(train.index[-1]),
        'mean':mean.to_dict(),'scale':sd.to_dict(),'means':model.means_.tolist(),'transmat':model.transmat_.tolist(),
        'covariances':variance.tolist(),'bull_state_rule':'larger fitted return mean','seed':seed,'iterations':model.monitor_.iter,
        'likelihood_history_tail':list(model.monitor_.history)[-2:],
        'session_boundary':'Final prior-session filtered state carried to next session; overnight duration is not modelled.'}


def build_panel(bars):
    data=bars.copy()
    data['time']=pd.to_datetime(data.close_available_ny).dt.tz_localize('America/New_York').dt.tz_convert('UTC')
    if data.duplicated(['symbol','time']).any():raise ValueError('Duplicate symbol/time bars.')
    if not np.isfinite(data[['open','close','volume']]).all().all() or (data[['open','close']]<=0).any().any():raise ValueError('Invalid bars.')
    features={};panels=[];previous_close={}
    for date,day in data.groupby('market_date'):
        grid=pd.date_range(pd.Timestamp(date+' 09:31',tz='America/New_York'),pd.Timestamp(date+' 16:00',tz='America/New_York'),freq='min').tz_convert('UTC')
        for symbol,g in day.groupby('symbol'):
            g=g.set_index('time').sort_index().reindex(grid)
            open_row=g.loc[grid[0],'open']
            if not np.isfinite(open_row):continue
            frame=pd.DataFrame({'close':g.close,'volume':g.volume,'session_move':g.close/open_row-1,
                'move5':g.close/g.close.shift(5)-1,'move30':g.close/g.close.shift(30)-1,
                'open_gap':open_row/previous_close.get(symbol,np.nan)-1},index=grid)
            previous_close[symbol]=g.close.iloc[-1]
            features[(date,symbol)]=frame
        for t in grid:
            obs={}
            for symbol in EQUITIES+['IEF']:
                frame=features.get((date,symbol))
                if frame is None:continue
                row=frame.loc[t]
                if pd.isna(row['close']) or pd.isna(row['move5']):continue
                obs[symbol]=dict(available_at=t,session_move=float(row.session_move),move5=float(row.move5))
            state=classify_observation(obs,t,allow_proxy=True)
            support={}
            for symbol in EQUITIES+['IEF','SHY']:
                frame=features.get((date,symbol))
                if frame is not None:
                    for field in ['close','session_move','move5','move30','open_gap']:
                        support[symbol+'_'+field]=frame.at[t,field]
            panels.append(dict(time=t,date=date,**state,**support))
    panel=pd.DataFrame(panels).set_index('time').sort_index()
    # Preserve missing observations. No cross-session returns or rolling windows.
    hmm_features=[]
    for (date,symbol),frame in features.items():
        if symbol!='SPY':continue
        r=np.log(frame.close).diff()
        f=pd.DataFrame({'return':r,'volatility':r.rolling(20,min_periods=20).std(ddof=0),
                        'volume_change':np.log(frame.volume.clip(lower=1)).diff()},index=frame.index)
        hmm_features.append(f)
        panel.loc[frame.index,'SPY close']=frame.close
        panel.loc[frame.index,'outcome_15m']=frame.close.shift(-15)/frame.close-1
        # Labels require the complete intervening observation window.
        window_ok=frame.close.notna().iloc[::-1].rolling(16,min_periods=16).sum().iloc[::-1].eq(16)
        panel.loc[frame.index[~window_ok],'outcome_15m']=np.nan
    return panel,pd.concat(hmm_features).sort_index(),features


def replay(bars,out):
    panel,hmm_features,features=build_panel(bars);hmm_records=[]
    evaluation=sorted(d for d in panel.date.unique() if d>='2026-10-12')
    if len(evaluation)<4:raise ValueError('Declared minimum four evaluation sessions unavailable.')
    out.mkdir(parents=True,exist_ok=False)
    bars.groupby(['market_date','symbol']).size().unstack().to_csv(out/'source_coverage.csv')
    # Record scope and source feasibility before fitting or computing economics.
    (out/'preflight.json').write_text(json.dumps({'evaluation_dates':evaluation,
        'expected_regular_session_bars':390,'actual_provider_receipt_times_available':False,
        'availability_assumption':'Each aggregate becomes available at its bar end; actual network latency is unknown.',
        'direct_intraday_yields_available':False,'native_trade_reproduction':False,
        'specification_sha256':hashlib.sha256(Path(__file__).with_name('specification.json').read_bytes()).hexdigest()},indent=2),encoding='utf8')
    for date in evaluation:
        test_index=panel.index[panel.date==date];train=hmm_features.loc[hmm_features.index<test_index[0]]
        probability,record=causal_hmm(train,hmm_features.loc[test_index]);panel.loc[test_index,'HMM bear probability']=probability;hmm_records.append(dict(date=date,**record))
    panel['guard_signal']=panel.equity_guard.eq('BEARISH')
    panel['equity_early_signal']=panel.early_equity_stress
    panel['macro_signal']=panel.state.str.contains('STRESS')
    panel['hmm_signal']=panel['HMM bear probability']>=.7
    panel['combined_signal']=panel.macro_signal & panel.hmm_signal
    rows=[];economics=[]
    for date in evaluation:
        day=panel[panel.date==date]
        valid=day.outcome_15m.notna() & day['HMM bear probability'].notna() & day.state.ne('UNKNOWN')
        label=day.outcome_15m<-.002
        for signal in ['guard_signal','equity_early_signal','macro_signal','hmm_signal','combined_signal']:
            pred=day[signal];tp=int((pred&label&valid).sum());fp=int((pred&~label&valid).sum());fn=int((~pred&label&valid).sum())
            active=day.index[pred&valid]
            stress_times=day.index[label&valid]
            # Relative timing of the first predictive label and alert only. It
            # is not latency against a measured macro event or native logs.
            delay=(active[0]-stress_times[0]).total_seconds()/60 if len(active) and len(stress_times) else None
            rows.append(dict(date=date,method=signal,eligible_minutes=int(valid.sum()),true_positive=tp,false_positive=fp,missed_stress=fn,
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                first_signal_ny=str(active[0].tz_convert('America/New_York')) if len(active) else None,
                first_label_ny=str(stress_times[0].tz_convert('America/New_York')) if len(stress_times) else None,
                first_alert_minus_first_label_minutes=delay,
                state_changes=int(pred.loc[valid].astype(int).diff().abs().sum()),unknown_minutes=int(day.state.eq('UNKNOWN').sum())))
        # Common eligible, non-overlapping hypothetical opportunities. No position
        # or actual trade receipt is inferred from this diagnostic.
        spy=features[(date,'SPY')]
        for minute in range(30,331,30):
            t=day.index[minute-1];entry=t+pd.Timedelta(minutes=1);exit_at=entry+pd.Timedelta(minutes=30)
            interval=spy.loc[entry:exit_at,'close']
            if not bool(valid.at[t]) or len(interval)!=31 or interval.isna().any():continue
            gross=float(spy.at[exit_at,'close']/spy.at[entry,'close']-1)
            for signal in ['always_long','guard_signal','equity_early_signal','macro_signal','hmm_signal','combined_signal']:
                take=signal=='always_long' or not bool(day.at[t,signal])
                economics.append(dict(date=date,decision=str(t),method=signal,take=take,gross=gross if take else 0.,
                    net_2bps_each_side=((1-.0002)*(1+gross)*(1-.0002)-1) if take else 0.,
                    net_5bps_each_side=((1-.0005)*(1+gross)*(1-.0005)-1) if take else 0.,
                    excluded_opportunity_return=0. if take else gross))
    panel.to_csv(out/'states.csv');pd.DataFrame(rows).to_csv(out/'classification_metrics.csv',index=False)
    econ=pd.DataFrame(economics);econ.to_csv(out/'economic_diagnostic.csv',index=False)
    summary=econ.groupby('method').agg(opportunities=('take','size'),accepted=('take','sum'),
        net_2bps=('net_2bps_each_side',lambda x:float((1+x).prod()-1)),net_5bps=('net_5bps_each_side',lambda x:float((1+x).prod()-1)))
    summary.to_csv(out/'economic_summary.csv');(out/'hmm_training_receipts.json').write_text(json.dumps(hmm_records,indent=2),encoding='utf8')
    coverage=bars.groupby(['market_date','symbol']).size().unstack();coverage.to_csv(out/'source_coverage.csv')
    state_summary=panel.groupby(['date','state']).size().unstack(fill_value=0);state_summary.to_csv(out/'state_counts.csv')
    return summary,pd.DataFrame(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--bars',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    source=Path(args.bars);spec=Path(__file__).with_name('specification.json');out=Path(args.output)
    # Only market data are read, never credentials, broker state or strategy entry points.
    summary,metrics=replay(pd.read_csv(source),out)
    from importlib.metadata import version
    receipt=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),bars_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),specification_sha256=hashlib.sha256(spec.read_bytes()).hexdigest(),
        packages={x:version(x) for x in ['numpy','pandas','scipy','hmmlearn']},evidence='Current research code on historical aggregate bars; no untouched confirmation or native economics.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print(summary.to_string());print(metrics.to_string(index=False))

if __name__=='__main__':main()
