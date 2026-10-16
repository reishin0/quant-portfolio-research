"""Execute new methodology beside the unchanged frozen portfolio baseline."""
import argparse
import ast
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from forward_evaluation import verify_protocol
from run_updated_analysis import ROOT,build_updated_notebook,append_research_review


def amendment_cells():
    source=(ROOT/'portfolio_amendments.py').read_text(encoding='utf-8')
    tree=ast.parse(source);lines=source.splitlines(keepends=True)
    # Existing baseline dependencies already live inline in the notebook.
    for node in reversed(tree.body):
        if isinstance(node,ast.ImportFrom) and node.module in {'portfolio_tools','research_extensions','research_diagnostics','jpm_views'}:
            del lines[node.lineno-1:node.end_lineno]
    implementation=''.join(lines)
    comparison='''# Retrospective paired experiment; no journal writes in the notebook.
active_schedule = jpm_study['audit'].index[jpm_study['audit'].Active]
common_risk_study = replay_common_risk(prices, experiment['prior_result']['cash_returns'],
    jpm_source_document['forecast'], jpm_source_document['allocation_policy'], active_schedule)
common_risk_summary = pd.DataFrame({'Cumulative net return': (1+common_risk_study['returns']).prod()-1})
common_risk_summary['Sessions'] = len(common_risk_study['returns'])
print('NEW COMMON-RISK RECONSTRUCTION — both accounts begin in cash before first active date')
display(common_risk_summary)
display(common_risk_study['audit'])
diagnostic_tables['amended_common_risk_returns'] = common_risk_study['returns']
diagnostic_tables['amended_common_risk_audit'] = common_risk_study['audit']
diagnostic_tables['amended_common_risk_summary'] = common_risk_summary
for number, label in enumerate(common_risk_study['targets']):
    diagnostic_tables[f'amended_common_risk_{number}_targets'] = common_risk_study['targets'][label]
    diagnostic_tables[f'amended_common_risk_{number}_trades'] = common_risk_study['ledgers'][label]
'''
    uncertainty='''amended_valuations = load_gold_valuations(jpm_source_document['forecast'])
basis_observations, basis_checks = basis_walkforward(prices, amended_valuations)
forecast_records = json.loads(Path('data/amendments_20261016/forecast_outcomes.json').read_text(encoding='utf-8'))
calibration_status = forecast_calibration(forecast_records, pd.Timestamp.now(tz='UTC'))
print('UNCERTAINTY ADMISSION — daily timing basis is not the full mapping error')
display(pd.Series({'Aligned pairs':len(basis_observations),'Chronological evaluation pairs':len(basis_checks),
    'Diagnostic full-sample basis RMSE':float(np.sqrt((basis_observations**2).mean())),
    'Last prior-only shrunk sigma':float(basis_checks['Shrunk sigma'].iloc[-1]),
    'Observed band coverage':float(basis_checks['Within assumed 95pct band'].mean())}).to_frame('Value'))
display(basis_checks.tail())
display(pd.DataFrame(calibration_status['audit']))
print('Eligible calibration cycles:',calibration_status['eligible_cycles'],
      '| retained forecast sigma:',calibration_status['forecast_sigma'],'|',calibration_status['status'])
diagnostic_tables['amended_basis_observations'] = basis_observations.to_frame()
diagnostic_tables['amended_basis_walkforward'] = basis_checks
diagnostic_tables['amended_forecast_calibration_audit'] = pd.DataFrame(calibration_status['audit'])
'''
    journal='''paper_entries = verify_decision_journal('data/paper_journal_20261016')
print('PAPER JOURNAL — reading only; no orders, execution receipts or completed outcomes')
if paper_entries:
    paper_entry = paper_entries[-1]
    display(pd.Series({k:paper_entry[k] for k in ['decision_id','recorded_at_utc','information_close',
        'execution_close_utc','first_return_close_utc','solver_status','sha256','evidence']}).to_frame('Recorded value'))
    display(pd.DataFrame(paper_entry['targets']).style.format('{:.3%}'))
    display(pd.Series(paper_entry['horizon']).to_frame('Separate horizon rules'))
    diagnostic_tables['amended_paper_targets'] = pd.DataFrame(paper_entry['targets'])
else:
    print('No decision recorded. Use the explicit paper_research.py record command after verifying the protocol.')
print('The original October 9 forward contract remains intact; this amendment is a distinct protocol.')
'''
    return [nbformat.v4.new_markdown_cell('## Implemented remaining improvements — separate October 16 amendment\n\nThe new functions and calculations below preserve all frozen baseline cells. Common risk is tested retrospectively; calibration is gated by completed comparable outcomes; the paper journal is read without creating or changing decisions.',id='amended-methodology-declaration'),
        nbformat.v4.new_code_cell(implementation,id='amended-methodology-implementation'),
        nbformat.v4.new_code_cell(comparison,id='amended-common-risk'),
        nbformat.v4.new_code_cell(uncertainty,id='amended-uncertainty'),
        nbformat.v4.new_code_cell(journal,id='amended-paper-journal')]


def build_amended_notebook():
    nb,amendment=build_updated_notebook(ROOT/'data/refresh_20261016')
    where=next(i for i,c in enumerate(nb.cells) if c.id=='save')
    nb.cells[where:where]=amendment_cells()
    nb.cells.insert(0,nbformat.v4.new_markdown_cell('# Portfolio methodology amendment — 16 October 2026\n\nThis notebook retains the refreshed baseline calculations and adds the remaining feasible improvements in a separate executable section. The final amendment review supersedes earlier statements about work still pending. The original notebook and October 9 forward protocol remain unchanged.',id='amended-title'))
    amendment['additional_methodology']='Common feasible risk, prior-only uncertainty admission, horizon separation and read-only paper journal. Baseline calculation cells unchanged from the earlier dated refresh.'
    amendment['added_source_sha256']=hashlib.sha256((ROOT/'portfolio_amendments.py').read_bytes()).hexdigest()
    nb.metadata['methodology_amendment']=amendment
    nbformat.validate(nb);return nb,amendment


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    nb,amendment=build_amended_notebook()
    out=ROOT/'outputs'/datetime.now(timezone.utc).strftime('amended_report_%Y%m%dT%H%M%S_%fZ');out.mkdir(exist_ok=False)
    (out/'amendment.json').write_text(json.dumps(amendment,indent=2),encoding='utf-8')
    print('Executing 58 code cells; frozen baseline preserved:',out,flush=True)
    NotebookClient(nb,timeout=900,startup_timeout=60,kernel_name='portfolio-research',resources={'metadata':{'path':str(ROOT)}},allow_errors=False).execute()
    append_research_review(nb)
    review=ROOT/'research/AMENDMENTS_IMPLEMENTED_20261016.md'
    nb.cells.append(nbformat.v4.new_markdown_cell(review.read_text(encoding='utf-8'),id='amended-final-interpretation'))
    nb.metadata['methodology_review_sha256']=hashlib.sha256(review.read_bytes()).hexdigest()
    nbformat.write(nb,out/'portfolio_construction_amended.ipynb')
    exporter=HTMLExporter(template_name='lab');exporter.exclude_input=True
    html,_=exporter.from_notebook_node(nb);(out/'portfolio_construction_report.html').write_text(html,encoding='utf-8')
    receipt={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'executed_cells':sum(c.cell_type=='code' for c in nb.cells),
        'executed_code_sha256':hashlib.sha256('\n'.join(c.source for c in nb.cells if c.cell_type=='code').encode()).hexdigest(),
        'baseline_file_sha256':amendment['baseline_file_sha256'],'review_sha256':nb.metadata['methodology_review_sha256'],
        'notebook_sha256':hashlib.sha256((out/'portfolio_construction_amended.ipynb').read_bytes()).hexdigest(),
        'evidence':'Retrospective common-risk and basis results; separately recorded pending paper decision. No completed prospective outcome.'}
    (out/'execution_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    verify_protocol(ROOT/'data/forward_protocol_20261009.json')
    if hashlib.sha256((ROOT/'portfolio_construction.ipynb').read_bytes()).hexdigest()!=amendment['baseline_file_sha256']:raise RuntimeError('Frozen notebook file changed.')
    print('SUCCESS:',out,flush=True)


if __name__=='__main__':main()
