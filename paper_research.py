"""Explicit local paper-decision capture and separate outcome evaluation.

Never schedules work, submits orders or obtains broker holdings. Run from the
repository root. An existing decision cannot be overwritten or backdated.
"""
import argparse
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
import numpy as np
import pandas as pd
from forward_evaluation import verify_protocol
from portfolio_tools import ASSETS,black_litterman
from research_extensions import estimate_covariance
from jpm_views import mapped_price_target,stable_allocation
from portfolio_amendments import common_risk_pair,horizon_status,append_paper_decision,evaluate_paper_interval

ROOT=Path(__file__).resolve().parent


def verify_amended_protocol(path):
    doc=json.loads(Path(path).read_text(encoding='utf-8'))
    verify_protocol(ROOT/'data/forward_protocol_20261009.json')
    for name,digest in doc['file_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Amended protocol pin changed: '+name)
    for name,expected in doc['packages'].items():
        if version(name)!=expected:raise ValueError('Amended runtime changed: '+name)
    return doc


def prepare_paper_payload(protocol,path):
    now=pd.Timestamp.now(tz='UTC')
    prices=pd.read_csv(ROOT/protocol['prices_file'],index_col='Date',parse_dates=True)
    doc=json.loads((ROOT/protocol['views_file']).read_text(encoding='utf-8'));forecast=doc['forecast'];policy=doc['allocation_policy']
    decision=prices.index[-1]
    # Price information must be the immediately preceding completed NYSE close,
    # not stale data opportunistically journalled weeks later.
    import pandas_market_calendars as mcal
    schedule=mcal.get_calendar('NYSE').schedule(start_date=decision-pd.Timedelta(days=7),end_date=now.tz_convert('America/New_York').date())
    completed=schedule[schedule.market_close<=now]
    if completed.empty or completed.index[-1]!=decision:raise ValueError('Refresh inputs: latest completed NYSE close missing.')
    covariance=estimate_covariance(prices[ASSETS].pct_change(fill_method=None).dropna().tail(252),'sample')
    mapping=mapped_price_target(forecast,prices,decision,.03)
    horizon=horizon_status(forecast,now)
    execution=pd.Timestamp(horizon['next_execution_close_utc']).tz_convert('America/New_York').tz_localize(None).normalize()
    if execution>=pd.Timestamp(horizon['view_expiry_execution_boundary']):mapping=None
    details=black_litterman(covariance,risk_aversion=policy['risk_aversion'],views=[] if mapping is None else [mapping['view']],
        omega=None if mapping is None else [[mapping['Omega annual variance']]],return_details=True)
    names=['Scenario common risk','Equal weight common risk']
    currents={k:pd.Series(np.r_[np.zeros(len(ASSETS)),1.],index=ASSETS+['Cash']) for k in names}
    direction=stable_allocation(details['posterior'],covariance,currents[names[0]][ASSETS],.35,
        policy['risk_aversion'],policy['max_active_weight'],10.,policy['holding_years'])
    targets,audit=common_risk_pair({names[0]:direction,names[1]:pd.Series(1/len(ASSETS),index=ASSETS)},currents,covariance,
        cap=.275,turnover_limit=.10,initial=True)
    if not audit.Status.eq('MATCHED').all():raise ValueError('Common-risk initial paper allocation unavailable.')
    return {'decision_id':'paper_pair_'+str(decision.date()),'information_close':str(decision.date()),
        'protocol_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'input_sha256':protocol['file_sha256'],
        'inputs_available_at_utc':protocol['input_vintage_available_at_utc'],
        'execution_close_utc':horizon['next_execution_close_utc'],'first_return_close_utc':horizon['first_return_close_utc'],
        'starting_state':'ALL_CASH_NEW_PAPER_ACCOUNT','solver_status':'MATCHED','transaction_cost_bps':10.,
        'targets':{k:v.to_dict() for k,v in targets.items()},'common_risk_audit':audit.reset_index().to_dict('records'),
        'forecast_error_fraction':.10,'basis_error_fraction':.02,'view_active':mapping is not None,
        'horizon':horizon,'evidence':'Prospectively recorded local paper decision; no execution or return observed.',
        'policy_scope':'First holding interval only. Continued monthly decisions require new verified input vintages and drifted paper holdings; no all-cash resets presented as a continuous track record.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    record=sub.add_parser('record');record.add_argument('--protocol',required=True);record.add_argument('--journal',required=True)
    evaluate=sub.add_parser('evaluate');evaluate.add_argument('--decision',required=True);evaluate.add_argument('--prices',required=True)
    evaluate.add_argument('--cash-return',type=float,required=True);evaluate.add_argument('--output',required=True)
    args=p.parse_args()
    if args.action=='record':
        doc=verify_amended_protocol(args.protocol);payload=prepare_paper_payload(doc,args.protocol)
        result=append_paper_decision(args.journal,payload);print(json.dumps(result,indent=2))
    else:
        entry=json.loads(Path(args.decision).read_text(encoding='utf-8'))
        prices=pd.read_csv(args.prices,index_col='Date',parse_dates=True)
        result=evaluate_paper_interval(entry,prices,args.cash_return)
        out=Path(args.output);out.mkdir(parents=True,exist_ok=False);result.to_csv(out/'paper_outcome.csv',index=False)
        (out/'receipt.json').write_text(json.dumps({'decision_sha256':entry['sha256'],'observed_at_utc':pd.Timestamp.now(tz='UTC').isoformat(),
            'price_input_sha256':hashlib.sha256(Path(args.prices).read_bytes()).hexdigest(),'cash_return':args.cash_return,
            'evidence':'User-supplied observed closes; source provenance must accompany the file. No broker execution claimed.'},indent=2),encoding='utf-8')
        print(result.to_string(index=False))


if __name__=='__main__':main()
