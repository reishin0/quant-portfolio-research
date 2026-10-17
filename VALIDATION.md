# Validation record

## 17 October 2026 — credit/funding review before private publication

- Re-executed all **6 notebook code cells** after correcting financial-period selection, same-decision credit/sector binding and facility draw ordering/capacity reporting. The notebook opening declares the repairs; the source manifest retains preceding artifact hashes.
- **151 tests ran: 150 passed, one optional HMM test skipped.** The credit/funding suite now has **32 passing tests**, including ten review regressions and edge cases. The same 32 tests passed in the second folder's Python environment. Seven of the added cases exposed failures in the pre-review implementation.
- All seven synthetic scenario summary rows are unchanged; the new tests exercise cases absent from those examples. Source observations and the original research specification remain byte-identical. Dependency checks passed.
- Both existing portfolio notebooks, both frozen protocols and all baseline pins remain unchanged. The main notebook and reviewed portfolio notebook still hash to `a1924728765f10d91d7620054e5d2e604e1b3df3f47b872c74fefce41c85d244` and `932308ba0e87e884c655e750e5956ad8bf5e917cbdfdbaa3fb7c1b2cb9604b49` respectively.
- Updated execution and test evidence is in `research/credit_funding/validation_20261017.json`; the earlier execution identity is retained there. This remains retrospective/synthetic research with no completed issuer-credit trading comparison.

## 17 October 2026 — isolated credit and funding research

- All **6 executable cells** in `credit_funding_research.ipynb` passed. The notebook contains the calculation implementation, source audit, explicit amendment declaration, seven synthetic cash scenarios, chart and missing-evidence interpretation.
- **141 tests ran: 140 passed, one optional HMM test skipped.** The 22 new tests cover disclosure timing, future/current-vintage exclusion, issuer separation, stale and duplicate credit observations, peer-relative persistence, index-transmission gating, same-pool facilities, one-time capacity, fixed/floating/refinanced interest, hedge schedules and independently reconciled monthly funding gaps.
- Both existing portfolio notebook files, both frozen protocols, all their pinned inputs/source and the paper journal remain unchanged. `verify_review_snapshot()` and `git diff --check` pass.
- The case is classified as funding vulnerability with recent completed financing. Issuer, sector and broad-market stress remain `UNKNOWN`; the three-way performance comparison is not evaluated because qualified history and an exposure policy are missing. No default prediction, live connection or company cash-flow forecast is claimed.
- Execution hashes and counts are recorded in `research/credit_funding/validation_20261017.json`. The cash chart was visually checked. The extension was synced to the local `portfolio-construction-public` mirror; this does not publish it publicly.

## 16 October 2026 — review before private publication

- All **59 executable cells passed** in the published `portfolio_construction_amended.ipynb`. Its opening declaration describes the review repairs; the new integrity cell runs before calculations.
- **119 tests ran: 118 passed, one optional HMM test skipped.** The six new regression checks cover the retained snapshot, missing/truncated journals, protocol binding, changed policy bytes and unchanged inherited calculations. `pip check` passed.
- All **210 CSV result tables** agree with the preceding amended run within `rtol=1e-10`, `atol=1e-12`. No allocation or parameter changes were introduced by the review.
- The complete frozen baseline, both protocol documents, their pinned code/data/runtime and all four original input hashes verify. The one retained paper decision is unchanged; no completed prospective outcome was added.
- `research/review_validation_20261016.json` records the executed artifact hash and validation counts. The runner writes timestamped local outputs; the root notebook is the reviewed publication copy.
- A clean export of the staged Git tree verified both protocols, all pinned inputs and the journal anchor, and successfully rebuilt the reviewed notebook without ignored raw downloads. Staged `git diff --check` passed with preserved CRLF bytes explicitly recognized.

## 16 October 2026 — implemented methodology extensions

- **All 58 executable cells passed** in `outputs/amended_report_20261016T054920_050400Z/portfolio_construction_amended.ipynb`; the HTML report is alongside it. Calculation exports are in `outputs/snapshot_20261016T055203_083927Z/`. The new notebook includes both implementation and amendment declarations. New common-risk results agree with the independent run; the baseline numeric tables agree with the earlier refreshed notebook.
- **113 tests ran: 112 passed, one optional HMM test skipped.** Thirteen added checks cover analytical common-risk scaling, cash-inclusive turnover, infeasible pairs, future-price independence, independent forecast shrinkage arithmetic, prior-only basis estimation, forecast/outcome availability, calendar horizons, journal tampering/duplicate/backdating rejection, subsequent-outcome accounting, and exact inline-function/baseline-cell parity.
- New retrospective common-risk experiment: **53 sessions**, scenario **5.5597%**, equal weight **5.7420%**; risk matches at all three rebalances within 1e-8. The independent accounting ledger reconciles turnover. Both accounts start in cash before the first active return, so this is a distinct experiment from slicing the older portfolios.
- **75** aligned daily basis observations yield **35** chronological checks after the initial 40. Last prior-only shrunk sigma: **1.3236%**. This daily timing-basis diagnostic does not replace the full forecast-horizon mapping assumption.
- Forecast calibration admission finds **zero eligible comparable completed quarters**: Q3 is an in-quarter forecast with an unverified outcome proxy/calendar; Q4 is unfinished. The 10% forecast and 2% mapping-basis assumptions remain unchanged and uncalibrated.
- Separate paper protocol `research/paper_protocol_20261016.json` pins the new implementation, design and input vintage while retaining the original protocol as a dependency. First local paper decision recorded at **2026-10-16 05:49:05 UTC**, before intended execution **October 16, 20:00 UTC** and first return endpoint **October 19, 20:00 UTC**. Receipt hash: `5808c1f3bcfb7c85202cd42ab552675f6605f3d2c4d9a1bb0d27b80a16cfdc66`. It is a decision receipt only, with no execution or subsequent return observed.
- Both protocols verify; original submission hashes and the full frozen notebook hash remain unchanged. `git diff --check` passes. New execution result and output identities are recorded in the amended notebook's execution receipt.

## 16 October 2026 — current-vintage rerun and isolated macro prototype

- **All 54 calculation cells passed** in the refreshed real-data notebook, with prices and issuer valuations through October 15. Final report directory: `outputs/updated_report_20261016T051447_810132Z/`; calculation exports: `outputs/snapshot_20261016T051554_592198Z/`. The dated portfolio and intraday reviews are embedded as narrative cells after execution; calculation sources/outputs are unchanged by that insertion.
- **100 tests ran: 99 passed, one optional HMM test skipped** in the portfolio environment. The separate seven-test macro suite passed in the existing AutoTrade numerical environment, including the skipped HMM causal-filter test. No AutoTrade strategy or broker code was executed. `pip check` and `git diff --check` pass.
- The entire frozen notebook file and all four original submission files are byte-identical to their pre-refresh identities. Frozen protocol code/input/runtime verification passes. The updated Yahoo history correctly fails the original exact-prefix extension test; gold and cash prefixes remain equal. No accepted frozen forward result is claimed.
- Main evaluation: 700 sessions through October 15. Equal-weight CAGR 23.7540%, Sharpe 1.2583; minimum-variance CAGR 22.3587%, Sharpe 1.4133. Its paired Sharpe difference interval still includes zero.
- JPM reconstruction: 53 sessions, scenario 6.1204%, matched prior 6.2721%, difference -0.1517 percentage points. Forecast, allocation policy and uncertainty assumptions are unchanged.
- Isolated macro replay: four exploratory evaluation dates, 1,403 common eligible minutes and only eight overlapping positive minute labels. The bond proxy adds no true-positive minutes versus the broad guard; the combined HMM filter misses all eight. Every artificial 30-minute trading diagnostic loses after both declared cost assumptions. Full results and limitations are in `research/macro_regime/REVIEW_20261016.md`.
- Native session logs, actual arrival times and measured intraday yields were unavailable; no native latency, realized execution or causal-regime claim is made. No thresholds were tuned after the replay.
- Non-fatal upstream NumPy/calendar deprecation, Windows Jupyter selector and physical-core detection warnings remain documented. They did not produce cell errors or failed tests. Pinned baseline dependencies were not changed to suppress warnings.

## 9 October 2026 — quarterly-average model and frozen forward protocol

This entry supersedes the earlier endpoint/confidence scenario below.

- **90 tests passed**, including independent quarterly-average/error-propagation math, explicit Omega, same-date issuer inputs, future-data independence, trading-cost behavior, turnover-cap/ledger agreement and frozen-history admission.
- **All 54 executable cells passed** in snapshot, synthetic and submission modes. The maintained notebook contains **109 cells, 51 inline calculation functions and 18 PNG charts**, with the executed snapshot saved in place. Notebook/module parity passes.
- The issuer input contains **70 NAV/ounces pairs** from 1 July through 8 October. Two explicitly marked US holidays are excluded. NAV-implied bullion is a proxy, and the provider averaging calendar and forecast-error distribution remain uncalibrated research assumptions.
- Main strict recorded-date results remain unchanged. The separate reconstruction uses a cost-aware mean/variance objective and actual execution-turnover guard; it is not directly the old maximum-Sharpe portfolio with a single parameter changed.
- **3 August–8 October, 48 sessions:** scenario cumulative net return **6.7826%**, cost-aware prior **6.9232%**, difference **-0.1405 percentage points**. Maximum drawdowns: **-1.8498%** and **-1.8308%**. Preserve the negative finding; no calibration was chosen to improve it.
- Fixed GLD overweight returns **6.0362%**, GLD-exposure-matched control **6.1979%**, cash-scaled equal-weight risk control **6.2761%**. Actual GLD matching is exact at the three active rebalances. The cash-only risk control cannot increase leverage and falls short of scenario ex ante volatility; inspect the exported risk gaps before interpreting comparisons.
- The scenario's GLD execution targets are **13.2309%, 13.9058%, 13.1517%**. Latest-close announced GLD target: **12.7515%**. Active-period total one-way turnover is **1.9196%**, versus **0.8866%** for its prior. The 10% per-rebalance limit is checked against an independent replay; initial all-cash deployment is explicitly exempt.
- Five declared error/basis cases show cumulative return differences versus prior from **-0.2981 to approximately 0 percentage points**. No winner selection. At the latest close Q is **79.72% annual arithmetic excess** but Omega is **1.0578 annual-return variance**; a large annualized Q is not strong evidence or a promised return.
- Protocol frozen at **2026-10-09 11:46:11 UTC**, after the last observed price of **8 October**. Source/code/package pins verify. No future evidence is present. Earliest eligible fit/execute/earned-return dates are **12/13/14 October**, conditional on receiving those observations. Generated dates in the forward evaluator's unit test are fixtures only and are not exported as evidence.
- All four original data hashes remain unchanged. `pip check` and `git diff --check` pass. Existing upstream NumPy/calendar and Jupyter Windows-loop warnings are non-fatal; no notebook cell raised an error.
- Snapshot report: `outputs/validation_report_20261009T114727_491930Z/`; research exports: `outputs/snapshot_20261009T114723_660877Z/`.
- Synthetic report: `outputs/validation_report_20261009T114743_989899Z/`.
- Submission report: `outputs/validation_report_20261009T114716_666392Z/`.
- Executed notebook calculation SHA-256: `8e7cd5f3686a68785946e36df8013ba7c18ac0d2232a31616a73a8205c60bf1a`.

The implementation is validated under the declared assumptions. This short retrospective study does not establish forward superiority. The frozen evaluator preserves that distinction rather than treating a replay as new evidence.


## 9 October 2026 — JPM research review and mapped GLD result

- **83 tests passed**. Ten new tests independently check the scalar absolute BL
  posterior, mixed P rows, horizon arithmetic/fees, future-price independence,
  publication and expiry, invalid inputs, matched trading schedules and budget/caps.
  Registered-set publication metadata now reports the actual active source date.
- **53 executable cells passed** in snapshot, synthetic and submission-price modes.
  The maintained notebook saves the snapshot run: **108 cells, 48 inline calculation
  functions, 18 PNG charts**. Synthetic/submission modes explicitly skip the real
  post-July-2026 JPM scenario rather than applying it to unrelated observations.
- Source review covers June 9 gold, July 1 mid-year, July 3 Reuters revision, July 28
  equity, August 7 factors and September 4 investor research. The June/early-July
  USD 6,000 gold figure was superseded by the July 3 Reuters-attributed **USD 4,500
  Q4 average**. The underlying JPM note was unavailable. Later qualitative research
  supplies no numerical ETF spread; public searches are not exhaustive coverage.
- Main strict recorded-date results, weights, return paths and configuration registry
  are byte-identical to the preceding stages 4–7 run. The JPM study is separate and
  explicitly reconstructed from publication dates; its mapping date is 9 October.
- Reconstruction: **3 August–8 October 2026, 48 sessions, three active rebalances**.
  Net cumulative return is **6.8735% versus 6.2761%** for the matched prior, a
  **0.5973 percentage-point** difference. Maximum drawdown is **-1.8254% versus
  -1.8293%**. These are short-period returns, not a validated annual alpha.
- All seven disclosed cases were retained. Their matched-prior cumulative return
  differences range from **+0.0787 to +1.3696 percentage points**. The quarter-start
  case has an extra expiry exit and its own identically timed prior control.
  No confidence, endpoint or basis assumption was chosen by these returns.
- GLD rebalance targets are **25.99%, 2.13%, 35.00%**. The latest-close research
  target is also **35%**, at the cap; other assets are shown in `jpm_latest_weights.csv`.
  This material allocation sensitivity limits any robustness claim. The source
  forecasts a quarterly average: the assumed endpoint and nonsynchronous spot/ETF
  conversion remain model choices, with explicit sensitivity checks.
- All four original data hashes remain unchanged. Notebook/module parity, package
  checks and `git diff --check` passed. The existing upstream calendar/Jupyter
  warnings remain non-fatal in this tested environment.
- Snapshot report: `outputs/validation_report_20261009T090000_872841Z/`;
  research exports: `outputs/snapshot_20261009T085953_109909Z/`.
- Synthetic report: `outputs/validation_report_20261009T090120_483433Z/`.
- Submission-price report: `outputs/validation_report_20261009T090015_161728Z/`.
- Executed notebook code SHA-256:
  `9cb2efc915a70cbc00ca907a7eb0d2f70e9b555cdd630c9407f2074c812a749a`.

The forecast horizon is unfinished. The result establishes implementation behavior,
not that JPM's forecast succeeded or that the reconstructed allocation has reliable
predictive superiority. Latest-close weights are research output, not executed trades.

## 9 October 2026 — stages 4–7 completed locally

- **73 tests passed** (`python -m unittest discover -s tests -q`): dated-view
  availability/supersession/expiry, matched control schedules, development-only
  selection under future-data mutation, an independent Bartlett HAC calculation,
  covariance shrinkage, paired bootstrap repeatability, drawdown duration and the
  explicit BAB cash policy, alongside the existing analytical/accounting checks.
- **51 executable cells passed in each of three offline modes**: updated frozen
  snapshot, synthetic and original submission prices. The maintained notebook saves
  the frozen snapshot: **105 cells, 45 inline calculation functions and 17 PNG charts**.
- Two independent frozen runs produced **110 byte-identical CSV exports** and
  identical higher-moment tensor arrays. This checks the tested Windows Python
  3.13.15 environment; other environments still require validation. The final run
  also records the actual runtime configuration separately from the saved source.
- Development: 500 sessions, 4 January 2022–29 December 2023. The declared
  minimum-variance volatility rule selected **252-session sample covariance** from
  four configurations before evaluating later observations. Every candidate is
  exported. Evaluation: **695 sessions, 2 January 2024–8 October 2026**.
- The 22-row experiment-case register records four window/covariance configurations,
  three caps, nine fixed-target cost scenarios, three confidence levels and three
  bootstrap block lengths. Confidence cases explicitly remain unavailable because
  no numerical view set is enabled; these are not passed empirical view tests.
- Minimum variance: net CAGR **22.09%**, Sharpe **1.39**, maximum drawdown **-10.19%**.
  Equal weight: **24.13%**, **1.28**, **-16.71%** respectively. The minimum-variance
  Sharpe difference is **0.11**, with a 21-session block-bootstrap 95% pointwise
  interval **[-0.67, 0.78]**. No positive Sharpe improvement is established by these
  conditional intervals. BL matches equal weight structurally with the current prior.
- Factor attribution uses **31 months, February 2024–August 2026**. All displayed
  alpha Holm-adjusted HAC p-values are 1.0. Submission-mode strategy attribution is
  explicitly unavailable with fewer than 24 aligned months; synthetic mode omits it.
- The selected BAB path holds cash at **one of 34 evaluation rebalances** because
  a leg beta is ineligible; that event is exported. Estimated beta neutrality does
  not imply zero realized beta. Cash-aware exposure and costs remain explicit.
- All **four original data hashes remain unchanged**. Package lock installation,
  `pip check`, notebook/module parity and `git diff --check` passed. The existing
  non-fatal Windows Jupyter and upstream calendar deprecation warnings remain.
- Frozen report: `outputs/validation_report_20261009T083930_929852Z/`;
  research exports: `outputs/snapshot_20261009T083927_213317Z/`.
- Synthetic report: `outputs/validation_report_20261009T084010_201673Z/`.
- Submission-price report: `outputs/validation_report_20261009T083955_974094Z/`.
- Saved/executed frozen notebook code SHA-256:
  `0506ad25f8ce940631fc59b3a38398f2edc5ee4491c9e5dddfd7d76eb3a8eec5`.

These are retrospective research and software results. The fixed ETF universe,
revised provider vintages, inspected evaluation period, conditional bootstrap and
simplified costs prevent a prospective performance claim or a guaranteed grade.
The dated records below describe earlier configurations, not current defaults.

## 9 October 2026 — stages 1–3 research foundation

- **62 tests passed** (`python -m unittest discover -s tests -q`), including 12 new
  analytical/failure-mode tests. These check closed-form variance/Sharpe/tracking
  optima, BL posterior/uncertainty, the quadratic gradient, monthly Kelly sizing,
  signed holdings/cash/cost accounting, variable-cash Sharpe, solver feasibility,
  execution-close exclusion, missing sessions and input tampering.
- **46 executable cells passed** in all three offline modes: frozen updated prices,
  synthetic and original submission. The maintained notebook retains the updated
  frozen run: **96 total cells, 35 inline calculation functions, 15 PNG outputs**.
- Two independent frozen notebook runs produced **66 byte-identical CSV exports**
  and identical moment-tensor arrays. This establishes repeatability for the tested
  Windows Python 3.13.15 environment, not universal bitwise agreement across platforms.
- Updated prices: **2 January 2020–8 October 2026**, 1,701 dates, nine ETFs;
  **258 corporate-action records**. No missing NYSE sessions/quotes. **32 adjusted
  moves above 10%** were flagged for inspection, not changed or declared errors.
- Realized SOFR covers every evaluated interval. Default evaluation is **4 January
  2022–8 October 2026**; every fit cutoff precedes execution by one session.
  Cash-against-cash Sharpe/Sortino are undefined and intentionally missing.
- Constant-cash replay preserves target histories. In this retrospective run,
  Kelly CAGR is 9.59% with SOFR versus 9.01% with constant cash; BAB is -0.48%
  versus -1.05%. Fully invested long-only wealth is unchanged by cash financing.
  These are sensitivity results, not evidence of statistical superiority.
- No active numerical views; BL maximum Sharpe matches equal weight structurally
  under the equal-weight reverse-optimized prior. It is not independent confirmation.
- Pinned environment installed and `pip check` passed. Reports record all installed
  package versions and executed code hash. Upstream calendar/NumPy deprecation and
  Jupyter Windows event-loop warnings are non-fatal; portability needs separate testing.
- Frozen report: `outputs/validation_report_20261009T080736_888825Z/`;
  research exports: `outputs/snapshot_20261009T080734_232159Z/`.
- Reports are local generated artifacts; saved results are embedded in the notebook.
- The current snapshot notebook rerun passed all 46 code cells; all 62 tests passed.
  The four data files match all four manifest hashes.
- Executed notebook code SHA-256:
  `de1aee2c45e2f5e5a5846e0b17d033d783c73f5739723e8897c3ebdb6ceb90af`.

The original universe is retrospective and providers can revise historical inputs.
The later stages 4–7 record above supersedes this earlier foundation-only status. Passing software checks is not a 100/100 research grade.


## 9 October 2026 — refreshed factors and dated-view eligibility

- **50 tests passed**. New checks reproduce the cleaned factor CSV from the raw
  official ZIP, verify both hashes and percent-to-decimal units, reject undated
  or malformed views, and prove pre-publication targets and returns are unchanged.
- The Yahoo notebook completed **all 44 executable cells**, retaining **15 PNG
  outputs** plus factor regression tables and professional-source assessments.
- Prices: **2 January 2020–8 October 2026**, 1,701 rows and nine symbols.
  Factors: **July 1963–August 2026**, 758 monthly rows.
- Strategy regressions use **55 months, February 2022–August 2026**; loaded-universe
  regressions use **79 months, February 2020–August 2026**. No missing months
  beyond the factor release are filled.
- The current run has zero configured/active numerical views. JPM evidence is
  visible but not automatically translated into unsupported ETF return spreads.
  View history is exported; first activation is null.
- Report: `outputs/validation_report_20261009T025848_176413Z/`; research outputs:
  `outputs/yahoo_20261009T025844_683243Z/` (both local ignored artifacts).

The entries below document prior configurations, not current defaults.

## 9 October 2026 — original inputs inactive; October price update

- **46 tests passed**, including checks that the active notebook configuration
  does not enable the original factor/macro/view inputs and that empty BL views
  leave the prior unchanged. Explicitly supplied views still update the posterior.
- The default `launch.py --check` now ran Yahoo mode. **All 44 executable cells
  completed**, with inactive historical/factor sections printing explicit status.
- The extended-window synthetic run also completed all 44 executable cells;
  its report is separate and does not replace the visible Yahoo results.
- Provider coverage was verified as **2 January 2020–8 October 2026**, with
  **1,701 price rows across the eight allocation ETFs plus SPY**. The requested
  exclusive end was `2026-10-09`; no later dates were inferred.
- The visible notebook now saves this Yahoo run, including **13 PNG chart outputs**.
  Its snapshot metadata states the actual price coverage. The view count is zero
  and the view date is null; old 2024 views are not applied to the updated prices.
- Factor analysis and factor-tilt plots are inactive until a factor file is
  explicitly supplied. Original AUM/inflation/credit illustrations are disabled
  unless historical context is explicitly enabled. Their implementation remains
  visible; no unchanged series has been relabelled as updated.

## 9 October 2026 — calculations and results inside the notebook

- The maintained notebook now has **92 cells, including 44 executable cells**.
  All **32 calculation functions** are visible in 21 implementation cells beside
  their relevant analysis. There are no imports from project calculation modules.
- **44 tests passed**, including AST-level parity checks between every visible
  calculation function and its callable Python counterpart, and a check rejecting
  hidden project-module imports.
- The inline submission run completed all 44 code cells. Its saved notebook now
  retains **16 PNG chart outputs and 36 HTML table outputs**, plus execution counts
  and a dated submission-snapshot record. GitHub readers can inspect the analysis
  without first executing it or opening a separate HTML report.
- The inline synthetic run also completed all 44 code cells; real-data-only
  appendix and factor branches remain explicitly skipped in synthetic mode.
- The frozen inputs and methodology have not changed in this presentation update.
  The supplementary experiments remain after research interpretation. Optional
  network calls remain disabled in the saved submission run.
- Automated reruns execute a separate copy and export a new report; they do not
  overwrite the committed submission display snapshot. Its snapshot metadata is
  removed from rerun copies so it cannot mislabel later synthetic/Yahoo results.

## Earlier 9 October 2026 — restored analyses

- **42 behavioral tests passed**, including 16 new checks for the restored analyses
  and regression cases from the repository review.
- **All 50 notebook cells completed on the actual submission inputs** through
  `launch.py --check`; **all 50 also completed in synthetic mode** through
  `launch.py --check --mode synthetic`. Conditional data sections state when they
  are omitted; a completed notebook does not imply live optional-provider coverage.
- Submission mode exported **50 supplemental tables and 14 diagnostic figures**,
  alongside the main portfolio outputs, ordered moment tensors.
- The rolling-window comparison scored 414 common initial-training dates across
  20 candidate ETFs and selected 30 observations from 30/60/90. No evaluated-period
  returns were used to choose that window.
- Tensor-contracted skewness/kurtosis matched the direct portfolio sample within
  `2e-14` in the submission run. Separate fixtures check known CAPM beta,
  five-factor fitted returns, scalar mean–variance/cash solutions and capped weights.
- Regression cases prove that internal missing quotes cannot silently remove a
  different asset's gain, borrow fees debit cash without changing held share
  counts, and unfavorable Kelly opportunities can remain all cash.
- Kelly 0.50/0.66/1.00 comparisons use the same dated ledger; the configured main
  Kelly series matches its comparison series. Monthly heuristic statistics use 12
  observations/year and are labelled calibration-only.
- The optional market/metadata cell passed a mocked-provider execution test.
  **No live appendix acquisition was performed** in this validation. It requires
  explicit `RUN_NETWORK_CONTEXT=True`, network access and available provider data.
- Factor-fit and Kelly-comparison figures were visually inspected. At this earlier
  stage the source notebook stored no outputs; the presentation update above now
  retains the submission results directly in the notebook.

Environment: the existing Windows Python 3.13.15 project environment; `pip check`
reported no broken requirements. Local Jupyter emitted its existing Windows
selector-thread/transport warnings and completed successfully. macOS/Linux and
other Python versions were not exercised in this update.

The restored diagnostics do not establish prospective investment performance.
BAB and Kelly results supersede their earlier accounting/definition versions;
earlier generated reports have been preserved rather than overwritten.

## Historical validation — 8 October 2026

The records below describe earlier notebook versions and their then-current scope.
They do not override the latest validation above.

## Actual-submission integration

- **26 behavioral tests passed**, including nine new source-data checks.
- **All 24 notebook cells passed on the actual submission inputs**, through `launch.py --check`.
- **All 24 cells passed in explicit synthetic mode**, through `launch.py --check --mode synthetic`.
- Submission prices: 1,166 rows per selected symbol, 1,165 aligned returns,
  504 initial training observations and 661 evaluation observations from
  3 January 2022 through 20 August 2024. Seven methods and 224 rebalance targets.
- Factor attribution: eight series (seven strategies plus SPY), 29 monthly
  observations each, February 2022–June 2024. All 21 ETF regressions use 53
  observations, February 2020–June 2024. Boundary months are excluded.
- Inflation series: 1970–2023. BIS bank-credit series: last value 41.279% of GDP
  for 2023 Q2. Row reordering leaves both macro loaders' selected data unchanged;
  duplicate BIS matches fail explicitly. The resulting macro chart was visually checked.
- Duplicate ETF keys, invalid prices, missing symbols, short factor overlap and
  rank-deficient regressions are rejected. Original unit and look-ahead tests pass.

Environment: Python 3.13.15, pandas 2.3.3, NumPy 2.5.3, SciPy 1.18.1,
openpyxl 3.1.5. `pip check` reported no broken requirements. Windows Jupyter
emitted selector-thread and local-kernel transport warnings but completed.

These checks establish software execution and the stated input contracts. The
August 2024 asset selection and views are retrospective; no prospective investment
performance claim is inferred. The supplied factors stop before the price cache,
and macro release-date histories are unavailable.

## Earlier consolidation checks (before submission import)

## Completed checks

| Check | Result |
| --- | --- |
| Python source and notebook structure | The maintained notebook parsed as JSON; every code cell and maintained Python file compiled successfully |
| Offline behavioral suite | 17 tests passed |
| Deterministic notebook execution | All 22 cells passed; executed notebook, HTML report, charts, tables and metadata were created |
| Supported launcher path | `launch.py --check` completed environment checks, `pip check`, imports, kernel registration and the full report run |
| Live Yahoo integration | All nine symbols downloaded and all seven portfolio methods completed |
| Factor regression fixture | Recovered a known 1.5 market loading, 1.2% annual alpha and R-squared of 1.0 |
| BAB construction fixture | Estimated market beta was zero to numerical precision; gross exposure matched the configured bound |
| Look-ahead test | Changing later prices did not change earlier target weights |
| Cost test | Positive transaction costs reduced terminal wealth for every tested long-only strategy |

The live-price check used 2020-01-01 through 2024-08-23, with the end date exclusive. It downloaded 1,168 complete adjusted-price rows, formed 1,167 aligned return observations, reserved 504 observations before evaluation, and evaluated 663 later observations from 2022-01-03 through 2024-08-22. Seven methods produced 224 portfolio/rebalance records. The final BAB target had estimated beta `6.94e-17` and gross exposure `2.0`; its modeled cumulative short-borrow charge was 2.04% of portfolio value across the evaluation observations before compounding interactions.

External-provider availability and historical revisions can change. A successful integration check does not guarantee that a later Yahoo request will succeed or return identical history.

## Behavioral coverage

- Deterministic synthetic prices and explicit provenance labels.
- Per-symbol returns without cross-asset transitions or implicit gap filling.
- Consistent annual mean, CAGR, volatility, Sharpe and initial-wealth drawdown calculations.
- Black–Litterman covariance, view and solver input validation.
- Feasible long-only constraints and solver convergence checks.
- Expanding-window targets fitted strictly before each rebalance.
- Cash balances, weight drift, signed weights, turnover and transaction costs.
- Daily short-borrow deductions for negative positions.
- Higher-moment weights generated by the higher-moment objective itself.
- Fractional Kelly risky-budget, cap and log-domain checks.
- BAB low/high leg selection, beta neutrality and gross-exposure bound.
- Fama–French schema validation, explicit unit conversion, monthly compounding and OLS diagnostics.
- Timestamped exports that preserve every earlier run.
- Explicit provider errors without automatic synthetic substitution.

## Verified environment

| Component | Version |
| --- | --- |
| Python | 3.12.14 |
| NumPy | 2.5.3 |
| pandas | 2.3.3 |
| SciPy | 1.18.1 |
| Matplotlib | 3.11.2 |
| yfinance | 1.7.0 |
| JupyterLab | 4.6.4 |
| ipykernel | 7.4.0 |
| nbclient | 0.10.4 |
| nbconvert | 7.17.1 |

`requirements.txt` uses compatibility ranges rather than an exact cross-platform lockfile. Each automated report records the versions actually used in `environment.json`.

## Historical limits before submission integration

macOS, Linux and Python 3.11/3.13 were not rerun for the 8 October consolidation. Factor-regression behavior was verified with controlled fixtures; the project does not redistribute the Kenneth French file, so the complete notebook validation correctly skipped live factor attribution when that local file was absent.

These checks establish execution and the stated methodological behavior. They do not establish economic significance, parameter stability, future profitability or institutional execution quality.
