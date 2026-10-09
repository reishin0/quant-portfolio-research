# Methodology amendments

**Initial amendment:** 6 October 2026

**Professional research consolidation:** 8 October 2026

**Source-code reconciliation and accounting corrections:** 9 October 2026

**Scope:** maintained professional continuation of the 2024 portfolio study

The August 2024 notebook is retained under `research_archive/` as provenance. Its
published results have not been silently rewritten. `portfolio_construction.ipynb`
and the tested Python modules form the single maintained implementation.

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

The supplied notebook contains 213 cells, including 127 code cells. Every code cell
has a destination and review decision in the maintained notebook's final source
reconciliation table. Metadata records the exact source-file hash, each code-cell
hash and destination cell IDs. The maintained notebook now contains 92 cells;
repeated displays and formula variants are consolidated. Historical files are unchanged.

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

The actual submission directory supplied the 49-page report, four original data
files, notebook and its `utils.py` dependency. The existing archive notebook was
replaced from that source, retaining all 127 code cells unchanged. Saved outputs,
execution counts and cell metadata were cleared; IDs and a provenance note were
added and the title attribution shortened. The PDF and data bytes are unchanged.
`data/manifest.json` records source and imported hashes. Duplicate HTML/DOCX,
bytecode and the declaration were excluded.

| Evidence in submission | Maintained implementation |
| --- | --- |
| Report Table 1, page 5: 21 ETFs plus RFR, with eight selected ETFs | Default `submission` mode consumes the actual adjusted closes. All 21 ETFs are retained for coverage, initial-training correlation and factor attribution. The allocation universe remains the documented eight assets. |
| Price cache ends 20 August 2024; each ETF has one repeated AUM value | Actual coverage is reported, never extrapolated. Snapshot AUM is excluded from historical priors. No historical Treasury-bill series is fabricated. |
| Factor file ends June 2024 | Decimal-unit conversion, geometric monthly returns, conservative removal of first/last partial-month risk, and an explicit overlap period. Require 24 months and full-rank OLS. |
| Report section 4.6 discusses factor regressions and weight tilts | Maintained output is labelled time-series OLS attribution with IID standard errors. It does not claim Fama–MacBeth estimation or automatic factor tilting. |
| Report section 4.7: macroeconomic context | World Bank series are selected by name; BIS series by full metadata key, not row 142. Charts retain percent and percent-of-GDP units. Release histories are unavailable, so these charts are context only. |
| Report section 4.8, pages 33–34: views as of 21 August 2024 | These views postdate the last supplied price. Earlier evaluation is a retrospective scenario, even though covariance/beta fitting is chronological. This limitation is now explicit in output metadata. |

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
