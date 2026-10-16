"""Bounded data-only acquisition through the existing AutoTrade Yahoo helper.

Does not import a strategy, inspect credentials, connect to MySQL or submit orders.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pandas as pd


def main():
    p=argparse.ArgumentParser();p.add_argument('--helper',required=True);p.add_argument('--output',required=True)
    p.add_argument('--start',default='2026-10-01');p.add_argument('--end',default='2026-10-16');args=p.parse_args()
    helper=Path(args.helper);out=Path(args.output);out.mkdir(parents=True,exist_ok=False);raw=out/'raw';raw.mkdir()
    spec=importlib.util.spec_from_file_location('existing_yahoo_data_helper',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    config=SimpleNamespace(start=dt.date.fromisoformat(args.start),end=dt.date.fromisoformat(args.end))
    if config.start>=config.end or (config.end-config.start).days>28:raise ValueError('Bounded research window required.')
    results={};rows=[]
    for symbol in ['SPY','QQQ','DIA','IEF','SHY']:
        r=module.fetch_symbol(symbol,config,raw);rows.extend(r.pop('rows'));results[symbol]=r
        print(symbol,len([row for row in rows if row['symbol']==symbol]),r['errors'],flush=True)
        if module.STOP.is_set():break
    pd.DataFrame(rows).to_csv(out/'bars.csv',index=False)
    receipt=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),helper=str(helper),helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
        request_start=args.start,end_exclusive=args.end,results=results,
        bar_file_sha256=hashlib.sha256((out/'bars.csv').read_bytes()).hexdigest(),
        evidence='Downloaded retrospective aggregate bars, available at bar end. Bond ETFs are price proxies, not measured yields. No native-tick or live-receipt claim.')
    (out/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
