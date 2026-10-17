# Methodology amendments

## 17 October 2026 — credit/funding review corrections

- Correct disclosure selection to prioritize the newest accounting period, then the latest available same-period revision.
- Bind issuer, sector and broad-credit assessments to the same decision timestamp and assessment type; cached future/stale or unstamped states cannot affect current permissions.
- Draw eligible facilities in deterministic earliest-expiry order. Separate nominal unused commitments from current drawable capacity. Reject absent facility dates, boolean/nonnumeric cash inputs and invalid policy windows.
- Apply all declared credit/breadth parameters in the notebook. Record preceding artifact hashes in the updated extension manifest and disclose repairs in the notebook opening. Original thresholds, source observations, both portfolio notebooks and both frozen protocols remain unchanged.

## 17 October 2026 — isolated credit and funding extension

- Add `research/credit_funding/model.py`, its declared specification, source-checked observations under `data/credit_funding_20261017/`, an executable runner and the separate `credit_funding_research.ipynb`. Both portfolio notebooks, all pinned baseline files and the paper decision are byte-preserved.
- Separate dated funding vulnerability, positive financing events, issuer-relative credit stress and sector/index transmission. Preserve missing-data states; an issuer warning cannot automatically become a SPY signal.
- Add reconciled monthly same-pool cash scenarios, one-time facility capacity consumption, conditional capacity haircuts, receipt/renewal shocks and incremental interest on eligible exposures. Existing fixed coupons do not reprice with secondary-market yields. Avoid subtracting baseline interest or operating leases twice.
- Preserve publication timing. Date-only disclosures use an explicit conservative next-midnight convention; current-vintage broad-credit observations are descriptive only. No exact first-warning time is claimed.
- Record that issuer/peer history and monthly usable company cash schedules are missing. The three-way trading comparison is not evaluated. Seven synthetic scenarios are correctness demonstrations, not company forecasts. The new module has no operational connections.

## 16 October 2026 — review and publication repair

- Publish the executed derivative as `portfolio_construction_amended.ipynb`; preserve the complete frozen baseline bytes and both existing protocols.
- Add `review_checks.py` and `run_reviewed_analysis.py`. Check protocol documents, parent binding, forecast registry, pinned source/data/runtime and original inputs before execution. Require the retained journal head and entry count so deletion cannot be reported as an empty, valid history.
- Preserve hashed Python, JSON, CSV and notebook bytes through Git checkout. Verify the staged tree independently before publishing.
- Declare these software repairs in the notebook's first cell and `research/REVIEW_FIXES_20261016.md`. No allocation, uncertainty or cost parameter changes; no replacement paper decision and no completed prospective outcome.

## 16 October 2026 — remaining feasible improvements implemented

- Add `portfolio_amendments.py`, `paper_research.py` and `run_amended_analysis.py`; the new notebook includes the additional functions inline in four new executable cells, while preserving the 54 refreshed baseline cells.
- Replace the approximate risk comparison in a separately declared experiment with the intersection of two cash-sleeve feasible risk intervals. Apply identical caps, turnover/cash/financing constraints and independently verify accounting. All three sampled rebalances match; expose and hold both if a later pair is infeasible.
- Add an exclusive, hash-chained local paper journal and separate subsequent-outcome evaluator; reject backdating, stale decision prices, future input availability, duplicate IDs and premature outcomes. The first entry is a new all-cash paper pair, not an actual account or historical backfill.
- Separate completed-quarter forecast scoring from strategy inference. A new protocol retains a 60-session minimum and adds eight completed comparable forecast cycles; the current view has only 32 remaining active return sessions.
- Add chronological ETF/NAV timing-basis checks and a comparable-quarter uncertainty gate. The completed Q3 proxy fails comparability/definition gates; Q4 is unfinished. Existing 10%/2% uncertainty assumptions remain in allocations, explicitly uncalibrated.
- New common-risk result: scenario 5.5597%, equal weight 5.7420% over 53 retrospective sessions. No parameter tuning or positive-edge claim. Full declarations and data limits appear in `research/AMENDMENTS_IMPLEMENTED_20261016.md` and in the new executed notebook.

## 16 October 2026 — dated input refresh and isolated macro investigation

- Preserve the frozen notebook, pinned code/inputs/protocol and four original submission inputs. Add a new price/valuation vintage through October 15, lagged-rate/factor coverage audit and exact-prefix revision comparison under `data/refresh_20261016/`.
- Add `refresh_inputs.py` and `run_updated_analysis.py`. The executed derivative changes input paths, the exclusive end date and the descriptive vintage label; allocation mathematics, parameters, forecast and uncertainty assumptions remain fixed. It embeds the dated review and intraday investigation after the existing research sections.
- Reject revised historical Yahoo observations under the original forward contract. Retain the new reconstruction separately; do not splice histories or relax the frozen check.
- Reassess all five improvements, including common-risk mismatch, forecast horizon, decision journaling and uncalibrated uncertainty, in `research/REFRESH_20261016.md`.
- Add a separate bar-level macro prototype with explicit bond-price proxy labels, freshness rejection, prior-only HMM fitting, causal filtering, controls and cost sensitivity. Preserve its negative result; this is not native trade reproduction or an untouched holdout.
- Raw vendor files stay local; derived data and hashes support the research run. No live strategies, shadow settings, launchers, schedules or broker state were changed. No commit or push was performed for this amendment.

## 9 October 2026 — quarterly observations, uncertainty, costs and forward protocol

- Replaced arbitrary quarterly-average endpoint and mismatched July quotes with a conditional quarterly observation model and same-date issuer NAV/ounces pairs.
- Propagate explicit, uncalibrated forecast and basis error into Omega; display effective Bayesian weight and all five error/basis cases.
- Put trading costs inside mean/variance utility, constrain announced active weights, and cap actual execution turnover with a declared initial-entry exception. Report drift beyond target bounds.
- Add fixed GLD, GLD exposure and cash-scaled risk controls, including matching gaps and identical costs/dates.
- Add exclusive protocol freezing and subsequent-data evaluation with code/runtime/input pins, immutable historical rows, calendar validation and decision/execution/return admission.
- This supersedes the endpoint/confidence mapping described in the earlier entry below. All original data files remain unchanged. Forward performance remains unavailable until new observations arrive.


## 9 October 2026 — JPM source revision and absolute-view review

- Audit June–September JPM research and record publication dates, public-source
  limits and retrieved HTML hashes. Detect that the June/July USD 6,000 gold pages
  are superseded by the July 3 Reuters-attributed USD 4,500 Q4 average.
- Add absolute excess-return BL views (`comparator=None`) and independent scalar
  posterior tests. A bullion forecast no longer requires inventing another ETF view.
- Keep strict recorded-date results separate from a publication-date reconstruction.
  Never backdate the 9 October mapping; expose its quarter-average/endpoint, fee,
  timing-basis and confidence assumptions and all seven sensitivity cases.
- Recalculate remaining-horizon arithmetic excess return using only decision-close
  prices, enforce an explicit short-horizon exit, and match control trading dates.
- Fix registered-view publication metadata: active-set publication now appears in
  each rebalance audit instead of the empty legacy fixed-view date field.
- Correct single-series chart sizing; retain all calculations, audit tables and
  results inside the notebook with module parity checks.

## 9 October 2026 — stages 4–7 research experiments

- Introduce a dated, validated view-set register, separating provider statements,
  ETF mapping and confidence assumptions. Publication and mapping-record dates
  precede decisions; newest sets supersede older ones; expiry causes a recorded
  prior-only rebalance. Matched controls use the same schedule and costs.
- Keep JPM records disabled: no justified numerical ETF mapping/confidence is
  supplied. Confidence sensitivity explicitly records unavailable cases.
- Select from four fixed window/covariance configurations using development-only
  minimum-variance volatility. Display all later candidate outcomes on common dates.
- Add an explicit BAB cash policy for ineligible near-zero/nonpositive leg betas,
  recording every affected rebalance. Other failures remain visible errors.
- Add paired circular block-bootstrap CAGR/Sharpe differences at three block lengths;
  intervals are conditional and pointwise, not proof of prospective superiority.
- Add three-lag Bartlett HAC standard errors, alpha intervals and Holm alpha p-values
  alongside IID factor estimates. Require contiguous monthly samples of at least 24.
- Add Ledoit–Wolf covariance fitted per prior window, cap and fixed-target cost grids,
  target exposure/concentration, signed risk contributions, drawdown duration and
  realized BAB beta. Small-window factor-tilt diagnostics explicitly state insufficient data.
- Generate headline tables and sentences from one results object. Export candidate
  paths, case statuses, source/runtime/input hashes and a timestamped specification.

All inspected observations remain retrospective. Numerical-view benefit cannot be
estimated from the current inactive register. No perfect grade or deployment claim
follows from successful software validation. Prior dated entries describe older defaults.


## 9 October 2026 — stages 1–3: research contract, audit and frozen inputs

This entry supersedes earlier descriptions of Yahoo defaults, same-close fitting,
daily Kelly scenarios and constant-only financing. The four original data files remain unchanged.

- State the research question, primary comparisons, strategy objectives, default
  constraints and retrospective/prospective boundary in the notebook.
- Fit through close t-2, execute at close t-1 and earn the return ending t. Dated
  views must precede the fit cutoff. Export both fit and execution timestamps.
- Fit Kelly to completed monthly buy-and-hold scenarios, excluding both boundary
  months, to match monthly target holding. Keep daily mode an explicit alternative.
- Check higher-moment solutions from four deterministic starts for solver success,
  finite objective, budget and caps; export local utility spread, without claiming
  global optimality. Reject non-positive-definite optimizer covariance.
- Add independent analytical tests for variance/Sharpe/tracking optima, BL updates,
  quadratic gradients, Kelly, financing, short positions and execution timing.
- Default to hash-verified updated price/action snapshots, audit NYSE sessions and
  flag large adjusted moves. Preserve all source data and avoid filling gaps.
- Use historical realized SOFR financing for real-data runs; leave the constant
  3% forecast explicit. Add a fixed-target constant-financing sensitivity and
  excess-volatility Sharpe. Undefined cash-against-cash ratios stay missing.
- Pin the tested Windows Python 3.13 environment, export actual versions/code hash,
  and keep all 35 calculation functions inline with module parity tests.

The new cash rate is a current-vintage realized proxy, not an available-at-decision
forecast. Prices, factors and universe selection still prevent a point-in-time claim.
The subsequent stages 4–7 entry above extends this foundation with robustness and uncertainty assessment.

## Earlier amendment history


**Initial amendment:** 6 October 2026

**Professional research consolidation:** 8 October 2026

**Accounting corrections:** 9 October 2026

## 9 October 2026: refreshed factors and enforced view chronology

This update supersedes the inactive-factor default described in the earlier entry.
The new official factor snapshot runs through August 2026. Source ZIP, cleaned
monthly CSV and provenance metadata are saved separately under `data/`. No original
input bytes are changed. Current-vintage revised factors are used only for
retrospective attribution and the explicitly in-sample appendix sensitivity.

**Corrected defect:** the previous implementation recorded `views_as_of` but
applied supplied views at all historical rebalances. Nonempty views now require
a valid publication date and are withheld unless the preceding observed close is
strictly after that date. Tests compare all pre-publication targets and returns
against a no-view run, and check same-close exclusion and subsequent activation.
Final P/Q/Omega diagnostics use the actual eligible views, not the configured list.
Exports distinguish configured and active views and record each rebalance decision.

Professional-source review found that the recently uploaded JPM Drive report is
from June 2020. The current official October 1, 2026 outlook is separately recorded.
It does not directly supply annual return spreads/confidences for the eight ETFs;
its views remain sourced research rather than invented numerical inputs. The
October 1 monthly target is ineligible for an October 1 publication in any case.
Fixed scenarios have no automatic expiry; time-limited forecast activation needs
an explicit validity/review policy. All calculations and source assessments remain
visible in the main notebook, with regenerated factor outputs.

## October 2026 active configuration and original-input declaration

Unchanged original 2024 input settings are now commented in the notebook and
labelled **ORIGINAL 2024 SUBMISSION**. The data bytes remain intact
for provenance. The active notebook and report launcher default to Yahoo with
exclusive end `2026-10-09`; the verified provider history reaches 8 October 2026.

- Original price mode/cutoff, factor-file path, macro-file paths and investor views
  appear as commented references. Historical context is disabled by default.
- The original factor file ends June 2024. `FACTOR_FILE=None` makes its analysis
  and dependent experiments explicitly inactive until an updated file is selected.
- The original 21-August-2024 views are no longer embedded as active BL defaults.
  Empty `INVESTOR_VIEWS` returns the equilibrium prior unchanged; explicit supplied
  views still use the maintained posterior formula. Run metadata records view count
  and the supplied date instead of hard-coding the original date.
- The eight-asset selection is still the original study universe. The cash/cost
  settings remain user assumptions. Neither is represented as refreshed market data.
- Notebook results are regenerated using Yahoo prices; unchanged factors, macro
  snapshots and original views are not silently combined with the newer prices.

The dated entries below describe the earlier restoration and corrections; this
active-input policy supersedes their previous defaults.

**Scope:** maintained professional continuation of the 2024 portfolio study

## What was amended

| Original issue | Amendment in the executable workflow |
| --- | --- |
| Returns crossed ETF boundaries in a long table | Prices remain in a date-by-symbol table. `pct_change(fill_method=None)` runs down each symbol column. Common unavailable endpoints are trimmed; internal gaps are rejected rather than erasing held-period returns. |
| Covariance was treated as correlation | Annualized covariance is used by Black-Litterman and the optimizers. Correlation is calculated and labelled separately for display only. |
| Daily, monthly and annual quantities were mixed | Optimization inputs use annual excess returns and annual covariance. Historical metrics convert daily observations with one documented 252-observation convention. |
| Fama-French percentage points were mixed with decimal ETF returns | The maintained loader requires an explicit `percent` or `decimal` unit, converts once, validates the schema, compounds portfolios to monthly frequency and runs aligned five-factor excess-return regressions. |
| Optimizer names did not always match their objectives | Each named allocation has a matching explicit objective: portfolio variance, Black-Litterman Sharpe, or tracking variance. Solver success, bounds and the full-investment constraint are checked. |
| Higher-moment results used weights from another optimization | A dedicated optimizer now evaluates each candidate portfolio's own annual mean and variance, skewness and excess kurtosis, and returns its own checked weights. |
| Selection and evaluation used the same sample | Numerical fitting uses 504 prior observations and monthly expanding windows. This does not correct the retrospective eight-ETF selection or August 2024 views; the results are explicitly retrospective scenarios. |
| Costs and turnover were absent | Monthly one-way turnover is recorded. The default deducts 10 basis points per unit of one-way turnover, including initial investment, from the walk-forward return stream. |
| Current beta, AUM and risk-free inputs were mixed with historical observations | The maintained workflow uses no live beta or AUM. It uses equal prior weights and one user-stated annual risk-free assumption recorded with each run. BAB betas are estimated within each prior training window. |
| BAB used a full-sample ranking without beta-neutral scaling or costs | Each rebalance estimates betas from prior observations, scales low/high legs to zero estimated market beta, bounds gross exposure and includes transaction and short-borrow costs. |
| Kelly mixed units and exponentiated simple returns | Solve constrained full Kelly with cash available, then scale its risky weights by the fraction. Compound dated simple returns and apply financing and costs consistently. |

## Restored source analyses (9 October 2026)

The initial restoration called calculation functions from project modules and
cleared the saved results. The notebook presentation has now been corrected:
all 32 calculation functions appear directly in 21 implementation cells, placed
alongside the relevant analysis. Saved submission-run tables and charts are retained
for reading on GitHub. No project calculation module is imported by the notebook.
Tests enforce parity with the callable Python counterparts used for testing and reuse.

| Source topic | Restoration and correction |
| --- | --- |
| Asset performance and Sortino | Initial-window table, full-history descriptive wealth/drawdown panels and outlier inspection. Downside deviation includes all observations and uses the period cash rate as the target. |
| Rolling beta/alpha window choice | Compare conditional return residuals for 30/60/90 windows on common initial-training dates. Coefficients exclude the current observation. Realized market returns used for scoring are not claimed as ex-ante forecasts. |
| CAPM and return-vector comparison | Estimate beta against the same SPY or ACWI proxy used for its premium; compare annual excess returns on one prior window. Current provider beta belongs only in the optional appendix. |
| Explicit BL calculations | Expose P, Q, Omega, posterior-mean covariance and predictive covariance. Main strategies retain return covariance; predictive covariance is a labelled sensitivity. |
| Normalizing return estimates into weights; dividing weights by risk aversion | Replace with constrained mean–variance utility at lambda 0.5, 1 and 3.07, with explicit cash. These numerical coefficients are not universal investor classifications. |
| Higher-order tensors | Contract raw third/fourth-order central moments, then standardize by portfolio volatility. Verify against the higher-moment optimizer's own portfolio. Pairwise standardized slices are not substituted for full tensors. |
| Factor scatter plots | Plot observed against fitted excess returns using all five factors. Restore loadings/threshold displays with corrected units. |
| Factor weight multipliers | Preserve +/-10% multipliers as a capped appendix sensitivity, with original numerical and adaptive thresholds explicitly labelled. Calibration metrics use 12 periods/year, not 252. No claim of Fama–MacBeth estimation or predictive performance. |
| Original quartile beta spread | Fix membership on initial-training betas. Keep the uncosted zero-net-investment payoff separate from the main funded, costed beta-neutral BAB portfolio. |
| Kelly fractions | Compare 0.50, 0.66 and 1.00 against the same full-Kelly target at each rebalance using the shared net cash/holdings ledger. |
| Snapshot AUM and cap redistribution | Appendix only: acknowledge one undated repeated snapshot, normalize selected assets and repeatedly enforce all caps. An eight-asset 10% cap is infeasible. |
| Inflation, credit, six indices, gold, Treasury yield and VIX | Move descriptive macro context after research interpretation. Keep local CPI/BIS charts plus standardized credit. Restore optional network acquisition with accurate price/yield labels, provenance and explicit current-vintage metadata. Replace the hard-coded Kavout URL with symbol-specific Yahoo metadata. |

The same update fixes three defects found in the maintained implementation:

- An internal missing price previously removed complete return dates for every
  asset. It now fails explicitly, preserving the need for a valuation policy.
- Borrow charges previously reduced reported NAV without reducing the cash used
  to calculate later weights. They now debit cash and normalize positions against
  net wealth. Rebalance transaction costs retain their declared proportional
  capital deduction before target holdings are established.
- Kelly previously forced a fixed fraction into risky assets. The cash-aware full
  solution can now choose all cash; fractions multiply that solution.

These changes invalidate numerical equivalence to earlier BAB and Kelly outputs.
Previously generated reports remain historical artifacts and are not overwritten.

## Evaluation contract

- The first 504 aligned return observations are training history only.
- The first available observation in each calendar month is the rebalance date.
- Every rebalance uses observations strictly before that date.
- Target weights are held between rebalances and drift with asset returns.
- One-way turnover is half the absolute change across risky assets and cash.
  Initial turnover is 1.0 for a fully invested long-only portfolio and follows
  the same cash-inclusive formula for partial or long/short portfolios.
- Transaction cost is `turnover × basis points / 10,000` and is deducted on the
  rebalance observation.
- SPY is an uncosted reference series, not an investable strategy in this example.

## Integration of the actual submission (8 October 2026)

The four input files are retained with their source hashes in `data/manifest.json`.

| Research input or issue | Maintained implementation |
| --- | --- |
| ETF universe: 21 ETFs with eight allocation assets | Default `submission` mode consumes the actual adjusted closes. All 21 ETFs are retained for coverage, initial-training correlation and factor attribution. The allocation universe remains the documented eight assets. |
| Price cache ends 20 August 2024; each ETF has one repeated AUM value | Actual coverage is reported, never extrapolated. Snapshot AUM is excluded from historical priors. No historical Treasury-bill series is fabricated. |
| Factor file ends June 2024 | Decimal-unit conversion, geometric monthly returns, conservative removal of first/last partial-month risk, and an explicit overlap period. Require 24 months and full-rank OLS. |
| Factor regressions and weight tilts | Maintained output is labelled time-series OLS attribution with IID standard errors. It does not claim Fama–MacBeth estimation or automatic factor tilting. |
| Macroeconomic context | World Bank series are selected by name; BIS series by full metadata key, not row 142. Charts retain percent and percent-of-GDP units. Release histories are unavailable, so these charts are context only. |
| Historical views dated 21 August 2024 | These views postdate the last supplied price. Earlier evaluation is a retrospective scenario, even though covariance/beta fitting is chronological. This limitation is now explicit in output metadata. |

`run_project.bat --check` and its shell equivalent now execute the actual submission
inputs by default. `--mode synthetic` remains an explicit software validation path.
Synthetic returns are not regressed against actual historical factors.

The output includes target-weight history, rebalance-level turnover, summarized
cost estimates, net walk-forward returns, assumptions, dates and a hash of the
input price table.

## What this amendment does not claim

The fixed views are historical scenarios rather than forecasts. Yahoo mode is a
convenient public-data example, not a point-in-time institutional dataset. The
test is a single historical path and does not establish statistical significance,
market impact, taxes, security-locate availability or future performance. Factor,
higher-moment, BAB and Kelly methods are maintained research implementations, but
their historical results remain sample-dependent rather than performance claims.
