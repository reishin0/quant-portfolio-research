"""Execute an offline issuer case; use --publish to update the generic notebook."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from review_checks import verify_review_snapshot
from research.credit_funding.issuer_replay import inside, load_case

ROOT = Path(__file__).resolve().parent
DEFAULT_CASE = 'research/credit_funding/cases/coreweave_20261017.json'
NOTEBOOK = 'issuer_credit_funding_research.ipynb'


def build_notebook(case_path=DEFAULT_CASE):
    case, *_ = load_case(ROOT, case_path)
    case_sha = hashlib.sha256(inside(ROOT,case_path).read_bytes()).hexdigest()
    nb = nbformat.v4.new_notebook()
    nb.metadata.kernelspec = dict(name='portfolio-research',display_name='Portfolio research',language='python')
    def md(s): nb.cells.append(nbformat.v4.new_markdown_cell(s))
    def code(s): nb.cells.append(nbformat.v4.new_code_cell(s))
    md('''# Issuer credit and funding research

**Amendment declared 18 October 2026:** generalize the previous issuer-specific replay into a reusable, case-configured diagnostic. The issuer, bond identifiers, equity symbols, monetary units, disclosure timezone, data snapshot, quorum and horizons now come from a separate case file. CoreWeave is the retained historical case, not a hard-coded model or a classifier for future companies. The frozen portfolio notebooks, earlier credit/funding notebook/model, protocols and paper journal remain unchanged.

**Review fixes:** reject duplicate bonds, mixed issuers, invalid diagnostic states, boolean prices/yields, bad dates and invalid rule settings; handle empty panels and no-warning cases; retain different fiscal periods and dated revisions; verify bond ownership and all evidence hashes. Results and chart labels are computed from the selected case instead of copied historical conclusions. A staged-checkout check found Git line-ending differences in supporting text; explicitly declared canonical-LF digests permit those text-only differences. Frozen code, data and notebooks still require exact bytes, and both existing local copies remain byte-unchanged.

Use this framework to investigate capital-intensive issuers whose investments depend on continuing debt/equity funding, collateral-backed borrowing or concentrated contract receipts. A company is not classified as vulnerable merely because it resembles the example. Inspect its own dated evidence, cash restrictions, funding access and contrary evidence.

**Evidence boundary:** current-vintage last-sale yields are not option-adjusted spreads. They can reflect rates, optionality, liquidity and trade composition. Trade dates are not verified historical delivery times. Multiple bonds of one issuer are not independent issuers or matched credit peers. This notebook cannot establish default probability, actionable sell timing or trading advantage. The original qualified OAS gate stays separate.
''')
    md(f"Selected case: **{case['issuer_name']}** (`{case['case_id']}`). Configuration: `{case_path}`. The generic calculations below contain no issuer-specific symbols or conclusions.")
    code((ROOT/'research/credit_funding/issuer_replay.py').read_text(encoding='utf-8'))
    code(f'''from IPython.display import display
from review_checks import verify_review_snapshot
ROOT=Path.cwd()
CASE_PATH={case_path!r}
EXPECTED_CASE_SHA={case_sha!r}
if hashlib.sha256(inside(ROOT,CASE_PATH).read_bytes()).hexdigest()!=EXPECTED_CASE_SHA:
    raise ValueError('Case configuration changed; generate a newly declared run')
case,spec,manifest,instruments,bonds,equity,funding=load_case(ROOT,CASE_PATH)
print(verify_review_snapshot())
display(pd.Series(spec).to_frame('Declared rule'))
display(instruments)
display(pd.Series({{'case':case['case_id'],'bond_rows':len(bonds),'missing_yields':int(bonds.lastSaleYield.isna().sum()),
    'bond_history_through':bonds.tradeDate.max() if len(bonds) else None,
    'equity_history_through':str(equity.index.max().date()) if len(equity) else None,
    'evidence_created_at':manifest.get('created_at'),'monetary_units':case['units']}}).to_frame('Coverage'))
for note in case.get('case_notes',[]): print(note)
''')
    md('''## Dated funding disclosures

The financing-dependence condition requires cash capital spending above operating cash flow and positive debt principal. It is a direction-only research watch, not a cash-runway estimate. Units must match the case; no currency conversion occurs. Annual, quarterly and cumulative periods remain separate and are never summed or compared as equal-duration rates.

Date-only filings enter at the following midnight in the case's reporting timezone. This is a conservative public-information convention, not measured feed arrival. The table is an event ledger: it does not carry stale financial states forward or let a later restatement overwrite an earlier decision. The first displayed event means earliest loaded disclosure, not earliest possible public warning. Each row retains its primary source URL.
''')
    code('''funding_results=funding_timeline(funding['records'],issuer=case['issuer'],units=case['units'],reporting_timezone=case['reporting_timezone'])
display(funding_results)
display(pd.DataFrame(funding['records']))
schedules=funding.get('principal_schedules',funding.get('principal_schedules_usdm',[]))
if 'principal_schedules_usdm' in funding and case['units']!='USD millions':
    raise ValueError('Legacy USD schedule cannot be used in another currency')
for schedule in schedules:
    matches=[r for r in funding['records'] if r['period_end']==schedule['period_end']]
    # Multiple revisions/periods need an explicit disclosure identifier, not an arbitrary match.
    if len(matches)!=1 or not np.isclose(sum(schedule['buckets'].values()),matches[0]['debt_principal'],rtol=0,atol=1e-6):
        raise ValueError('Ambiguous or unreconciled principal schedule')
    if schedule.get('units',case['units'])!=case['units']: raise ValueError('Schedule units differ')
if schedules: display(pd.DataFrame([dict(period_end=s['period_end'],**s['buckets']) for s in schedules]))
if funding.get('facilities'): display(pd.DataFrame(funding['facilities']).T)
for note in funding.get('favourable_evidence',[]): print(note)
''')
    md('''## Yield change and all diagnostic episodes

For each instrument independently, compare the recent persistence window with the median of the preceding history window. Every recent yield must widen by the declared basis-point threshold. Percent yields are multiplied by 100 to obtain basis points. A window with missing prices/yields or an excessive calendar gap is UNKNOWN. No forward fill or replacement instrument is used.

An issuer flag requires the declared number of distinct bonds on the same date. Dates with insufficient eligible bonds remain UNKNOWN. A flag following a missing/no-quorum date is an onset or resumption, not necessarily an independent episode. A cleared change-based flag does not prove that absolute funding costs are safe. Rules are illustrative and uncalibrated; changing them after observing losses requires a new experiment and untouched holdout data.

The retained case uses [public FINRA TRACE](https://www.finra.org/finra-data/fixed-income/corp-and-agency/trade). The optional generic downloader uses explicit CUSIPs and dates and writes to a new destination. Provider fields and their acquisition receipts stay with each snapshot. Current metadata must not be spliced into historical EOD series.
''')
    code('''diagnostics=bond_diagnostics(bonds,spec)
timeline=issuer_timeline(diagnostics,equity.index,spec)
context=equity_context(timeline,equity,horizons=case['horizons'])
display(diagnostics.groupby('cusip').agg(first_date=('date','min'),last_date=('date','max'),observations=('date','size')))
display(timeline.loc[timeline.onset_or_resumption])
display(context)
display(timeline.state.value_counts().rename('sessions').to_frame())
if len(diagnostics): display(diagnostics.loc[diagnostics.date==diagnostics.date.max()])
''')
    md('''## Equity context and computed results

All onsets are retained, including warnings followed by rising prices. Returns are close changes over the configured number of **observed rows** of the equity panel, not a promise of complete exchange-session coverage. Incomplete horizons remain blank. These are descriptive outcomes, not achieved strategy returns: there is no verified signal arrival, executable entry, cost assumption or exposure policy. Equity benchmarks provide market context, not credit-peer controls.
''')
    code('''watch=funding_results.loc[funding_results.state=='FUNDING_VULNERABILITY']
print('Issuer:',case['issuer_name'])
print('Earliest loaded funding-watch disclosure:',watch.eligible_at.iloc[0] if len(watch) else 'None in loaded disclosures')
events=timeline.loc[timeline.onset_or_resumption,'date']
print('Diagnostic onsets/resumptions:',[str(x.date()) for x in events])
for row in context.to_dict('records'):
    print('Event:',str(row['date'].date()))
    for h in case['horizons']:
        value=row[f"{case['issuer']}_{h}_sessions_pct"]
        print(f"  Issuer change over {h} observed sessions: {value:+.2f}%" if pd.notna(value) else f"  {h}-session outcome: incomplete")
print('No reliable advance-warning or cross-issuer generalization claim follows from this one selected case.')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True)
for cusip,g in diagnostics.groupby('cusip'):
    axes[0].plot(g.date,g.yield_pct,label=cusip,linewidth=1)
axes[0].set_ylabel('Last-sale yield (%)')
if len(diagnostics): axes[0].legend(ncol=2)
if len(equity): (100*equity/equity.iloc[0]).plot(ax=axes[1])
axes[1].set_ylabel('Adjusted close, first row = 100')
for event in events:
    for ax in axes: ax.axvline(event,color='red',alpha=.25,linewidth=1)
fig.suptitle(case['issuer_name']+' retained case; red = diagnostic onset or resumption')
plt.tight_layout()
plt.show()
''')
    md('''## Applying this to future funding-dependent issuers

1. Create a new case with its own issuer identity, instrument ownership evidence, currency, reporting timezone, equity calendar/panel and hash-pinned source snapshot. The shipped case is an example of the contract, not a prediction template.
2. Collect dated financial disclosures, mandatory investment commitments, debt maturity buckets, facility conditions, cash restrictions and successful financing events. Reconcile periods and preserve evidence against the stress hypothesis.
3. Capture issuer and matched-peer OAS with delivery/correction vintages for the stricter credit test. Last-sale yields alone cannot establish issuer-specific credit deterioration. Match currency, maturity, seniority, credit quality and option treatment.
4. Obtain legally usable cash, drawable capacity, monthly receipts/capex/debt service and actual hedge schedules before running a company cash forecast. Capacity, future hedge requirements and annual buckets are not substitutes.
5. Declare exposure rules, costs, false-alarm measures and issuer/period holdouts before outcomes. Compare price-only, broad-credit and issuer-enriched rules on identical coverage. Keep prospective records separately and include failed cases.

The notebook is a research diagnostic, not an automated issuer screening service. None of these inputs is inferred from company resemblance. Missing information remains unknown; one issuer does not establish sector or index stress. The original cash scenarios, portfolio allocations and paper journal are untouched.
''')
    code('''from research.credit_funding.model import credit_assessment
strict=credit_assessment([],manifest['created_at'])
print('Original qualified issuer OAS gate:',strict)
print('Frozen baseline:',verify_review_snapshot()['status'])
''')
    return nb


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',default=DEFAULT_CASE,help='Repository-relative case JSON')
    parser.add_argument('--publish',action='store_true',help='Update the root generic notebook after a successful run')
    args=parser.parse_args()
    verify_review_snapshot()
    case,*_=load_case(ROOT,args.case)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out=ROOT/'outputs'/('issuer_credit_'+case['case_id']+'_'+stamp);out.mkdir(parents=True)
    nb=build_notebook(args.case)
    NotebookClient(nb,timeout=180,kernel_name='portfolio-research',resources={'metadata':{'path':str(ROOT)}}).execute()
    verify_review_snapshot()
    nbformat.write(nb,out/NOTEBOOK)
    html,_=HTMLExporter().from_notebook_node(nb)
    (out/NOTEBOOK.replace('.ipynb','.html')).write_text(html,encoding='utf-8')
    if args.publish: nbformat.write(nb,ROOT/NOTEBOOK)
    receipt=dict(executed_at=datetime.now(timezone.utc).isoformat(),case=case['case_id'],
                 case_sha256=hashlib.sha256(inside(ROOT,args.case).read_bytes()).hexdigest(),
                 notebook_sha256=hashlib.sha256((out/NOTEBOOK).read_bytes()).hexdigest(),
                 code_cells=sum(c.cell_type=='code' for c in nb.cells),
                 published=args.publish,status='EXECUTED_WITHOUT_CELL_ERRORS',
                 scope='Retrospective diagnostic; no qualified historical strategy or prospective claim')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2));print(out)


if __name__=='__main__': main()
