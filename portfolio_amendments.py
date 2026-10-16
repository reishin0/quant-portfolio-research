"""Separate October 16 research extensions. No changes to the frozen model.

All decisions are paper research. Functions are also embedded in the amended
notebook; no broker, scheduler, network, or production imports occur here.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog
import pandas_market_calendars as mcal
from portfolio_tools import ASSETS, black_litterman, portfolio_step
from research_extensions import estimate_covariance
from research_diagnostics import evaluate_targets
from jpm_views import mapped_price_target, stable_allocation


def feasible_cash_scale(direction, current, cap=.275, turnover_limit=.10, initial=False):
    """Exact linear-program interval on a fixed risky allocation plus cash.

    Turnover includes cash; long-only and unlevered. Empty intervals are exposed.
    This chooses exposure, never a new return forecast or asset direction.
    """
    d=np.asarray(direction,dtype=float);old=np.asarray(current,dtype=float);n=len(d)
    if (old.shape!=(n+1,) or not np.isfinite(np.r_[d,old,cap,turnover_limit]).all()
            or (d<0).any() or (old < -1e-10).any() or abs(d.sum()-1)>1e-8
            or abs(old.sum()-1)>1e-8 or not 0<cap<=1 or not 0<turnover_limit<=1):
        raise ValueError('Invalid cash-scale direction, holdings or constraints.')
    if initial and not np.allclose(old,np.r_[np.zeros(n),1.]):
        raise ValueError('Initial deployment exception requires all cash.')
    # w(s) = [s*d, 1-s]. Epigraph t >= abs(w(s)-old).
    slope=np.r_[d,-1.];intercept=np.r_[np.zeros(n),1.]-old
    a=np.vstack([np.c_[slope,-np.eye(n+1)],np.c_[-slope,-np.eye(n+1)],np.r_[0.,np.ones(n+1)]])
    b=np.r_[-intercept,intercept,2*(1. if initial else turnover_limit)]
    bound=min(1.,cap/d.max());bounds=[(0.,bound)]+[(0,None)]*(n+1)
    low=linprog(np.r_[1.,np.zeros(n+1)],A_ub=a,b_ub=b,bounds=bounds,method='highs')
    high=linprog(np.r_[-1.,np.zeros(n+1)],A_ub=a,b_ub=b,bounds=bounds,method='highs')
    if low.status==2 or high.status==2:return None
    if not low.success or not high.success:raise RuntimeError('Cash-scale LP failed numerically.')
    return max(0.,float(low.x[0])),min(bound,float(high.x[0]))


def common_risk_pair(directions, currents, covariance, cap=.275, turnover_limit=.10, initial=False):
    """Intersect attainable volatility intervals, using the SAME prior covariance.

    Choose the highest shared risk no greater than either fully invested sleeve.
    If infeasible, both controls hold; the mismatch remains visible in the audit.
    Equality holds at rebalance under this covariance, not continuously or ex post.
    """
    names=list(covariance.columns);sigma=covariance.to_numpy(float)
    if (list(covariance.index)!=names or not np.isfinite(sigma).all()
            or not np.allclose(sigma,sigma.T) or np.linalg.eigvalsh(sigma).min()<=0
            or set(directions)!=set(currents) or len(directions)!=2):
        raise ValueError('Two controls and a positive definite labelled covariance required.')
    intervals={};vols={}
    for label,direction in directions.items():
        if list(direction.index)!=names or list(currents[label].index)!=names+['Cash']:
            raise ValueError('Asset order mismatch.')
        vols[label]=float(np.sqrt(direction@sigma@direction))
        intervals[label]=feasible_cash_scale(direction,currents[label],cap,turnover_limit,initial)
    feasible=all(x is not None for x in intervals.values())
    lower=max(intervals[k][0]*vols[k] for k in intervals) if feasible else None
    upper=min(intervals[k][1]*vols[k] for k in intervals) if feasible else None
    feasible=bool(feasible and lower<=upper+1e-10)
    targets={};rows=[]
    for label,d in directions.items():
        scale=float(upper/vols[label]) if feasible else None
        target=pd.Series(np.r_[scale*d,1-scale],index=names+['Cash']) if feasible else currents[label].copy()
        risk=float(np.sqrt(target[names]@sigma@target[names]));turnover=float(abs(target-currents[label]).sum()/2)
        if feasible and (turnover>(1 if initial else turnover_limit)+1e-7 or target[names].max()>cap+1e-7
                         or target.min() < -1e-8 or abs(target.sum()-1)>1e-8 or abs(risk-upper)>1e-8):
            raise RuntimeError('Common-risk execution failed independent constraint check.')
        targets[label]=target
        rows.append({'Strategy':label,'Status':'MATCHED' if feasible else 'INFEASIBLE_HOLD_BOTH',
            'Common volatility':upper if feasible else None,'Actual ex ante volatility':risk,'Risk gap':risk-upper if feasible else None,
            'Feasible minimum':None if intervals[label] is None else intervals[label][0]*vols[label],
            'Feasible maximum':None if intervals[label] is None else intervals[label][1]*vols[label],
            'Risky scale':scale,'One-way turnover':turnover,'Cash':target['Cash'],'Initial exception':initial})
    return targets,pd.DataFrame(rows).set_index('Strategy')


def replay_common_risk(prices, cash_returns, forecast, policy, schedule, annual_rf=.03, training_rows=252):
    """New retrospective paired experiment with an independent holdings path.

    Fit t-2. Freeze risky directions/covariance then; at t-1 only apply the
    predeclared cash-scaling rule using actual pretrade holdings. Earn at t.
    """
    returns=prices[ASSETS].pct_change(fill_method=None).iloc[1:]
    if not returns.index.equals(cash_returns.index):raise ValueError('Cash/date mismatch.')
    dates=returns.index[returns.index>=schedule[0]];labels=['Scenario common risk','Equal weight common risk']
    states={k:pd.Series(np.r_[np.zeros(len(ASSETS)),1.],index=ASSETS+['Cash']) for k in labels}
    tables={k:[] for k in labels};audits=[];previous=None
    equal=pd.Series(1/len(ASSETS),index=ASSETS)
    expiry=pd.Timestamp(forecast['period_end'])-pd.Timedelta(days=forecast['minimum_remaining_days']-1)
    schedule=pd.DatetimeIndex(schedule).sort_values()
    expiry_positions=np.flatnonzero(returns.index>=expiry)
    if len(expiry_positions) and expiry_positions[0]+1<len(returns):
        schedule=schedule.union(returns.index[expiry_positions[0]+1:expiry_positions[0]+2])
    for effective in schedule:
        pos=returns.index.get_loc(effective)
        if pos<2:raise ValueError('Need decision and execution observations before return.')
        decision,execution=returns.index[pos-2:pos]
        for label in labels:
            if previous is not None:
                for day in returns.loc[previous:decision].index:
                    st=states[label];_,w,c,_=portfolio_step(st[ASSETS],st['Cash'],returns.loc[day],cash_returns.at[day],0.)
                    states[label]=pd.Series(np.r_[w,c],index=ASSETS+['Cash'])
        covariance=estimate_covariance(returns.loc[:decision].tail(training_rows),'sample')
        mapping=mapped_price_target(forecast,prices,decision,annual_rf)
        if execution>=expiry:mapping=None
        detail=black_litterman(covariance,risk_aversion=policy['risk_aversion'],
            views=[] if mapping is None else [mapping['view']],omega=None if mapping is None else [[mapping['Omega annual variance']]],return_details=True)
        direction=stable_allocation(detail['posterior'],covariance,states[labels[0]][ASSETS],.35,
            policy['risk_aversion'],policy['max_active_weight'],10.,policy['holding_years'])
        directions={labels[0]:direction,labels[1]:equal}
        for label in labels:
            if previous is not None:
                st=states[label];_,w,c,_=portfolio_step(st[ASSETS],st['Cash'],returns.loc[execution],cash_returns.at[execution],0.)
                states[label]=pd.Series(np.r_[w,c],index=ASSETS+['Cash'])
        targets,audit=common_risk_pair(directions,states,covariance,
            cap=min(.35,1/len(ASSETS)+policy['max_active_weight']),turnover_limit=policy['max_one_way_turnover'],initial=previous is None)
        audit['First return']=effective;audit['Decision close']=decision;audit['Execution close']=execution
        audit['Fit last observation']=returns.loc[:decision].index[-1];audit['View active']=mapping is not None
        audits.append(audit.reset_index())
        for label in labels:tables[label].append(targets[label].rename(effective));states[label]=targets[label]
        previous=effective
    target_tables={k:pd.DataFrame(v) for k,v in tables.items()};paths={};ledgers={}
    for label in labels:
        paths[label],ledgers[label]=evaluate_targets(returns.loc[dates],target_tables[label],annual_rf,10.,100.,cash_returns.loc[dates])
    # Independent accounting replay must agree with the execution audit.
    audit=pd.concat(audits,ignore_index=True)
    for label in labels:
        actual=ledgers[label]['One-way turnover'].to_numpy()
        expected=audit.loc[audit.Strategy==label,'One-way turnover'].to_numpy()
        if not np.allclose(actual,expected,atol=1e-9):raise RuntimeError('Independent turnover ledger disagrees.')
    return {'returns':pd.DataFrame(paths),'targets':target_tables,'audit':audit,'ledgers':ledgers}


def basis_walkforward(prices, valuations, minimum=40, prior_sigma=.02, prior_strength=40):
    """Prior-only diagnostic of close/NAV timing basis; NOT forecast Omega.

    Zero-centred RMSE shrunk toward the existing assumption; no P&L tuning.
    NAV and ETF close differ in observation time. Serial dependence is retained.
    """
    if minimum<2 or prior_sigma<=0 or prior_strength<=0:raise ValueError('Invalid basis policy.')
    joined=pd.concat([prices['GLD'].rename('Close'),valuations['NAV per share'].rename('NAV')],axis=1).dropna()
    if (joined<=0).any().any() or not np.isfinite(joined).all().all():raise ValueError('Invalid basis inputs.')
    basis=joined.Close/joined.NAV-1;rows=[]
    for i in range(minimum,len(basis)):
        train=basis.iloc[:i];variance=(float((train**2).sum())+prior_strength*prior_sigma**2)/(len(train)+prior_strength)
        sigma=float(np.sqrt(variance));error=float(basis.iloc[i])
        rows.append({'Date':basis.index[i],'Training end':train.index[-1],'Training observations':len(train),
            'Past mean basis':float(train.mean()),'Past RMSE':float(np.sqrt((train**2).mean())),
            'Shrunk sigma':sigma,'Observed basis':error,'Within assumed 95pct band':abs(error)<=1.96*sigma})
    return basis.rename('Close/NAV minus one'),pd.DataFrame(rows)


def forecast_calibration(records, asof, minimum_cycles=8, prior_sigma=.10, prior_strength=8):
    """Use only completed, available, comparable, distinct forecast quarters.

    Same-quarter revisions are not independent samples. Eligibility requires
    matching provider/outcome definition and pre-quarter publication.
    """
    now=pd.Timestamp(asof)
    if now.tzinfo is None:raise ValueError('Aware calibration asof required.')
    if minimum_cycles<2 or prior_sigma<=0 or prior_strength<=0:raise ValueError('Invalid calibration policy.')
    errors=[];seen=set();audit=[]
    for record in records:
        r=dict(record);start=pd.Timestamp(r['period_start']);end=pd.Timestamp(r['period_end']);reason=[]
        available=pd.Timestamp(r['available_at_utc'])
        if available.tzinfo is None:raise ValueError('Aware outcome availability required.')
        if available>now:reason.append('not available at decision')
        if end>=now.tz_convert('America/New_York').tz_localize(None).normalize():reason.append('quarter unfinished')
        if pd.Timestamp(r['published_on'])>=start:reason.append('different forecast lead horizon')
        if not r['outcome_definition_verified']:reason.append('outcome proxy/calendar not verified')
        actual=r.get('actual');target=float(r['target'])
        if target<=0 or not np.isfinite(target):raise ValueError('Invalid forecast target.')
        if actual is None or not np.isfinite(actual) or actual<=0:reason.append('completed outcome missing')
        cycle=(r['period_start'],r['period_end'])
        if cycle in seen:reason.append('duplicate forecast quarter')
        if not reason:seen.add(cycle);errors.append(float(actual/target-1))
        audit.append(dict(id=r['id'],eligible=not reason,reason='; '.join(reason) or 'eligible',
            diagnostic_proxy_error=None if actual is None else float(actual/target-1)))
    enough=len(errors)>=minimum_cycles
    sigma=float(np.sqrt((sum(e*e for e in errors)+prior_strength*prior_sigma**2)/(len(errors)+prior_strength))) if enough else prior_sigma
    return {'eligible_cycles':len(errors),'minimum_cycles':minimum_cycles,'forecast_sigma':sigma,
            'status':'PRIOR_ONLY_SHRINKAGE_ESTIMATE' if enough else 'RETAIN_UNCALIBRATED_DEFAULT','audit':audit}


def horizon_status(forecast, recorded_at, sessions_observed=0, completed_cycles=0):
    """Separate quarter scoring, active-view attribution and strategy inference."""
    now=pd.Timestamp(recorded_at)
    if now.tzinfo is None:raise ValueError('Aware protocol timestamp required.')
    end=pd.Timestamp(forecast['period_end']);expiry=end-pd.Timedelta(days=forecast['minimum_remaining_days']-1)
    schedule=mcal.get_calendar('NYSE').schedule(start_date=now.tz_convert('America/New_York').date(),end_date=end+pd.Timedelta(days=10))
    future=schedule.loc[schedule.market_close>now]
    if len(future)<2:raise ValueError('No future execution and return sessions.')
    execution=future.iloc[0].market_close;earned=future.iloc[1].market_close
    active=int(((future.index[:-1]<expiry)&(future.index[1:]<=end)).sum())
    return {'recorded_at_utc':now.tz_convert('UTC').isoformat(),'next_execution_close_utc':execution.isoformat(),
        'first_return_close_utc':earned.isoformat(),'view_expiry_execution_boundary':str(expiry.date()),
        'remaining_active_return_sessions':active,'minimum_strategy_sessions':60,'minimum_completed_forecast_cycles':8,
        'strategy_inference_admitted':sessions_observed>=60 and completed_cycles>=8,
        'completed_quarter_score_admitted':now.tz_convert('America/New_York').tz_localize(None).normalize()>end,
        'score_rule':'Quarter average forecast error separately; portfolio returns across frozen cycles. No inference from this unfinished quarter.'}


def canonical_hash(document):
    return hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def verify_decision_journal(directory):
    """Verify sequence and hash chain. Local tamper evidence, not external notarization."""
    entries=[];previous=None
    for number,path in enumerate(sorted(Path(directory).glob('*.json')),1):
        if path.name!=f'{number:06d}.json':raise ValueError('Missing/reordered journal entry.')
        doc=json.loads(path.read_text(encoding='utf-8'));payload={k:v for k,v in doc.items() if k!='sha256'}
        if doc['sha256']!=canonical_hash(payload) or doc['previous_sha256']!=previous:raise ValueError('Journal chain/tamper failure.')
        if entries and pd.Timestamp(doc['recorded_at_utc'])<pd.Timestamp(entries[-1]['recorded_at_utc']):raise ValueError('Journal time reversal.')
        entries.append(doc);previous=doc['sha256']
    return entries


def append_paper_decision(directory, payload):
    """Write once, before execution. No caller-supplied timestamp/backdating.

    A paper decision is NOT an execution receipt. Outcomes are admitted later
    through a separate pure evaluator, never by editing this entry.
    """
    folder=Path(directory);folder.mkdir(parents=True,exist_ok=True)
    entries=verify_decision_journal(folder);now=pd.Timestamp.now(tz='UTC')
    for key in ['sha256','previous_sha256','recorded_at_utc','sequence']:
        if key in payload:raise ValueError('Caller cannot supply journal identity/time fields.')
    if any(e['decision_id']==payload['decision_id'] for e in entries):raise ValueError('Duplicate decision ID.')
    available=pd.Timestamp(payload['inputs_available_at_utc']);execution=pd.Timestamp(payload['execution_close_utc']);earned=pd.Timestamp(payload['first_return_close_utc'])
    if any(t.tzinfo is None for t in [available,execution,earned]) or not available<=now<execution<earned:
        raise ValueError('Decision must follow input availability and precede execution/outcome.')
    if payload['solver_status']!='MATCHED':raise ValueError('Journal requires a feasible declared paired allocation.')
    if not np.isfinite(payload['transaction_cost_bps']) or not 0<=payload['transaction_cost_bps']<10000:
        raise ValueError('Invalid paper cost assumption.')
    for weights in payload['targets'].values():
        values=np.array(list(weights.values()),float)
        if 'Cash' not in weights or not np.isfinite(values).all() or min(values)<-1e-8 or abs(values.sum()-1)>1e-8:
            raise ValueError('Invalid journal target budget.')
    document=dict(payload,sequence=len(entries)+1,recorded_at_utc=now.isoformat(),previous_sha256=entries[-1]['sha256'] if entries else None)
    document['sha256']=canonical_hash(document)
    # Exclusive creation makes a concurrent sequence collision fail explicitly.
    with (folder/f'{len(entries)+1:06d}.json').open('x',encoding='utf-8') as f:json.dump(document,f,indent=2,allow_nan=False)
    return document


def evaluate_paper_interval(entry, closing_prices, cash_return, now=None):
    """Evaluate only the first fully observed holding interval, independently.

    Supplied close dates must exactly match the recorded interval. First-entry
    cost uses the declared all-cash starting state. No broker execution implied.
    """
    current=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if entry['sha256']!=canonical_hash({k:v for k,v in entry.items() if k!='sha256'}):raise ValueError('Decision receipt was changed.')
    start=pd.Timestamp(entry['execution_close_utc']);end=pd.Timestamp(entry['first_return_close_utc'])
    if current.tzinfo is None or current<end:raise ValueError('Outcome has not completed.')
    if entry['starting_state']!='ALL_CASH_NEW_PAPER_ACCOUNT':raise ValueError('Unsupported initial state.')
    if list(closing_prices.index)!=[start.tz_convert('America/New_York').tz_localize(None).normalize(),end.tz_convert('America/New_York').tz_localize(None).normalize()]:
        raise ValueError('Exact recorded execution/return closes required.')
    if (closing_prices<=0).any().any() or not np.isfinite(closing_prices).all().all() or not np.isfinite(cash_return) or cash_return<=-1:
        raise ValueError('Invalid realized inputs.')
    r=closing_prices.iloc[1]/closing_prices.iloc[0]-1;rows=[]
    for label,target in entry['targets'].items():
        w=pd.Series(target);assets=w.drop('Cash')
        if list(assets.index)!=list(closing_prices.columns):raise ValueError('Outcome asset mismatch.')
        cost=(1-w['Cash'])*entry['transaction_cost_bps']/10000
        net=(1-cost)*(1+float(assets@r)+w['Cash']*cash_return)-1
        rows.append({'Strategy':label,'Net interval return':net,'Initial cost':cost,'Decision sha256':entry['sha256'],
                     'Evidence':'Recorded paper target with subsequently supplied closes; not an execution receipt'})
    return pd.DataFrame(rows)
