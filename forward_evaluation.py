"""Freeze a research protocol and evaluate only observations arriving afterwards.

No network access, scheduling or orders. Run --help for the explicit data contract.
Existing freezes and output folders are never replaced.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from data_tools import load_sofr_cash_returns, audit_prices
from portfolio_tools import ASSETS, BENCHMARK
from jpm_views import run_jpm_view_study

ROOT=Path(__file__).resolve().parent
CODE_FILES=['portfolio_tools.py','research_extensions.py','research_diagnostics.py','jpm_views.py','forward_evaluation.py','data_tools.py']
PACKAGES=['numpy','pandas','scipy','pandas_market_calendars','exchange_calendars']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def notebook_digest(path):
    nb=json.loads(Path(path).read_text(encoding='utf-8'))
    return hashlib.sha256('\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code').encode()).hexdigest()


def freeze_protocol(path):
    now=datetime.now(timezone.utc)
    files=CODE_FILES+['data/jpm_research_views_20261009.json','data/gld_valuation_20261009.csv',
                     'data/etf_adjusted_20261009.csv','data/sofr_20261009.csv','data/sofr_provenance_20261009.json']
    document={'schema_version':1,'frozen_at_utc':now.isoformat(),
        'decision_cutoff_date':str(now.astimezone(ZoneInfo('America/New_York')).date()),
        'last_observed_price':'2026-10-08',
        'policy':'First fit strictly after cutoff, execute next close, earn following return. No retrospective rows count.',
        'selection':'Fixed 252-session sample covariance, no subsequent reselection or sensitivity winner.',
        'training_window_days':252,'covariance_estimator':'sample','annual_rf':.03,'max_weight':.35,
        'transaction_cost_bps':10.,'annual_short_borrow_bps':100.,
        'prices_file':'data/etf_adjusted_20261009.csv','views_file':'data/jpm_research_views_20261009.json',
        'file_sha256':{name:digest(ROOT/name) for name in files},
        'notebook_code_sha256':notebook_digest(ROOT/'portfolio_construction.ipynb'),
        'packages':{name:version(name) for name in PACKAGES},
        'evidence':'No subsequent observations at freeze; historical reconstruction excluded.',
        'evaluation_rule':'Report all five controls and all net paths. Minimum 60 subsequent sessions before bootstrap inference. No alpha claim from an unfinished quarter.'}
    # Exclusive creation is intentional: modifying a frozen design requires a new file.
    with Path(path).open('x',encoding='utf-8') as f:json.dump(document,f,indent=2);f.write('\n')
    return document


def verify_protocol(path, root=ROOT):
    frozen=json.loads(Path(path).read_text(encoding='utf-8'))
    for name,expected in frozen['file_sha256'].items():
        if digest(Path(root)/name)!=expected:raise ValueError(f'Frozen file changed: {name}. Create a new dated protocol.')
    if notebook_digest(Path(root)/'portfolio_construction.ipynb')!=frozen['notebook_code_sha256']:
        raise ValueError('Frozen notebook calculation changed. Create a new dated protocol.')
    for name,expected in frozen['packages'].items():
        if version(name)!=expected:raise ValueError(f'Frozen runtime changed: {name}')
    if pd.Timestamp(frozen['frozen_at_utc'])>pd.Timestamp.now(tz='UTC'):
        raise ValueError('Protocol freeze is in the future.')
    if pd.Timestamp(frozen['decision_cutoff_date'])<pd.Timestamp(frozen['last_observed_price']):
        raise ValueError('Cutoff cannot precede already observed prices.')
    return frozen


def check_extension(original, extended, label):
    if (not isinstance(extended.index,pd.DatetimeIndex) or extended.index.has_duplicates
            or not extended.index.is_monotonic_increasing or list(extended.columns)!=list(original.columns)
            or not np.isfinite(extended.to_numpy()).all()):
        raise ValueError(f'Invalid {label} extension schema, dates or values.')
    if not extended.loc[:original.index[-1]].index.equals(original.index):
        raise ValueError(f'{label} must retain every frozen historical date without insertion.')
    # CSV round trips may differ at machine precision; economic revisions cannot pass.
    if not np.allclose(extended.loc[original.index],original,rtol=1e-13,atol=1e-13):
        raise ValueError(f'{label} revised previously frozen observations.')


def evaluate_forward(frozen, prices, cash, valuations, now=None):
    now=pd.Timestamp.now(tz='America/New_York') if now is None else pd.Timestamp(now).tz_convert('America/New_York')
    last_allowed=now.normalize().tz_localize(None)
    if now.hour<16:last_allowed-=pd.Timedelta(days=1)
    if prices.index[-1]>last_allowed:raise ValueError('Prices include a future or unfinished US close.')
    old=pd.read_csv(ROOT/frozen['prices_file'],index_col='Date',parse_dates=True)
    doc=json.loads((ROOT/frozen['views_file']).read_text());forecast=doc['forecast']
    old_gold=pd.read_csv(ROOT/forecast['valuation_file'],index_col='Date',parse_dates=True)
    old_cash,_=load_sofr_cash_returns(old.index)
    check_extension(old,prices,'Prices');check_extension(old_gold,valuations,'Issuer valuations')
    check_extension(old_cash.rename('Cash return').to_frame(),cash.rename('Cash return').to_frame(),'Cash')
    if (prices<=0).any().any() or (valuations<=0).any().any() or (cash<=-1).any():
        raise ValueError('Positive prices/valuations and valid decimal cash returns required.')
    audit_prices(prices, prices.index[0], prices.index[-1]+pd.Timedelta(days=1))
    returns=prices.pct_change(fill_method=None).iloc[1:]
    if not cash.index.equals(returns.index):raise ValueError('Cash returns must match all close-to-close price intervals.')
    cutoff=pd.Timestamp(frozen['decision_cutoff_date'])
    eligible=pd.DatetimeIndex([returns.index[i] for i in range(2,len(returns)) if returns.index[i-2]>cutoff])
    if not len(eligible):return None
    # Enter at the first admissible execution, then use the established monthly schedule.
    monthly=returns.groupby(returns.index.to_period('M')).head(1).index
    schedule=monthly.intersection(eligible).union(eligible[:1])
    base={'returns':returns,'portfolio_returns':pd.DataFrame(index=eligible),'view_history':pd.DataFrame(index=schedule),
          'cash_returns':cash,**{k:frozen[k] for k in ['training_window_days','covariance_estimator','max_weight','transaction_cost_bps','annual_short_borrow_bps']}}
    return run_jpm_view_study(prices,base,forecast,frozen['annual_rf'],valuations=valuations,
                              policy=doc['allocation_policy'],prospective_after=cutoff)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',default='data/forward_protocol_20261009.json')
    p.add_argument('--freeze',action='store_true',help='Create this protocol once, only after completing and testing revisions.')
    p.add_argument('--prices',help='Extended Date-indexed adjusted prices with identical frozen history and asset columns.')
    p.add_argument('--cash',help='Extended CSV: Date,Cash return; decimal realized interval cash returns including frozen history.')
    p.add_argument('--valuations',help='Extended CSV: Date,Ounces per share,NAV per share; include the frozen issuer history.')
    args=p.parse_args()
    if args.freeze:
        if any([args.prices,args.cash,args.valuations]):p.error('Freeze and evaluate are separate operations.')
        result=freeze_protocol(args.protocol);print(json.dumps(result,indent=2));return
    frozen=verify_protocol(args.protocol)
    if not any([args.prices,args.cash,args.valuations]):
        print(f"Verified frozen specification. No new data supplied; forward evidence pending. Decisions must be after {frozen['decision_cutoff_date']}.")
        return
    if not all([args.prices,args.cash,args.valuations]):p.error('Provide prices, cash and valuations together; no synthetic fallback.')
    prices=pd.read_csv(args.prices,index_col='Date',parse_dates=True)
    cash_frame=pd.read_csv(args.cash,index_col='Date',parse_dates=True)
    if list(cash_frame.columns)!=['Cash return']:raise ValueError('Cash CSV must have only Date,Cash return columns.')
    valuations=pd.read_csv(args.valuations,index_col='Date',parse_dates=True)
    run=evaluate_forward(frozen,prices,cash_frame['Cash return'],valuations)
    if run is None:print('No eligible subsequent decision/execution/return observations. Forward evidence pending.');return
    output=ROOT/'outputs'/datetime.now(timezone.utc).strftime('forward_%Y%m%dT%H%M%S_%fZ')
    output.mkdir(parents=True,exist_ok=False)
    for key in ['returns','summary','audit','control_audit']:run[key].to_csv(output/f'{key}.csv')
    for i,label in enumerate(run['targets']):
        run['targets'][label].to_csv(output/f'control_{i}_targets.csv');run['ledgers'][label].to_csv(output/f'control_{i}_trades.csv')
    receipt={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':digest(args.protocol),
             'input_sha256':{name:digest(getattr(args,name)) for name in ['prices','cash','valuations']},
             'sessions':len(run['returns']),'evidence':'Subsequent supplied observations under the verified frozen design; provenance of extended inputs requires source documentation.',
             'control_order':list(run['targets'])}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(run['summary'][['Total period return','Max drawdown','Sessions']].to_string());print(output)


if __name__=='__main__':main()
