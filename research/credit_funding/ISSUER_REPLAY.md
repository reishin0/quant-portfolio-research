# Issuer credit and funding replay

The reusable entry point is `python run_issuer_credit_replay.py`. Its default case is `research/credit_funding/cases/coreweave_20261017.json`. `--case` selects another repository-relative case file. Runs produce a dated notebook, HTML and receipt under `outputs/`. Only `--publish` updates `issuer_credit_funding_research.ipynb` in the root.

## Review amendment — 18 October 2026

The previous CoreWeave-specific notebook, runner, calculation module, downloader and test module were replaced with generic entry points. CoreWeave's source data, original replay specification and previous validation receipt remain dated case evidence. The earlier receipt's filenames and hashes describe the superseded implementation; the new issuer review receipt identifies the current implementation. No frozen portfolio notebook, earlier credit/funding model/notebook, protocol or journal was modified.

Repairs:

- Removed hard-coded issuer, USD-only calculations, New York-only disclosure timing, fixed equity symbols and copied result paragraphs. Source currency and timezone now come from the case. CoreWeave-specific interpretation lives in its case notes.
- Empty histories and no-warning cases now return stable empty tables or UNKNOWN states instead of crashing.
- Duplicate diagnostic rows cannot manufacture a multi-bond quorum. Mixed issuers, unrecognised states, bad dates, boolean financial values and invalid rule settings are rejected.
- Fiscal year and quarter disclosures sharing a period end are retained separately. Later revisions remain dated events; they are not backdated or silently used as current funding states. The optional principal-table reconciliation rejects ambiguous period matches.
- Manifest hashes, instrument ownership and configured equity symbols are verified before calculation. Missing yields invalidate their windows. The downloader refuses existing destinations and incomplete responses.
- A staged-checkout review exposed Git line-ending changes in supporting text files. Explicit canonical-LF digests in the case allow only those declared text transformations. Code, notebooks and data retain exact byte-hash requirements; other content changes still fail. Both existing local folders retain their original frozen bytes.

The 20-observation history, three-observation persistence, 100 bp threshold and two-bond quorum remain unchanged for the retained case. Tests compare its outputs with the earlier receipt. A fictional second-issuer fixture tests another currency/timezone; this is software verification, not an empirical second-company result.

## Case contract

Use the shipped case JSON as a schema example, replacing all issuer-specific fields and sources. Do not reuse its manifest hash or finance values for another company. Each case has:

| Field | Meaning |
|---|---|
| `case_id`, `issuer`, `issuer_name` | Unique case identifier, equity symbol and display name |
| `bond_issuer_name`, `bonds` | Exact source issuer name and distinct instrument identifiers |
| `units`, `bond_currency` | One currency, e.g. `USD millions` and `USD`; no implicit FX conversion |
| `reporting_timezone` | IANA timezone used for the following-midnight filing convention |
| `evidence_dir`, `evidence_manifest_sha256` | Repository-relative source directory and SHA-256 of its manifest |
| `bond_window` | Inclusive start/end dates of the declared panel |
| `equity_symbols`, `horizons` | Issuer plus optional benchmark symbols; positive observed-row horizons |
| `rules` | History, persistence, widening bp, maximum calendar gap and distinct-bond quorum |
| `case_notes` | Source-specific qualifications and contrary evidence, not calculation code |

The evidence manifest requires `created_at` and `file_sha256` entries for every case input. At minimum:

- `bond_daily.csv`: `cusip`, `tradeDate`, `lastSalePrice`, `lastSaleYield`. One instrument/date; yield in **percent**. Dates are daily labels, not delivery timestamps. Missing numeric values remain missing. The current adapter uses TRACE field names; another provider needs an explicit provenance-labelled transformation.
- `instruments.json`: distinct `cusip` and exact `issuerName` at minimum. Retain coupon, maturity, currency, seniority, callable/convertible terms and source dates when available. Identity matching alone does not establish economic comparability or point-in-time eligibility.
- `equity_adjusted.csv`: daily date index and configured symbol columns. Finite positive adjusted prices; no missing prices or duplicate dates. Horizons count observed rows. Acquire and separately audit the correct exchange-session calendar before interpreting them as trading-session horizons.
- `funding_disclosures.json`: `records` containing issuer, units, period start/end/label, filing date, HTTPS source URL, positive cash capex outflow, operating cash flow and debt principal. Positive debt and capex above OCF produce a financing-dependence event. Include favourable financing evidence, restrictions and provenance. An optional `principal_schedules` list uses period ends, buckets and case units; ambiguous revisions require a more specific source contract before reconciliation.

Pin every input's exact bytes and then pin the manifest in the case JSON. A changed data vintage or rule needs a new case/declaration. The legacy CoreWeave manifest also binds `prior_spec_path` and 98 preserved project files; these checks remain enforced. No case file executes arbitrary Python.

`preserved_text_lf_sha256` is an optional explicit map for Git-normalized supporting text (`.md`, `.txt`, `.bat`, `.command` and `.gitattributes`). It tolerates CRLF/LF differences only when the canonical digest matches. It cannot relax hashes for Python, JSON, notebooks or data. The frozen mathematical protocols are verified separately without normalization.

## Optional public bond acquisition

```powershell
python -m research.credit_funding.fetch_bond_history outputs/new_bond_snapshot --cusips 21873SAB4 21873SAC2 --start 2026-01-01 --end 2026-10-16
```

The identifiers above are the retained example, not defaults. Supply the target issuer's identifiers and dates. This downloads current-vintage TRACE EOD history only; it does not acquire financial disclosures, issuer metadata, OAS or delivery vintages. The directory must not exist. Requests are bounded at 5,000 rows; a larger/truncated response fails without publishing a normalized panel. Retain the raw response and receipt, narrow the requested interval, and explicitly reconcile any later combination. No automatic current-quote splice or synthetic replacement occurs.

## What future validation must establish

This tool helps investigate investment exceeding internal cash generation and changes in quoted borrowing yields. It does not automatically discover or classify companies resembling the historical example. Examine each issuer's own investment commitments, collateral/borrowing-base limits, cash-pool restrictions, customer concentration, renewal exposure and financing access.

The retained case demonstrates the limits: July's warning preceded strong gains and October's warning followed the October 14 fall. Earlier financing dependence was visible, but reliable sell-off timing was not established. All warning episodes and incomplete outcomes stay visible.

Before claiming predictive or portfolio value, obtain historical issuer/peer OAS with delivery/correction vintages, comparable instrument definitions, actual monthly cash/commitment/hedge inputs, a declared exposure and cost policy, and untouched issuer/period holdouts. Compare price-only, broad-credit and issuer-enriched rules on identical coverage. Multiple bonds of one issuer are not sector breadth. Last-sale yields cannot enter the frozen OAS gate; public capacity totals cannot enter the cash engine as unrestricted parent cash.

## Cross-issuer amendment, 18 October 2026

The generic notebook now includes the separately declared six-issuer comparison in
`issuer_study_20261018.json`, using saved evidence in `data/issuer_study_20261018/`.
Run `python run_issuer_credit_replay.py --publish` to execute both the retained
case and the comparison offline. The prior review receipt applies to its recorded
version; see `issuer_comparison_review_20261018.json` for this amendment's checks.

The four nearer peers (APLD, IREN, NBIS, CORZ) cannot meet the unchanged two-bond,
same-legal-borrower rule with the available instruments. ORCL and EQIX are mature
contrasts, not matched credit peers; neither triggered a warning. All six first
loaded 2026 disclosures show financing dependence. Four have an interim 10% loss
within 20 sessions, but none within five; APLD and NBIS finish 20 sessions higher.
These are descriptive cases, not demonstrated incremental warning skill.

The study retains current-vintage FINRA observations, Yahoo adjusted prices,
primary-source financial facts, instrument exclusions, missing-data states and
failed warnings. Five zero-price/missing-yield rows are made unavailable only in
the new adapter; raw observations and the earlier issuer model are unchanged.
No frozen portfolio notebook, input snapshot, protocol or journal was amended.
