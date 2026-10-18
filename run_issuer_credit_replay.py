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
from research.credit_funding.issuer_comparison import STUDY_DATA

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
    append_comparison(nb)
    append_early_warning(nb)
    return nb


def append_comparison(nb):
    """Declare and execute the new comparison after the retained single case."""
    def md(s): nb.cells.append(nbformat.v4.new_markdown_cell(s))
    def code(s): nb.cells.append(nbformat.v4.new_code_cell(s))
    digest=hashlib.sha256((ROOT/STUDY_DATA/'manifest.json').read_bytes()).hexdigest()
    md('''## Cross-issuer test — amendment declared 18 October 2026

**Question:** does the unchanged warning rule give useful earlier warnings in other funding-dependent infrastructure companies? The declared convenience sample is Applied Digital (APLD), IREN, Nebius (NBIS) and Core Scientific (CORZ), plus Oracle (ORCL) and Equinix (EQIX) as mature infrastructure contrasts. These contrasts are not matched credit peers. APLD and CORZ also have commercial links to CoreWeave, so the observations are not economically independent.

The universe, January 1–October 16 window, 20 prior observations, three persistent observations, 100 bp widening and two distinct bonds from one legal borrower were written to `research/credit_funding/issuer_study_20261018.json` before fetching bond/equity outcomes. Issuer financing structures had already been inspected. Before outcomes, fixed-coupon instruments were selected by maturity then CUSIP, excluding floating-rate notes. This is a retrospective test on current-vintage data, **not a preregistered historical or untouched holdout backtest**. Current instrument searches may omit retired instruments; there is no survivorship-free universe claim.

**Amendments:** add hash-pinned evidence under `data/issuer_study_20261018/`, a separate comparison module, full exchange-session checks, source-linked funding facts, explicit censoring, price-only/base-rate comparisons and a missed-warning audit. The strict parser found five zero-price/missing-yield TRACE rows. A study adapter preserves these raw rows and marks them unavailable, invalidating their windows. It never fills prices. No thresholds or frozen model files changed.

The original portfolio notebooks, credit/funding notebook/model, protocols, journal and CoreWeave snapshot remain unchanged. The earlier review receipt describes the earlier version; this comparison is a separately declared extension.
''')
    code((ROOT/'research/credit_funding/issuer_comparison.py').read_text(encoding='utf-8'))
    code(f'''STUDY_MANIFEST_SHA={digest!r}
study=run_study(ROOT,STUDY_MANIFEST_SHA)
print('Evidence snapshot:',study['manifest']['created_at'])
display(study['coverage'])
display(study['instruments'][['equity_symbol','cusip','issuerName','couponRate','maturityDate','isConvertible']])
print('Equity panel: complete XNYS sessions through',study['prices'].index.max().date())
print('TRACE histories stop on October 15; October 16 bond state is unavailable, not carried forward.')
''')
    md('''### What the bond test can and cannot evaluate

IREN and Nebius instruments retrieved in this search are convertible. Their embedded equity option makes their yield changes unsuitable for this unchanged straight-bond test. Applied Digital has one selected issue at each of three different ComputeCo borrowers. Core Scientific has a Finance I project issue; the selected older parent issue has no observations in this window. Reg S and 144A versions of the same debt are not independent bonds. These four peers remain **NOT EVALUABLE** for the two-bond rule, rather than receiving fabricated no-warning or successful-warning scores. Individual project histories are retained and structurally checked but are not pooled into a parent signal.

Oracle and Equinix each have four selected fixed-rate USD issues with verified legal-issuer identity and source-linked currency evidence. Current metadata does not establish historical security-master availability. Their sample has 175 evaluable equity sessions each; the remaining 24 sessions are unknown. Both are mature contrasts, so even a successful result would not validate the closer peers.
''')
    md('''### Funding evidence and first loaded disclosure events

Each candidate contributes its first loaded financial statement published in 2026. The gap is cash capital investment minus signed operating cash flow over the same reported period. Periods and capex definitions differ, are shown explicitly, and are **not annualized or ranked as comparable gap magnitudes**. For this direction-only test, reported book debt or a disclosed positive debt component can establish debt > 0; those amounts are labelled and are never treated as principal schedules. This is an amendment to the input contract, not an alteration of the retained principal-based case.

Eligibility starts at midnight in New York on the calendar day after publication; the first subsequent observed close is the outcome anchor. Any loss on publication day or anchor day cannot be claimed as predicted by these results. The first loaded disclosure is not the earliest public indication of financing dependence. No stale state is carried forward and no future filing is used to reconstruct earlier cash availability.

Successful financing, customer prepayments, restricted cash and relevant caveats accompany every issuer. A cash investment gap is not evidence that financing failed or that a default is imminent.
''')
    md('''**Timing review added after inspecting the initial outcome tables:** the price-context table shows changes up to the disclosure anchor and earlier daily falls within 20 sessions. It is descriptive context, not another fitted signal or a change to the declared success metric. It prevents an already-underway decline from being described as a newly predicted problem. Short prehistory remains blank. Changes to the anchor include the anchor session; the daily-fall count excludes that session.''')
    code('''display(study['disclosures'])
display(study['disclosure_context'])
display(study['funding_records'][['issuer','period_start','period_end','operating_cash_flow','cash_capex','reported_debt','debt_basis','capex_basis']])
for row in study['funding_records'].to_dict('records'):
    print(row['issuer'], '\\n  Source:',row['source_url'],'\\n  Locator:',row['locator'])
    print('  Funding support:',row['favourable_evidence'],'\\n  Caveat:',row['caveat'])
''')
    md('''### Earlier-warning outcomes, adverse cases and base rates

The fixed loss target is a subsequent closing price at least 10% below the event close within the next 5 or 20 sessions. `minimum_close_pct` measures loss relative to the event close, **not** peak-to-trough maximum drawdown. A path can hit that loss threshold and still finish with a positive return. Final close returns and SPY-relative changes are therefore reported alongside the loss indicator. Full horizons are required; incomplete observations stay censored even if an early loss has already occurred.

The comparisons retain every equity day, a price-only alarm after a daily fall of at least 5%, and, where bonds qualify, eligible nonwarning dates and price-only alarms on the same bond coverage. These are descriptive base rates, not matched causal controls or achieved trading returns. Rolling windows overlap, adjacent price alarms can belong to one episode, and six first-disclosure events are too few for a reliable incremental-predictive claim. No threshold was optimized.
''')
    code('''display(study['events'])
display(study['comparison'].loc[study['comparison'].horizon.eq(20)])
fund20=study['events'].loc[study['events'].arm.eq('first_funding_watch') & study['events'].horizon.eq(20)]
fund5=study['events'].loc[study['events'].arm.eq('first_funding_watch') & study['events'].horizon.eq(5)]
print('First-disclosure watches:',len(fund20),'20-session loss hits:',int(fund20.loss_hit.sum()),'5-session loss hits:',int(fund5.loss_hit.sum()))
print('Watches followed by a positive 20-session close change:',int(fund20.close_return_pct.gt(0).sum()))
near=['APLD','IREN','NBIS','CORZ']
base=study['comparison'].loc[study['comparison'].issuer.isin(near) & study['comparison'].arm.eq('all_equity_days') & study['comparison'].horizon.eq(20)]
print('Near-peer ordinary-date 20-session loss-hit frequency (overlapping descriptive windows):',round(100*base.loss_hits.sum()/base.complete.sum(),2),'%')
print('Two-bond warning onsets in the two evaluable contrasts:',int(study['coverage'].warning_onsets.sum()))
print('Conclusion: financing dependence is visible, but useful incremental early-warning performance is NOT established.')
''')
    md('''The funding watch is followed by a 20-session loss-threshold hit in APLD, IREN, NBIS and ORCL, but not CORZ or EQIX; none hits the threshold within five sessions. APLD and NBIS finish the 20-session window higher despite interim losses. Because ordinary-date losses are already frequent in the volatile near peers, three hits among four near-peer disclosure events do not demonstrate skill. Oracle's subsequent decline is a useful case to retain, not evidence of a general predictive rule.

Neither mature contrast triggers a two-bond warning. There are subsequent 20-session loss windows on otherwise eligible nonwarning dates, so zero bond alarms cannot be presented as successful loss detection. No bond precision estimate exists when there are zero warning events. The closest peers cannot supply a fair two-bond recall estimate with the available instruments.
''')
    code('''display(study['crashes'])
print('Daily falls of at least 10%, grouped without hiding ineligible issuers:')
display(study['crashes'].groupby(['issuer','bond_prior_status']).size().rename('days').to_frame())
import matplotlib.pyplot as plt
fig,axes=plt.subplots(3,2,figsize=(13,10))
for ax,row in zip(axes.flat,study['disclosures'].to_dict('records')):
    symbol=row['issuer'];p=study['prices'][symbol];event=row['event_close']
    (100*p/p.iloc[0]).plot(ax=ax,color='navy',linewidth=1)
    if pd.notna(event):
        ax.axvline(event,color='orange',label='First funding-watch close')
        pos=p.index.get_loc(event);ax.axvspan(event,p.index[min(pos+20,len(p)-1)],color='orange',alpha=.12)
    ax.set_title(symbol);ax.set_ylabel('First close = 100');ax.set_xlabel('')
    ax.legend(fontsize=7)
fig.suptitle('Retrospective funding watches; shading = next 20 observed sessions')
plt.tight_layout();plt.show()
print('Frozen baseline verification:',verify_review_snapshot()['status'])
''')
    md('''### Interpretation and next evidence needed

The daily-crash audit asks whether a qualified bond diagnostic was present **1–20 prior sessions**, excluding the crash day. Missing prior coverage remains unknown. The 31 daily falls of at least 10% occur in the four structurally ineligible peers; the two evaluable contrasts have none. That prevents a meaningful cross-issuer daily-crash sensitivity estimate in this sample. The separate 20-session loss tables retain slower declines as well.

Keep the unchanged rule as a research watch, not an allocation or short-selling trigger. A stronger next study needs historical issuer/borrower mappings, credit spreads with option treatment for convertibles, matched credit/rates controls, dated receipt/correction vintages, and repeated nonoverlapping disclosure events. Freeze a broader issuer and time holdout before calibration. These retrospective results do not justify changing the frozen portfolio weights or backfilling the prospective paper journal.

Reproduce offline with `python run_issuer_credit_replay.py --publish`. Source URLs, request receipts, raw issuer-filtered FINRA responses, selection decisions and evidence hashes are packaged with this study. Whole financial publications and failed acquisition attempts remain local acquisition outputs; structured factual extracts and primary links are included. Results are unchanged by an unavailable live data service because notebook execution uses only the saved snapshot.
''')


def append_early_warning(nb):
    """Broader early-warning study (early_warning_20261018), executed from saved evidence."""
    def md(s): nb.cells.append(nbformat.v4.new_markdown_cell(s))
    def code(s): nb.cells.append(nbformat.v4.new_code_cell(s))
    manifest_sha=hashlib.sha256((ROOT/'data/early_warning_20261018/manifest.json').read_bytes()).hexdigest()
    doc=(ROOT/'research/credit_funding/EARLY_WARNING_20261018.md').read_text(encoding='utf-8')
    intro,closing=doc.split('<!-- notebook-intro-end -->')
    md(intro)
    md("""### Audit of the six-issuer result

The earlier study reported a 10% interim loss within 20 sessions after four of six funding watches. The cell below asks how often that would happen with no information at all, using each issuer's own ordinary-day rate from the same table. The ordinary-day windows overlap, so this is an approximate benchmark, not an exact null.""")
    code("""from itertools import product
c20=study['comparison'].loc[study['comparison'].horizon.eq(20)&study['comparison'].arm.eq('all_equity_days')].set_index('issuer')
rates=(c20.loss_hits/c20.complete).reindex(['APLD','IREN','NBIS','CORZ','ORCL','EQIX'])
display(rates.rename('ordinary-day 20-session loss rate').to_frame())
p_ge4=sum(np.prod([r if h else 1-r for r,h in zip(rates,hits)]) for hits in product([0,1],repeat=6) if sum(hits)>=4)
print(f'Probability of at least 4 of 6 hits from ordinary-day rates alone: {p_ge4:.2f}')
""")
    md("""Other audit findings. The earlier study stays as published; these points qualify how it is read:

- **Selection.** The six issuers were picked after a visible AI-infrastructure sell-off, with their financing structures already inspected. That makes them development evidence, not a test.
- **The funding flag is close to a constant.** All six first disclosures were flagged. A flag that fires for every capital-intensive issuer describes the sector; it cannot time anything.
- **Overlapping windows.** The ordinary-day comparison uses 179 overlapping 20-session windows per issuer, which overstates how much independent evidence there is.
- **Raw yields mix rates and credit.** The 100 bp raw-yield rule responds to Treasury moves as well as issuer credit. The new study adds a G-spread version.
- **No calculation error was found.** Censoring, the next-day eligibility rule and the same-day exclusion behave as documented.
""")
    code(f"""import json
from research.credit_funding import early_warning as ew
EW_MANIFEST_SHA={manifest_sha!r}
ew_inputs=ew.load(ROOT,EW_MANIFEST_SHA)
print('Evidence pinned at',ew_inputs['manifest']['created_at'],'| protocol',ew_inputs['manifest']['protocol_sha256'][:12])
display(pd.DataFrame([dict(issuer=k,status=v['status'],legal_issuer=v.get('legal_issuer'),bonds=len(v['bonds']),
    callable=sum(x=='Y' for x in v.get('callable',{{}}).values()),convertibles_excluded=len(v.get('convertible_cusips',[])))
    for k,v in ew_inputs['selection'].items()]))
print('Equity exclusions:',json.dumps(ew_inputs['quality']['reasons'],indent=1))
""")
    md("""### Development (2022-2023) and holdout (2024 to 16 October 2026)

Both phases are recomputed here from the saved evidence and checked against their dated receipts. The holdout receipt was written once, after the development receipt, and neither phase changed a parameter. Permutation and bootstrap results are read from the receipts because they are slow to recompute.

Without funding data the declared primary sample is empty, so this section uses `common_no_funding`: the identical issuer-sessions on which the price, broad-credit and issuer-credit signals are all evaluable. In development it is almost empty because the ICE high-yield series on FRED starts in October 2023.""")
    code("""cols=['signal','issuer_sessions','alarm_onsets','hits','false_alarms','same_day','in_episode','censored',
      'precision_pct','episodes','warned','recall_pct','median_lead_sessions','false_per_250','persistence_sessions','base_rate_pct']
phase_tables={}
for phase in ['development','holdout']:
    receipt=json.loads((ROOT/f'research/credit_funding/early_warning_{phase}_receipt_20261018.json').read_text(encoding='utf-8'))
    got=ew.run_phase(ew_inputs,phase)
    saved=pd.DataFrame(receipt['results'])
    fresh=got['results'][saved.columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(fresh.astype(float,errors='ignore').round(9),saved.astype(float,errors='ignore').round(9),check_dtype=False)
    phase_tables[phase]=dict(results=got['results'],dependence=pd.DataFrame(receipt['dependence_tests']),
        relative=pd.DataFrame(receipt['relative_results']),executed=receipt['executed_at'])
    print(phase,receipt['period'],'receipt',receipt['executed_at'],'reproduced exactly')
for phase in ['development','holdout']:
    r=phase_tables[phase]['results']
    for sample in ['common_no_funding','own_price']:
        print(f'{phase} | {sample}')
        display(r.loc[r['sample'].eq(sample),cols].round(2))
""")
    md("""**Reading the tables.** A *hit* is an alarm followed by a new stress episode 1 to 20 sessions later. *Same-day* alarms fire on the onset session and *in-episode* alarms fire while a drop is already under way; neither counts as a warning. *Base rate* is the share of ordinary eligible sessions followed by an onset within 20 sessions, so a signal is informative only if its precision clearly beats it.""")
    code("""h=phase_tables['holdout']
dep=h['dependence']
display(dep.loc[dep['sample'].eq('common_no_funding')].dropna(axis=1,how='all'))
print(json.dumps(ew.verdict(h['results'],dep,'common_no_funding'),indent=1,default=str))
rel=h['relative']
print('Secondary target: drawdown relative to SPY')
display(rel.loc[rel['sample'].eq('common_no_funding'),['signal','alarm_onsets','hits','false_alarms','same_day','in_episode','precision_pct','episodes','warned','recall_pct','base_rate_pct']].round(2))
""")
    md("""### How close did issuer spreads come to the rule?

With zero issuer alarms there is nothing to score, so the useful question is whether the rule was nearly reached and when. For each issuer the cell shows the largest holdout widening of the second-widest bond on any day, which is what the two-bond quorum needs to exceed 100 bp. This is descriptive and changes no rule.""")
    code("""_,_,ew_diag=ew.build_panel(ew_inputs)
rows=[]
for s,(d0,d1) in ew_diag.items():
    d=d1[(d1.date>='2024-01-02')&d1.state.ne('UNKNOWN')]
    q=d.groupby('date').minimum_widening_bp.apply(lambda x: x.nlargest(2).iloc[-1] if len(x)>=2 else np.nan) if len(d) else pd.Series(dtype=float)
    rows.append(dict(issuer=s,known_bond_days=len(d),widest_bond_bp=d.minimum_widening_bp.max() if len(d) else np.nan,
        second_bond_bp=q.max() if q.notna().any() else np.nan,date=q.idxmax() if q.notna().any() else None))
near=pd.DataFrame(rows).sort_values('second_bond_bp',ascending=False)
display(near.round(1))
""")
    code("""import matplotlib.pyplot as plt
r=h['results'].loc[h['results']['sample'].eq('common_no_funding')].set_index('signal')
show=['P1','P2','B1','I0','I1']
fig,axes=plt.subplots(1,2,figsize=(13,4.2))
ax=axes[0]
ax.bar(show,r.loc[show,'precision_pct'].fillna(0),color=['#4c72b0','#4c72b0','#dd8452','#55a868','#55a868'])
ax.axhline(r.base_rate_pct.iloc[0],color='k',ls='--',lw=1,label='base rate')
for i,s in enumerate(show):
    v=r.loc[s,'precision_pct']
    ax.text(i,(v if np.isfinite(v) else 0)+0.6,f"{int(r.loc[s,'alarm_onsets'])} alarms",ha='center',fontsize=8)
ax.set_ylabel('Precision (%)');ax.set_title('Holdout: advance-warning precision, identical sessions');ax.legend()
ax=axes[1]
r.loc[show,['hits','false_alarms','same_day','in_episode']].plot(kind='bar',stacked=True,ax=ax,
    color=['#55a868','#c44e52','#8172b2','#ccb974'])
ax.set_title('Holdout: what each signal fired on');ax.set_ylabel('Alarm onsets');ax.set_xlabel('')
plt.tight_layout();plt.show()
""")
    md("""### Funding addendum: SEC filings, scored after the main holdout

Declared at 12:32 UTC after the author authorised an SEC contact header. The rules are unchanged from the 11:10 protocol, and the evaluator module is the same file. Both funding phases are recomputed here and checked against their receipts. `common` is now the declared primary sample: price, broad-credit, issuer-credit and funding signals all evaluable.""")
    code("""from research.credit_funding.early_warning_filings import load_addendum
ledger,usable,add_manifest=load_addendum(ROOT)
print('Filing ledger:',len(ledger),'records |',ledger.status.value_counts().to_dict())
fund_inputs=dict(ew_inputs); fund_inputs['filings']=usable
for phase in ['development','holdout']:
    receipt=json.loads((ROOT/f'research/credit_funding/early_warning_funding_{phase}_receipt_20261018.json').read_text(encoding='utf-8'))
    got=ew.run_phase(fund_inputs,phase)
    saved=pd.DataFrame(receipt['results'])
    pd.testing.assert_frame_equal(got['results'][saved.columns].reset_index(drop=True).astype(float,errors='ignore').round(9),
        saved.astype(float,errors='ignore').round(9),check_dtype=False)
    print(phase,'funding receipt',receipt['executed_at'],'reproduced exactly')
    if phase=='holdout':
        fh=got['results']; fdep=pd.DataFrame(receipt['dependence_tests'])
display(fh.loc[fh['sample'].eq('common'),cols].round(2))
display(fdep.loc[fdep['sample'].eq('common')].dropna(axis=1,how='all'))
print('Funding verdict:',json.dumps(ew.verdict(fh,fdep,'common',issuer_signal='F2'),indent=1,default=str))
print('Issuer-credit verdict on the primary sample:',ew.verdict(fh,fdep,'common')['verdict'])
display(usable.loc[usable.alarm_session.ge('2024-01-02'),['issuer','form','period_end','acceptance_local','alarm_session','ttm_ocf_usd','ttm_capex_usd','unrestricted_cash_usd','debt_usd','F1','F2']].tail(8))
posthoc=json.loads((ROOT/'research/credit_funding/early_warning_funding_posthoc_20261018.json').read_text(encoding='utf-8'))
print(posthoc['label']); print(json.dumps(posthoc['results'],indent=1))
""")
    md(closing)
    code("print('Frozen baseline verification:',verify_review_snapshot()['status'])")


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
    NotebookClient(nb,timeout=1200,kernel_name='portfolio-research',resources={'metadata':{'path':str(ROOT)}}).execute()
    verify_review_snapshot()
    nbformat.write(nb,out/NOTEBOOK)
    html,_=HTMLExporter().from_notebook_node(nb)
    (out/NOTEBOOK.replace('.ipynb','.html')).write_text(html,encoding='utf-8')
    if args.publish: nbformat.write(nb,ROOT/NOTEBOOK)
    receipt=dict(executed_at=datetime.now(timezone.utc).isoformat(),case=case['case_id'],
                 case_sha256=hashlib.sha256(inside(ROOT,args.case).read_bytes()).hexdigest(),
                 comparison_manifest_sha256=hashlib.sha256((ROOT/STUDY_DATA/'manifest.json').read_bytes()).hexdigest(),
                 early_warning_manifest_sha256=hashlib.sha256((ROOT/'data/early_warning_20261018/manifest.json').read_bytes()).hexdigest(),
                 early_warning_funding_manifest_sha256=hashlib.sha256((ROOT/'data/early_warning_20261018/funding_addendum/manifest.json').read_bytes()).hexdigest(),
                 early_warning_module_sha256=hashlib.sha256((ROOT/'research/credit_funding/early_warning.py').read_bytes()).hexdigest(),
                 comparison_module_sha256=hashlib.sha256((ROOT/'research/credit_funding/issuer_comparison.py').read_bytes()).hexdigest(),
                 notebook_sha256=hashlib.sha256((out/NOTEBOOK).read_bytes()).hexdigest(),
                 code_cells=sum(c.cell_type=='code' for c in nb.cells),
                 published=args.publish,status='EXECUTED_WITHOUT_CELL_ERRORS',
                 scope='Retrospective diagnostic; no qualified historical strategy or prospective claim')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2));print(out)


if __name__=='__main__': main()
