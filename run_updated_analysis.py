"""Run the maintained notebook against a new immutable input vintage.

The baseline notebook, its code and the forward protocol are never edited.
The generated notebook discloses its source/path overrides and evidence class.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from forward_evaluation import verify_protocol

ROOT=Path(__file__).resolve().parent


def build_updated_notebook(input_dir):
    inputs=Path(input_dir).resolve();manifest=json.loads((inputs/'refresh_manifest.json').read_text())
    optional_raw={'gld_historical.xlsx','ff5_source.zip','yahoo_daily_raw.csv'}
    absent_raw=[]
    for name,digest in manifest['files'].items():
        if name in optional_raw and not (inputs/name).exists():
            absent_raw.append(name);continue
        if hashlib.sha256((inputs/name).read_bytes()).hexdigest()!=digest:raise ValueError(f'Refresh input changed: {name}')
    baseline=verify_protocol(ROOT/'data/forward_protocol_20261009.json')
    nb=nbformat.read(ROOT/'portfolio_construction.ipynb',as_version=4)
    original_hash=hashlib.sha256((ROOT/'portfolio_construction.ipynb').read_bytes()).hexdigest()
    rel=inputs.relative_to(ROOT).as_posix()
    mapping={'data/etf_snapshot_20261009.json':f'{rel}/etf_snapshot.json',
             'data/etf_actions_20261009.csv':f'{rel}/etf_actions.csv',
             'data/sofr_provenance_20261009.json':f'{rel}/sofr_provenance.json',
             'data/F-F_Research_Data_5_Factors_2x3_monthly_20261009.csv':f'{rel}/ff5_monthly.csv',
             'data/ff5_provenance_20261009.json':f'{rel}/ff5_provenance.json',
             'data/jpm_research_views_20261009.json':f'{rel}/jpm_research_views.json'}
    from datetime import date,timedelta
    end=(date.fromisoformat(manifest['common_portfolio_end'])+timedelta(days=1)).isoformat()
    for c in nb.cells:
        if c.cell_type=='code':
            for old,new in mapping.items():c.source=c.source.replace(old,new)
            if c.id=='configuration':
                c.source=re.sub(r'^END_DATE\s*=.*$',f'END_DATE = "{end}"  # Exclusive common-data end for this dated refresh.',c.source,flags=re.M)
                c.source=c.source.replace('# Through August 2026.',f'# Latest downloaded month: {manifest["last_factor_month"]}.')
            if c.id=='price-return-implementation':c.source=c.source.replace('FROZEN YAHOO SNAPSHOT - adjusted ETF prices retrieved 9 October 2026','DATED REFRESH - adjusted ETF prices retrieved 16 October 2026')
            if c.id=='factor-analysis':c.source=c.source.replace('factor_path.name == "F-F_Research_Data_5_Factors_2x3_monthly_20261009.csv"','factor_path.name == "ff5_monthly.csv"')
            c.outputs=[];c.execution_count=None
    nb.metadata.pop('executed_snapshot',None)
    amendment={'baseline_file_sha256':original_hash,'baseline_code_sha256':baseline['notebook_code_sha256'],
               'path_overrides':mapping,'end_exclusive':end,'data_manifest':manifest,
               'absent_optional_raw_sources':absent_raw,
               'classification':'Updated current-vintage historical reconstruction; not the frozen forward experiment.',
               'algorithm_changes':'None. Input paths, end date and descriptive vintage label only. No parameter retuning or forecast replacement.'}
    nb.metadata['dated_refresh']=amendment
    nb.cells.insert(0,nbformat.v4.new_markdown_cell('''# Dated research refresh — 16 October 2026

This is an executed derivative of the maintained notebook. The frozen baseline and its protocol remain unchanged. **Prices and issuer valuations now end on '''+manifest['common_portfolio_end']+'''**. Latest factors end in '''+manifest['last_factor_month']+''', SOFR in '''+manifest['last_sofr']+''', and daily Treasury observations in '''+manifest['last_daily_treasury']+'''. Data dates differ because publication schedules differ.

Historical Yahoo values differ from the frozen file, so this run is a **current-vintage reconstruction**, not accepted evidence under the original exact-prefix forward contract. The July gold forecast and its uncertainty assumptions are held fixed to isolate the data update. Earlier dated methodological commentary below describes the frozen study; this header and the actual tables govern current coverage.

The attached intraday macro investigation is a separate research prototype. Its bond ETF proxies are not Treasury yields, and monthly portfolio expectations are not intraday signals. See `research/macro_regime/REVIEW_20261016.md` for the five-improvement reassessment and source audit.
''',id='dated-refresh-declaration'))
    nbformat.validate(nb);return nb,amendment


def append_research_review(nb):
    """Embed the dated interpretation so the executed notebook is self-contained.

    These are declared narrative amendments; calculation cells are unchanged.
    """
    sources={}
    for filename,cell_id in [('research/REFRESH_20261016.md','dated-refresh-results'),
                             ('research/macro_regime/REVIEW_20261016.md','intraday-investigation-results')]:
        path=ROOT/filename
        sources[filename]=hashlib.sha256(path.read_bytes()).hexdigest()
        nb.cells=[c for c in nb.cells if c.id!=cell_id]
        nb.cells.append(nbformat.v4.new_markdown_cell(path.read_text(encoding='utf-8'),id=cell_id))
    nb.metadata['dated_review_sha256']=sources
    nbformat.validate(nb)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',default='data/refresh_20261016');args=p.parse_args()
    nb,amendment=build_updated_notebook(args.inputs)
    output=ROOT/'outputs'/datetime.now(timezone.utc).strftime('updated_report_%Y%m%dT%H%M%S_%fZ');output.mkdir(parents=True,exist_ok=False)
    (output/'amendment.json').write_text(json.dumps(amendment,indent=2),encoding='utf8')
    print('Executing updated notebook; frozen baseline preserved.',flush=True)
    NotebookClient(nb,timeout=900,startup_timeout=60,kernel_name='portfolio-research',resources={'metadata':{'path':str(ROOT)}},allow_errors=False).execute()
    append_research_review(nb)
    nbformat.write(nb,output/'portfolio_construction_updated.ipynb')
    exporter=HTMLExporter(template_name='lab');exporter.exclude_input=True
    body,_=exporter.from_notebook_node(nb);(output/'portfolio_construction_report.html').write_text(body,encoding='utf8')
    code_hash=hashlib.sha256('\n'.join(c.source for c in nb.cells if c.cell_type=='code').encode()).hexdigest()
    # The existing save cell records the baseline disk source. Make the executed
    # derivative identity explicit alongside it rather than silently replacing it.
    from importlib.metadata import distributions
    receipt={'executed_code_sha256':code_hash,'baseline_code_sha256':amendment['baseline_code_sha256'],
             'completed_at_utc':datetime.now(timezone.utc).isoformat(),'code_cells_passed':sum(c.cell_type=='code' for c in nb.cells),
             'packages':{d.metadata['Name']:d.version for d in distributions()},'evidence':amendment['classification']}
    (output/'execution_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    verify_protocol(ROOT/'data/forward_protocol_20261009.json')
    print('SUCCESS:',output,flush=True)

if __name__=='__main__':main()
