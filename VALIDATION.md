# Validation record

## 9 October 2026 — source reconciliation and restored analyses

- **42 behavioral tests passed**, including 16 new checks for the restored analyses
  and regression cases from the repository review.
- **All 50 notebook cells completed on the actual submission inputs** through
  `launch.py --check`; **all 50 also completed in synthetic mode** through
  `launch.py --check --mode synthetic`. Conditional data sections state when they
  are omitted; a completed notebook does not imply live optional-provider coverage.
- Every one of the supplied 213-cell notebook's **127 code cells** has a source
  hash, destination cell IDs and a review decision. All destinations exist.
  The original submission manifest's seven hashes remain valid.
- Submission mode exported **50 supplemental tables and 14 diagnostic figures**,
  alongside the main portfolio outputs, source reconciliation and ordered moment tensors.
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
- Factor-fit and Kelly-comparison figures were visually inspected. The source
  notebook is stored with execution counts and outputs cleared; generated reports
  remain separate timestamped local artifacts.

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
- All seven imported artifacts match the manifest. All 127 archived code cells
  match the actual submitted notebook's code. Data, PDF and helper bytes are
  unchanged; archive notebook transformations are declared in the manifest.
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
| Python source and notebook structure | Both notebooks parsed as JSON; every code cell and maintained Python file compiled successfully |
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
