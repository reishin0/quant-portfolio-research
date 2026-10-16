"""Acquire a separate dated research vintage without editing frozen inputs.

collect uses the project runtime/yfinance; prepare may use any pandas/openpyxl
runtime. Existing completed collections are never overwritten.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,obj):Path(path).write_text(json.dumps(obj,indent=2,default=str)+'\n',encoding='utf-8')

def collect(out, end):
    import requests
    import yfinance as yf
    from portfolio_tools import ASSETS,BENCHMARK
    from data_tools import audit_prices
    out.mkdir(parents=True,exist_ok=False)
    now=datetime.now(timezone.utc).isoformat();symbols=ASSETS+[BENCHMARK]
    raw=yf.download(symbols,start='2020-01-01',end=end,auto_adjust=False,actions=True,progress=False,threads=False,multi_level_index=True)
    if raw.empty or 'Adj Close' not in raw:raise ValueError('No adjusted Yahoo prices returned; no fallback.')
    prices=raw['Adj Close'].reindex(columns=symbols);prices.index.name='Date'
    prices=prices.loc[prices.index<pd.Timestamp(end)]
    audit_prices(prices,'2020-01-01',end)
    prices.to_csv(out/'etf_adjusted.csv',float_format='%.17g')
    raw.to_csv(out/'yahoo_daily_raw.csv',float_format='%.17g')
    actions=[]
    for symbol in symbols:
        for kind in ['Dividends','Stock Splits','Capital Gains']:
            if (kind,symbol) not in raw:continue
            for date,value in raw[(kind,symbol)].dropna().items():
                if value!=0:actions.append(dict(Date=str(date.date()),ETF=symbol,Action=kind,Value=float(value)))
    pd.DataFrame(actions,columns=['Date','ETF','Action','Value']).to_csv(out/'etf_actions.csv',index=False)
    write_json(out/'etf_snapshot.json',dict(source='Yahoo Finance via yfinance',retrieved_at_utc=now,
        requested_start='2020-01-01',requested_end_exclusive=end,price_file='etf_adjusted.csv',price_sha256=sha(out/'etf_adjusted.csv'),
        symbols=symbols,rows=len(prices),first_price=str(prices.index[0].date()),last_price=str(prices.index[-1].date()),
        actions_file='etf_actions.csv',actions_sha256=sha(out/'etf_actions.csv'),
        price_field='Adj Close, auto_adjust=False',vintage_note='Current-vintage research data; never spliced into frozen prices.'))
    urls={
      'sofr.csv':f'https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR&cosd=2019-12-20&coed={end}',
      'ff5_source.zip':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip',
      'gld_historical.xlsx':'https://api.spdrgoldshares.com/api/v1/historical-archive?exchange=NYSE&lang=en&product=gld',
      'treasury_daily.csv':f'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2,DGS10&cosd=2026-09-01&coed={end}',
      'nyse_market_update.html':'https://e.nyse.com/mac-desk-midday-market-update'}
    receipts={}
    for filename,url in urls.items():
        r=requests.get(url,timeout=90);r.raise_for_status();(out/filename).write_bytes(r.content)
        receipts[filename]=dict(url=url,retrieved_at_utc=datetime.now(timezone.utc).isoformat(),sha256=sha(out/filename),bytes=len(r.content))
        print(filename,len(r.content),flush=True)
    write_json(out/'download_receipts.json',receipts)
    print('Downloaded prices through',prices.index[-1].date(),flush=True)


def prepare(out):
    if (out/'refresh_manifest.json').exists():raise FileExistsError('Prepared vintage already frozen; use a new dated directory.')
    from data_tools import load_sofr_cash_returns
    prices=pd.read_csv(out/'etf_adjusted.csv',index_col='Date',parse_dates=True,float_precision='round_trip')
    receipts=json.loads((out/'download_receipts.json').read_text())
    x=pd.read_excel(out/'gld_historical.xlsx',sheet_name='US GLD Historical Archive')
    x['Date']=pd.to_datetime(x['Date'],format='%d-%b-%Y')
    x=x.loc[x.Date.between('2026-07-01',prices.index[-1]),['Date','Ounces of Gold per Share','NAV/Share at 10:30am NYT']]
    x=x.loc[~x['NAV/Share at 10:30am NYT'].eq('US Holiday')].copy()
    x.columns=['Date','Ounces per share','NAV per share']
    for c in x.columns[1:]:x[c]=pd.to_numeric(x[c],errors='raise')
    if x.Date.duplicated().any() or not np.isfinite(x.iloc[:,1:].to_numpy()).all() or (x.iloc[:,1:]<=0).any().any():raise ValueError('Invalid issuer valuation pair.')
    x.to_csv(out/'gld_valuations.csv',index=False,float_format='%.12g')
    with zipfile.ZipFile(out/'ff5_source.zip') as z:
        source=z.read(next(n for n in z.namelist() if n.lower().endswith('.csv'))).decode('utf-8-sig')
    lines=[line.strip() for line in source.splitlines() if re.match(r'^\s*\d{6}\s*,',line)]
    if not lines:raise ValueError('No monthly factor rows.')
    factors=pd.read_csv(io.StringIO('Date,Mkt-RF,SMB,HML,RMW,CMA,RF\n'+'\n'.join(lines)),dtype={'Date':str})
    factors.to_csv(out/'ff5_monthly.csv',index=False)
    write_json(out/'ff5_provenance.json',dict(**receipts['ff5_source.zip'],monthly_file='ff5_monthly.csv',
        monthly_sha256=sha(out/'ff5_monthly.csv'),first_month=factors.Date.iloc[0],last_month=factors.Date.iloc[-1],
        stored_units='percentage points; convert exactly once in notebook',rows=len(factors),vintage_note='Current CIZ vintage; retrospective attribution only.'))
    rates=pd.read_csv(out/'sofr.csv',na_values=['.']);valid=rates.dropna()
    write_json(out/'sofr_provenance.json',dict(**receipts['sofr.csv'],file='sofr.csv',coverage_first=str(valid.iloc[0,0]),coverage_last=str(valid.iloc[-1,0]),
        units='percent per annum; ACT/360 simple accrual',use='Realized financing proxy, not a decision input. Published in arrears.'))
    cash,_=load_sofr_cash_returns(prices.index,out/'sofr_provenance.json');cash.rename('Cash return').to_csv(out/'cash_returns.csv',index_label='Date',float_format='%.17g')
    baseline=json.loads((ROOT/'data/jpm_research_views_20261009.json').read_text())
    baseline['refresh_note']='Valuation inputs refreshed; July 3 forecast, recorded date and allocation policy unchanged. This is not a new JPM forecast.'
    baseline['forecast'].update(valuation_file=(out/'gld_valuations.csv').relative_to(ROOT).as_posix(),valuation_sha256=sha(out/'gld_valuations.csv'),source_workbook_sha256=sha(out/'gld_historical.xlsx'))
    write_json(out/'jpm_research_views.json',baseline)
    old=pd.read_csv(ROOT/'data/etf_adjusted_20261009.csv',index_col='Date',parse_dates=True,float_precision='round_trip')
    shared=old.index.intersection(prices.index);diff=prices.loc[shared]-old.loc[shared]
    audit=pd.DataFrame({'Changed observations':(diff.abs()>1e-12).sum(), 'Maximum absolute level revision':diff.abs().max(),
                        'Maximum relative level revision':(diff/old.loc[shared]).abs().max(),
                        'Maximum daily return revision':(prices.loc[shared].pct_change(fill_method=None)-old.loc[shared].pct_change(fill_method=None)).abs().max()})
    audit.to_csv(out/'price_vintage_comparison.csv')
    gold_old=pd.read_csv(ROOT/'data/gld_valuation_20261009.csv',index_col='Date',parse_dates=True)
    gold=x.set_index('Date');gold_prefix=gold.reindex(gold_old.index)
    old_cash,_=load_sofr_cash_returns(old.index)
    strict=dict(price_prefix_unchanged=bool(np.allclose(prices.loc[old.index],old,rtol=1e-13,atol=1e-13)),
                gold_prefix_unchanged=bool(np.allclose(gold_prefix,gold_old,rtol=1e-13,atol=1e-13)),
                cash_prefix_unchanged=bool(np.allclose(cash.loc[old_cash.index],old_cash,rtol=1e-13,atol=1e-13)))
    common=min(prices.index[-1],gold.index[-1]);daily=pd.read_csv(out/'treasury_daily.csv',na_values=['.']).dropna()
    write_json(out/'refresh_manifest.json',dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),last_price=str(prices.index[-1].date()),
        last_gold_valuation=str(gold.index[-1].date()),last_sofr=str(valid.iloc[-1,0]),last_factor_month=factors.Date.iloc[-1],
        last_daily_treasury=str(daily.iloc[-1,0]),common_portfolio_end=str(common.date()),**strict,
        files={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.suffix in {'.csv','.json','.zip','.xlsx'}},
        evidence='Refreshed historical reconstruction. Not a contemporaneously recorded paper trade.'))
    print(json.dumps(json.loads((out/'refresh_manifest.json').read_text()),indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['collect','prepare']);p.add_argument('--directory',required=True);p.add_argument('--end')
    args=p.parse_args();out=Path(args.directory).resolve()
    if not out.is_relative_to(ROOT/'data') or out==ROOT/'data':raise ValueError('Use a new subdirectory below data.')
    if args.phase=='collect':
        if not args.end:p.error('collect requires an explicit --end exclusive completed-session date.')
        collect(out,args.end)
    else:prepare(out)

if __name__=='__main__':main()
