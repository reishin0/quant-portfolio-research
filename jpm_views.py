"""Quarter-average gold views, explicit uncertainty and cost-aware controls."""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from portfolio_tools import ASSETS, BENCHMARK, black_litterman, portfolio_step
from research_extensions import estimate_covariance
from research_diagnostics import evaluate_targets, performance_table


def load_gold_valuations(forecast):
    """Read the pinned issuer NAV/ounces pairs; never silently refresh them."""
    path = Path(forecast['valuation_file'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != forecast['valuation_sha256']:
        raise ValueError('Gold valuation file hash mismatch.')
    frame = pd.read_csv(path, index_col='Date', parse_dates=True)
    if (list(frame.columns) != ['Ounces per share', 'NAV per share']
            or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
            or not np.isfinite(frame.to_numpy()).all() or (frame <= 0).any().any()):
        raise ValueError('Invalid dated issuer valuation pairs.')
    return frame


def mapped_price_target(forecast, prices, decision_close, annual_rf=.03,
                        valuations=None, error_scale=1., basis_shift=0.):
    """Condition a quarterly-average forecast on observations already available.

    For N quarter weekdays, observed sum A, n future weekdays and their ACT/365
    times h_j, solve T*N = A + S0*(n + mu*sum(h_j)). S0 is same-date NAV/ounces.
    Convert the expected bullion price at mean(h_j) to GLD using current ounces,
    fee decay, and the decision market close. Propagate forecast error by the
    exact derivative dQ/dT, rather than asserting a provider confidence score.
    """
    if forecast.get('mapping_type') != 'bullion_quarter_average':
        raise ValueError('A quarterly-average observation model is required.')
    decision = pd.Timestamp(decision_close)
    published = pd.Timestamp(forecast['published_on'])
    start, end = pd.Timestamp(forecast['period_start']), pd.Timestamp(forecast['period_end'])
    target, fee = forecast['target_usd_per_ounce'], forecast['annual_expense_ratio']
    forecast_error, basis_error = forecast['forecast_error_fraction'], forecast['basis_error_fraction']
    minimum = forecast['minimum_remaining_days']
    if (not published < start <= end or not isinstance(minimum, int) or minimum < 1
            or not np.isfinite([annual_rf,target,fee,forecast_error,basis_error,error_scale,basis_shift]).all()
            or annual_rf <= -1 or target <= 0 or not 0 <= fee < 1 or forecast_error <= 0
            or basis_error < 0 or error_scale <= 0 or abs(basis_shift) > .1):
        raise ValueError('Invalid forecast dates, fees or error assumptions.')
    if decision <= published or (end-decision).days < minimum:
        return None
    asset = forecast['asset']
    if (not isinstance(prices.index,pd.DatetimeIndex) or prices.index.has_duplicates
            or not prices.index.is_monotonic_increasing or asset not in prices or decision not in prices.index):
        raise ValueError('Exact decision price is required on a sorted unique index.')
    valuations = load_gold_valuations(forecast) if valuations is None else valuations
    known = valuations.loc[:decision]
    if (known.empty or decision not in known.index or known.index.has_duplicates
            or not known.index.is_monotonic_increasing or not np.isfinite(known.to_numpy()).all()
            or (known <= 0).any().any()):
        raise ValueError('Exact same-date issuer NAV and ounces are required; no stale decision pair.')
    ounces, nav = known.loc[decision, ['Ounces per share','NAV per share']].astype(float)
    current = float(prices.at[decision, asset])
    if not np.isfinite(current) or current <= 0:
        raise ValueError('Decision price must be finite and positive.')
    spot = nav / ounces
    quarter = pd.bdate_range(start, end)  # Explicit weekday averaging convention.
    observed, future = quarter[quarter <= decision], quarter[quarter > decision]
    bullion = known['NAV per share'] / known['Ounces per share']
    observed_values = bullion.reindex(bullion.index.union(observed)).ffill().reindex(observed)
    if observed_values.isna().any():
        raise ValueError('Missing already observed quarter valuations.')
    # Carry-forward is solely the declared holiday convention; never bridge an
    # absent price session that should have its own issuer valuation.
    required = prices.loc[start:decision].index.intersection(observed)
    if not required.isin(known.index).all():
        raise ValueError('Missing issuer valuation for an observed price session.')
    times = (future-decision).days.to_numpy(dtype=float)/365
    h = float(times.mean())
    slope = (target*len(quarter)-observed_values.sum()-len(future)*spot)/(spot*times.sum())
    future_spot = spot*(1+slope*h)
    if future_spot <= 0 or (1+slope*times).min() <= 0:
        raise ValueError('Quarterly forecast implies a nonpositive linear price path.')
    conversion = ounces*(1-fee)**h*(1+basis_shift)
    mapped = conversion*future_spot
    cash_horizon = (1+annual_rf)**h-1
    q = (mapped/current-1-cash_horizon)/h
    derivative = conversion/current*len(quarter)/times.sum()
    omega = (derivative*target*forecast_error*error_scale)**2 + (basis_error*error_scale/h)**2
    return {'view': (asset,None,float(q),1.), 'Omega annual variance': float(omega),
            'Asset':asset,'Published':str(published.date()),'Decision close':decision,
            'Mapping recorded':forecast['recorded_on'],'Quarter start':str(start.date()),
            'Quarter end':str(end.date()),'Quarter weekdays':len(quarter),
            'Observed quarter weekdays':len(observed),'Mean remaining years':h,
            'NAV per share':nav,'Ounces per share':ounces,'NAV-implied bullion':spot,
            'Decision ETF close':current,'Mapped mean future ETF price':mapped,
            'Implied annual bullion slope':float(slope),'Annual excess Q':float(q),
            'Forecast error fraction':forecast_error*error_scale,
            'Basis error fraction':basis_error*error_scale,'Basis shift assumption':basis_shift,
            'Evidence':'retrospective reconstruction; weekday average; NAV-implied bullion proxy'}


def stable_allocation(expected, covariance, current, cap=.35, risk_aversion=3.07,
                      max_active_weight=.15, transaction_cost_bps=10., holding_years=21/252):
    """Concave mean/variance utility minus explicit one-way trading costs.

    L1 epigraph variables make the cost term smooth for SLSQP. The static active
    bounds are relative to equal prior weights. Execution turnover is separately
    capped using actual holdings at the execution close, without refitting Q.
    """
    names = list(covariance.columns); n = len(names)
    mu, sigma, old = np.asarray(expected,float), covariance.to_numpy(float), np.asarray(current,float)
    if (list(covariance.index) != names or list(expected.index) != names
            or mu.shape != (n,) or old.shape != (n,) or not np.isfinite([*mu,*old,*sigma.ravel()]).all()
            or not np.allclose(sigma,sigma.T) or np.linalg.eigvalsh(sigma).min() < -1e-10
            or (old < -1e-10).any() or old.sum() > 1+1e-8
            or not np.isfinite([cap,risk_aversion,max_active_weight,transaction_cost_bps,holding_years]).all()
            or not 1/n <= cap <= 1 or risk_aversion <= 0 or max_active_weight < 0
            or transaction_cost_bps < 0 or holding_years <= 0):
        raise ValueError('Invalid optimizer labels, covariance, holdings or policy.')
    lower, upper = max(0.,1/n-max_active_weight), min(cap,1/n+max_active_weight)
    cost = transaction_cost_bps/10000/holding_years*.5
    def objective(x):
        w=x[:n]
        return risk_aversion/2*w@sigma@w-mu@w+cost*x[n:].sum()
    def gradient(x):
        return np.r_[risk_aversion*sigma@x[:n]-mu, np.full(n,cost)]
    # Initial cash movement is constant across fully invested candidate targets.
    constraints=[{'type':'eq','fun':lambda x:x[:n].sum()-1,
                  'jac':lambda x:np.r_[np.ones(n),np.zeros(n)]},
                 {'type':'ineq','fun':lambda x:x[n:]-(x[:n]-old),
                  'jac':lambda x:np.c_[-np.eye(n),np.eye(n)]},
                 {'type':'ineq','fun':lambda x:x[n:]+(x[:n]-old),
                  'jac':lambda x:np.c_[np.eye(n),np.eye(n)]}]
    x0=np.r_[np.full(n,1/n),np.abs(np.full(n,1/n)-old)]
    fit=minimize(objective,x0,jac=gradient,bounds=[(lower,upper)]*n+[(0,None)]*n,
                 constraints=constraints,method='SLSQP',options={'ftol':1e-12,'maxiter':1000})
    w=fit.x[:n]
    if (not fit.success or abs(w.sum()-1)>1e-7 or min(w)<lower-1e-7
            or max(w)>upper+1e-7 or (fit.x[n:]+1e-7<np.abs(w-old)).any()):
        raise RuntimeError(f'Cost-aware optimizer failed: {fit.message}')
    return pd.Series(w,index=names)


def limit_execution(target, current, max_turnover=.10, initial=False):
    """Interpolate toward the announced target to enforce actual one-way turnover.

    Includes cash. Initial deployment from all cash is explicitly exempt. Drift
    can leave an executed holding outside target bounds: report it, do not assert
    simultaneous hard bounds that can be infeasible under the turnover budget.
    """
    if (not target.index.equals(current.index) or not np.isfinite([*target,*current,max_turnover]).all()
            or not 0 < max_turnover <= 1 or min(target)<-1e-8 or min(current)<-1e-8
            or abs(target.sum()-1)>1e-7 or abs(current.sum()-1)>1e-7):
        raise ValueError('Execution needs matching long-only budgeted holdings and positive turnover cap.')
    turnover=float(np.abs(target-current).sum()/2)
    if initial and not (abs(current['Cash']-1)<1e-8):
        raise ValueError('Initial exception requires an all-cash portfolio.')
    fraction=1. if initial or turnover<=max_turnover else max_turnover/turnover
    return current+fraction*(target-current),fraction


def run_jpm_view_study(prices, prior_result, forecast, annual_rf=.03,
                       valuations=None, error_scale=1., basis_shift=0., policy=None,
                       prospective_after=None):
    """Dated signals and actual execution guard, with five common-cost controls.

    Forecast fit at t-2, execution at t-1, first earned return t. Current holdings
    in the objective stop at t-2. The turnover guard alone sees holdings at t-1.
    All paths start in cash and use identical execution dates and cash accounting.
    prospective_after additionally forbids fitting on or before the frozen date.
    """
    policy = dict(risk_aversion=3.07,max_active_weight=.15,max_one_way_turnover=.10,
                  holding_years=21/252,fixed_gold_overweight=.05,initial_cash_entry_exempt=True) if policy is None else dict(policy)
    if policy['initial_cash_entry_exempt'] is not True or not 0 <= policy['fixed_gold_overweight'] <= .15:
        raise ValueError('Invalid declared initial-entry or fixed-gold policy.')
    valuations = load_gold_valuations(forecast) if valuations is None else valuations
    all_returns=prior_result['returns']; dates=prior_result['portfolio_returns'].index
    expiry=pd.Timestamp(forecast['period_end'])-pd.Timedelta(days=forecast['minimum_remaining_days']-1)
    schedule=prior_result['view_history'].index
    possible=all_returns.index[all_returns.index>=expiry]
    if len(possible):
        loc=all_returns.index.get_loc(possible[0])
        if loc+1<len(all_returns) and all_returns.index[loc+1] in dates:
            schedule=schedule.union(all_returns.index[loc+1:loc+2])
    if prospective_after is not None:
        cutoff=max(pd.Timestamp(prospective_after),pd.Timestamp(forecast['recorded_on']))
        schedule=pd.DatetimeIndex([d for d in schedule if all_returns.index[all_returns.index.get_loc(d)-2]>cutoff])
        if not len(schedule):
            raise ValueError('No subsequent decision/execution/return observations after freeze.')
        dates=dates[dates>=schedule[0]]
    schedule=schedule.sort_values()
    labels=['JPM-mapped scenario','Matched prior','Fixed GLD overweight','GLD exposure matched','Risk matched equal weight']
    columns=ASSETS+['Cash']; equal=pd.Series(1/len(ASSETS),index=ASSETS)
    cash=prior_result['cash_returns'].loc[dates]
    tables={name:[] for name in labels}; states={name:pd.Series([0.]*len(ASSETS)+[1.],index=columns) for name in labels}
    audits=[]; control_audits=[]; previous_effective=None
    for effective in schedule:
        pos=all_returns.index.get_loc(effective)
        decision,execution=all_returns.index[pos-2],all_returns.index[pos-1]
        # Propagate previous post-trade holdings through only the decision close.
        for name in labels:
            if previous_effective is not None:
                for day in all_returns.loc[previous_effective:decision].index:
                    st=states[name]
                    _,w,c,_=portfolio_step(st[ASSETS].to_numpy(),st['Cash'],all_returns.loc[day,ASSETS].to_numpy(),float(prior_result['cash_returns'].at[day]),0.)
                    states[name]=pd.Series(np.r_[w,c],index=columns)
        train=all_returns.loc[:decision]
        if prior_result['training_window_days'] is not None:train=train.tail(prior_result['training_window_days'])
        covariance=estimate_covariance(train[ASSETS],prior_result['covariance_estimator'])
        mapping=mapped_price_target(forecast,prices,decision,annual_rf,valuations,error_scale,basis_shift)
        if execution>=expiry:mapping=None
        details=black_litterman(covariance,risk_aversion=policy['risk_aversion'],views=[] if mapping is None else [mapping['view']],
            omega=None if mapping is None else [[mapping['Omega annual variance']]],return_details=True)
        announced={}
        for name,expected in [('JPM-mapped scenario',details['posterior']),('Matched prior',details['prior'])]:
            w=stable_allocation(expected,covariance,states[name][ASSETS],prior_result['max_weight'],
                policy['risk_aversion'],policy['max_active_weight'],prior_result['transaction_cost_bps'],policy['holding_years'])
            announced[name]=pd.concat([w,pd.Series({'Cash':0.})])
        fixed=equal.copy()
        if mapping is not None:
            gold=min(equal['GLD']+policy['fixed_gold_overweight'],prior_result['max_weight'])
            fixed[:]=(1-gold)/(len(ASSETS)-1);fixed['GLD']=gold
        announced[labels[2]]=pd.concat([fixed,pd.Series({'Cash':0.})])
        # Only execution holdings, not Q/covariance, incorporate the next close.
        for name in labels:
            st=states[name]
            if previous_effective is not None:
                _,w,c,_=portfolio_step(st[ASSETS].to_numpy(),st['Cash'],all_returns.loc[execution,ASSETS].to_numpy(),float(prior_result['cash_returns'].at[execution]),0.)
                states[name]=pd.Series(np.r_[w,c],index=columns)
        jpm_executed,_=limit_execution(announced[labels[0]],states[labels[0]],policy['max_one_way_turnover'],previous_effective is None)
        gold=float(jpm_executed['GLD']);exposure=equal.copy();exposure[:]=(1-gold)/(len(ASSETS)-1);exposure['GLD']=gold
        announced[labels[3]]=pd.concat([exposure,pd.Series({'Cash':0.})])
        strategy_vol=float(np.sqrt(jpm_executed[ASSETS]@covariance@jpm_executed[ASSETS]))
        equal_vol=float(np.sqrt(equal@covariance@equal))
        scale=min(1.,strategy_vol/equal_vol) if equal_vol>0 else 1.
        announced[labels[4]]=pd.concat([equal*scale,pd.Series({'Cash':1-scale})])
        for name in labels:
            target,fraction=limit_execution(announced[name],states[name],policy['max_one_way_turnover'],previous_effective is None)
            actual_turnover=float(np.abs(target-states[name]).sum()/2)
            tables[name].append(target.rename(effective));states[name]=target
            control_audits.append({'Date':effective,'Strategy':name,'Execution fraction':fraction,'One-way turnover':actual_turnover,
                'Ex ante volatility':float(np.sqrt(target[ASSETS]@covariance@target[ASSETS])),
                'GLD weight':target['GLD'],'GLD difference vs strategy':target['GLD']-jpm_executed['GLD'],
                'Risk difference vs strategy':float(np.sqrt(target[ASSETS]@covariance@target[ASSETS]))-strategy_vol,
                'Executed max asset weight':target[ASSETS].max(),'Target upper bound':min(prior_result['max_weight'],1/len(ASSETS)+policy['max_active_weight'])})
        row={'Date':effective,'Decision close':decision,'Execution close':execution,'Active':mapping is not None,
             'Source publication':forecast['published_on'],'Mapping recorded':forecast['recorded_on'],
             'Evidence':'subsequent frozen-rule evaluation' if prospective_after is not None else 'retrospective publication reconstruction'}
        if mapping is not None:
            row.update({k:v for k,v in mapping.items() if k not in {'view','Evidence'}})
            row['Effective marginal weight']=float(details['views']['Effective marginal weight'].iloc[0])
        audits.append(row);previous_effective=effective
    paths,ledgers={},{};target_tables={k:pd.DataFrame(v) for k,v in tables.items()}
    for name,t in target_tables.items():
        paths[name],ledgers[name]=evaluate_targets(all_returns.loc[dates,ASSETS],t,annual_rf,
            prior_result['transaction_cost_bps'],prior_result['annual_short_borrow_bps'],cash_returns=cash)
    paths=pd.DataFrame(paths);audit=pd.DataFrame(audits).set_index('Date');active=audit.index[audit.Active]
    def summarize(period):
        if period.empty:return pd.DataFrame()
        frame=performance_table(period,annual_rf,cash_returns=cash.loc[period.index])
        frame['Total period return']=(1+period).prod()-1;frame['Sessions']=len(period)
        frame['First date']=str(period.index[0].date());frame['Last date']=str(period.index[-1].date())
        for name in frame.index:
            frame.loc[name,'One-way turnover']=ledgers[name].loc[period.index.intersection(ledgers[name].index),'One-way turnover'].sum()
        return frame
    last=prices.index[-1];mapping=mapped_price_target(forecast,prices,last,annual_rf,valuations,error_scale,basis_shift)
    train=all_returns.loc[:last]
    if prior_result['training_window_days'] is not None:train=train.tail(prior_result['training_window_days'])
    covariance=estimate_covariance(train[ASSETS],prior_result['covariance_estimator'])
    details=black_litterman(covariance,risk_aversion=policy['risk_aversion'],views=[] if mapping is None else [mapping['view']],
        omega=None if mapping is None else [[mapping['Omega annual variance']]],return_details=True)
    # Latest illustration references holdings drifted to the last observed close.
    latest={}
    for name,expected in [('JPM-mapped scenario',details['posterior']),('Matched prior',details['prior'])]:
        st=states[name]
        for day in all_returns.loc[previous_effective:last].index:
            _,w,c,_=portfolio_step(st[ASSETS].to_numpy(),st['Cash'],all_returns.loc[day,ASSETS].to_numpy(),float(prior_result['cash_returns'].at[day]),0.)
            st=pd.Series(np.r_[w,c],index=columns)
        latest[name]=stable_allocation(expected,covariance,st[ASSETS],prior_result['max_weight'],policy['risk_aversion'],
            policy['max_active_weight'],prior_result['transaction_cost_bps'],policy['holding_years'])
    latest=pd.DataFrame(latest);latest['Difference']=latest.iloc[:,0]-latest.iloc[:,1]
    return {'returns':paths,'targets':target_tables,'ledgers':ledgers,'audit':audit,
            'control_audit':pd.DataFrame(control_audits).set_index(['Date','Strategy']),
            'summary':summarize(paths),'since_first_activation':summarize(paths.loc[active[0]:]) if len(active) else pd.DataFrame(),
            'latest_weights':latest,'latest_details':details,'latest_mapping':mapping,'latest_price_date':last,
            'expiry_execution_boundary':expiry,'policy':policy}


def jpm_sensitivity(prices, prior_result, forecast, annual_rf=.03, policy=None):
    """Report all predeclared error/basis cases without performance selection."""
    valuations=load_gold_valuations(forecast)
    cases=[('base',1.,0.),('error_half',.5,0.),('error_double',2.,0.),('basis_minus_2pct',1.,-.02),('basis_plus_2pct',1.,.02)]
    rows,runs=[],{}
    for label,scale,basis in cases:
        run=run_jpm_view_study(prices,prior_result,forecast,annual_rf,valuations,scale,basis,policy)
        runs[label]=run;s=run['since_first_activation']
        row={'Case':label,'Forecast error fraction':forecast['forecast_error_fraction']*scale,
             'Basis error fraction':forecast['basis_error_fraction']*scale,'Basis shift':basis,
             'Active rebalances':int(run['audit'].Active.sum()),'Status':'evaluated reconstruction' if len(s) else 'no eligible dates'}
        if len(s):
            row.update({'First date':s.iloc[0]['First date'],'Last date':s.iloc[0]['Last date'],'Sessions':int(s.iloc[0]['Sessions']),
                'Scenario period return':s.loc['JPM-mapped scenario','Total period return'],
                'Prior period return':s.loc['Matched prior','Total period return'],
                'Period return difference':s.loc['JPM-mapped scenario','Total period return']-s.loc['Matched prior','Total period return'],
                'Scenario maximum drawdown':s.loc['JPM-mapped scenario','Max drawdown']})
        rows.append(row)
    return pd.DataFrame(rows).set_index('Case'),runs
