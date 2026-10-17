"""Execute the separate credit/funding notebook, preserving frozen artifacts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from review_checks import verify_review_snapshot

ROOT=Path(__file__).resolve().parent


def build_notebook():
    nb=nbformat.v4.new_notebook()
    nb.metadata.kernelspec={'name':'portfolio-research','display_name':'Portfolio research','language':'python'}
    def md(text):nb.cells.append(nbformat.v4.new_markdown_cell(text))
    def code(text):nb.cells.append(nbformat.v4.new_code_cell(text))
    md('''# Credit and funding research extension — 17 October 2026

This is an isolated amendment to the portfolio research repository. Both portfolio notebooks, frozen protocols, source pins and paper journal remain unchanged. It adds a daily disclosure/credit assessment and a separate monthly cash-funding stress engine. All calculation functions are embedded below.

**Evidence:** verified public disclosures, a small current-vintage broad-credit snapshot, and explicitly synthetic software scenarios. Issuer bond history, matched credit peers and a usable monthly company cash forecast are unavailable. No first-warning date, default probability, improved trading return or live permission is claimed. The module is not connected to EMA/VWAP, broker orders or portfolio allocations.

Date-only disclosures enter at the following local midnight as a conservative research convention. This is not evidence of actual historical feed arrival. No June financial statements enter a June decision when publication was later. All monetary calculations below use USD millions.

**Review corrections, 17 October 2026:** select the newest available accounting period before its latest revision; require issuer, sector and broad-credit assessments to share the decision timestamp and correct type; draw eligible facilities in earliest-expiry order with an ID tie-break; separate nominal unused capacity from currently drawable capacity; reject missing facility dates and nonnumeric cash inputs. These repairs are recorded in the source manifest with the preceding artifact hashes. The original rule thresholds and source observations are unchanged. Earliest-expiry draw order is a liquidity convention, not a globally optimal financing policy.
''')
    code('''from pathlib import Path
import json, hashlib
import pandas as pd
import numpy as np
from IPython.display import display
from review_checks import verify_review_snapshot
print(verify_review_snapshot())
manifest=json.loads(Path('data/credit_funding_20261017/manifest.json').read_text(encoding='utf-8'))
for name, expected in manifest['file_sha256'].items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
        raise ValueError('Credit research input/source changed: '+name)
document=json.loads(Path('data/credit_funding_20261017/source_observations.json').read_text(encoding='utf-8'))
spec=json.loads(Path('research/credit_funding/specification.json').read_text(encoding='utf-8'))
ASOF=document['retrieved_at_utc']
print('Research as-of:',ASOF,'| user-facing audit date:',document['source_audit_date_sgt'])
''')
    md('## Calculation implementation\n\nIndependent rules, explicit availability and cash accounting. Thresholds are untuned research assumptions. Missing issuer inputs remain UNKNOWN.')
    code((ROOT/'research/credit_funding/model.py').read_text(encoding='utf-8'))
    md('''## Verified disclosure case: funding dependence and financing access

The June 2026 filing reports historical financing dependence. The August loan announcement also exposes renewal risk. The September convertible financing is favourable evidence of access to capital and is retained separately; it does not establish an October cash balance.

Sources: [June 10-Q](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000366/crwv-20260630.htm), [filing availability](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000366/0001769628-26-000366-index.htm), [August facility](https://investors.coreweave.com/news/news-details/2026/CoreWeave-Closes-2-6-Billion-Loan-Facility-Expanding-Financing-Flexibility-for-AI-Infrastructure/default.aspx), [September financing](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000432/crwv-20260917.htm).
''')
    code('''funding=funding_assessment(document,ASOF,spec['fundamental_max_age_days'])
display(pd.Series(funding).to_frame('Assessment'))
timeline=pd.DataFrame([funding_assessment(document,t,spec['fundamental_max_age_days']) for t in
    ['2026-06-30T20:00:00Z','2026-08-10T20:00:00Z','2026-08-13T20:00:00Z','2026-09-21T20:00:00Z',ASOF]])
display(timeline[['asof_utc','funding_state','historical_investment_gap_usdm','financing_access','renewal_exposure']])
completed=document['financing_events'][1]
print('Net after capped calls, before offering expenses (historical transaction only):',
      completed['net_before_expenses']-completed['capped_call_cost'],'USD million')
print('This is not current cash and is not added to the June balance.')
''')
    md('''## Credit evidence and transmission

[FRED](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) reports a broad high-yield OAS increase from 3.11% to 3.23% between October 9 and 15: 12 basis points. This is not CoreWeave's bond spread. Only five current-vintage observations are retained, insufficient for the declared 20-prior-observation plus 3-observation persistence rule. Their historical release vintages are unqualified; none can enter before this retrieval.

Issuer bonds require stable instrument/peer definitions, comparable OAS units, observation and dissemination timestamps, and stale-print checks. [FINRA TRACE](https://www.finra.org/sites/default/files/TRACE_Overview.pdf) describes distinct end-of-day and historical products; no entitled issuer panel has been obtained here. A reported bond yield is not substituted for an OAS series.
''')
    code('''snapshot=document['broad_credit_snapshot']
# Retain source dates as dates. Do not invent exact OAS observation/release times.
# These five descriptive values are not a qualified point-in-time credit panel.
broad=credit_assessment([],ASOF,kind='broad',history=spec['credit_history_observations'],
    persistence=spec['credit_persistence_observations'],widening_bp=spec['broad_widening_bp'],
    max_age_days=spec['credit_max_age_days'],max_gap_days=spec['credit_max_gap_days'])
issuer=credit_assessment([],ASOF,history=spec['credit_history_observations'],
    persistence=spec['credit_persistence_observations'],widening_bp=spec['issuer_widening_bp'],
    relative_bp=spec['peer_relative_widening_bp'],max_age_days=spec['credit_max_age_days'],max_gap_days=spec['credit_max_gap_days'])
combined=combine_assessments(funding,issuer,broad,sector_min=spec['sector_min_issuers'],
    sector_fraction=spec['sector_stress_fraction'],weak_fraction=spec['broad_equity_weak_fraction'])
display(pd.DataFrame(snapshot['observations']))
display(pd.Series(combined).to_frame('Research state'))
display(pd.Series(document['unavailable']).to_frame('Missing evidence'))
print('Broad credit gate:',broad,'| descriptive snapshot observations:',len(snapshot['observations']))
''')
    md('''## Monthly cash stress engine — synthetic arithmetic scenarios

The following fictional cash pool demonstrates accounting, not a CoreWeave forecast. It uses net operating cash flow after baseline interest and operating leases, mandatory/discretionary capital spending, principal, finance-lease principal and additional receipt shortfalls. Only unhedged floating and refinanced-fixed balances receive incremental rate shocks; unchanged fixed coupons do not reprice.

Only verified committed capacity in the same cash pool can be drawn, and capacity is consumed once. Facilities must cover the whole model month. Monthly timing can hide intra-month deficits. Facility-interest assumptions must be included in supplied OCF or exposure balances. Forecasts must be supplied separately for non-transferable subsidiary pools; no blanket aggregation is allowed. Delayed receipts must include any later recovery explicitly. All scenario assumptions are exposed below.
''')
    code('''months=pd.date_range('2026-11-30',periods=12,freq='ME')
synthetic=pd.DataFrame(0.,index=months,columns=CASH_COLUMNS)
synthetic['operating_cash_flow']=30.
synthetic['mandatory_capex']=35.
synthetic['discretionary_capex']=10.
synthetic['principal_due']=[0,0,30,0,0,30,0,0,30,0,0,30]
synthetic['finance_lease_principal']=2.
synthetic['unhedged_floating_balance']=200.
synthetic['refinanced_fixed_balance']=[0.]*6+[100.]*6
facility=dict(id='fictional_committed_line',cash_pool='FICTIONAL_POOL',capacity=180.,qualified_drawable=True,
    drawable_from='2026-11-01',expires_on='2027-10-31')
scenarios=[FundingScenario('base'),FundingScenario('rates_plus_300bp',floating_rate_shock_bp=300,refinancing_rate_shock_bp=300),
    FundingScenario('no_further_draws',committed_access_fraction=0),FundingScenario('collateral_capacity_halved',collateral_capacity_fraction=.5),
    FundingScenario('defer_discretionary_capex',discretionary_capex_fraction=0),FundingScenario('receipt_delay'),FundingScenario('weaker_renewals')]
paths={}
for scenario in scenarios:
    forecast=synthetic.copy()
    if scenario.name=='receipt_delay':
        forecast.loc[months[:3],'additional_receipt_shortfall']=15.
        forecast.loc[months[3:6],'operating_cash_flow']+=15.
    if scenario.name=='weaker_renewals':forecast.loc[months[6:],'additional_receipt_shortfall']=15.
    paths[scenario.name]=funding_path(forecast,100.,[facility],scenario,cash_pool='FICTIONAL_POOL')
summary=pd.DataFrame([dict(scenario=name,peak_gap=path.attrs['peak_funding_gap'],ending_cash=path.closing_cash.iloc[-1],
    total_draw=path.committed_draw.sum(),incremental_interest=path.incremental_interest.sum()) for name,path in paths.items()]).set_index('scenario')
display(synthetic)
display(pd.DataFrame([s.__dict__ for s in scenarios]))
display(summary)
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(11,5))
for name,path in paths.items():ax.plot(path.index,path.closing_cash,label=name)
ax.axhline(0,color='black',linewidth=1)
ax.set(title='Synthetic cash pool: conditional monthly balances',ylabel='USD million');ax.legend(fontsize=8)
plt.tight_layout();plt.show()
''')
    md('''## Research interpretation and next work

The verified case supports a funding-vulnerability watch and also records successful financing. Active issuer stress, sector stress, broad-market transmission and a forward company funding gap remain unknown with the qualified inputs here. A high funding need does not establish default, and an issuer warning does not establish a bearish SPY signal.

The three-way replay is explicitly **not evaluated**: price-only versus broad-credit-enriched versus issuer-enriched models need matched decision times, historical availability vintages, issuer/peer bond panels and a fixed exposure policy. Report warning lead, false alarms, avoided losses and missed gains after costs on untouched issuer/period holdouts. The known CoreWeave episode can only be a retrospective case study. Adding an HMM before acquiring these inputs would not fill the evidence gap.

These synthetic scenarios validate accounting behaviour only. Neither their cash gaps nor the rule thresholds are CoreWeave forecasts. No strategy, order, shadow process or scheduler is activated.
''')
    code('''results={'asof_utc':ASOF,'funding':funding,'combined':combined,'broad_credit':broad,
    'comparison_status':'NOT_EVALUATED_MISSING_QUALIFIED_HISTORY_AND_EXPOSURE_POLICY',
    'synthetic_scenarios':summary.reset_index().to_dict('records')}
print('Freeze verification after research:',verify_review_snapshot()['status'])
''')
    nbformat.validate(nb)
    return nb


def main():
    verify_review_snapshot()
    preserved={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
        ['portfolio_construction.ipynb','portfolio_construction_amended.ipynb']}
    notebook=build_notebook()
    out=ROOT/'outputs'/datetime.now(timezone.utc).strftime('credit_funding_%Y%m%dT%H%M%S_%fZ')
    out.mkdir(parents=True,exist_ok=False)
    print('Executing isolated credit/funding notebook:',out,flush=True)
    NotebookClient(notebook,timeout=300,startup_timeout=60,kernel_name='portfolio-research',
        resources={'metadata':{'path':str(ROOT)}},allow_errors=False).execute()
    nbformat.write(notebook,out/'credit_funding_research.ipynb')
    html,_=HTMLExporter(template_name='lab',exclude_input=False).from_notebook_node(notebook)
    (out/'credit_funding_report.html').write_text(html,encoding='utf-8')
    for name,digest in preserved.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Existing notebook changed: '+name)
    verify_review_snapshot()
    receipt=dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),preserved_notebooks=preserved,
        executed_cells=sum(c.cell_type=='code' for c in notebook.cells),
        notebook_sha256=hashlib.sha256((out/'credit_funding_research.ipynb').read_bytes()).hexdigest(),
        evidence='Source-qualified retrospective diagnostics and synthetic cash scenarios only; trading comparison not evaluated.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('SUCCESS:',out,flush=True)


if __name__=='__main__':main()
