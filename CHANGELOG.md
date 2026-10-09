# Changelog

## 9 October 2026 — current factors and publication-date enforcement

- Save official monthly FF5 data through August 2026, raw source and hash provenance under data/.
- Record JPM Drive and current official report dates and ETF mapping limitations.
- Enforce publication dates in monthly allocation; export view eligibility and first activation.
- Use only eligible views in final notebook diagnostics; regenerate visible factor analysis.
- Preserve all original 2024 inputs unchanged.

## 9 October 2026 — original-input declaration and current price window

- Comment and label unchanged original price, factor, macro and view settings.
- Default notebook/report runs to Yahoo adjusted prices through 8 October 2026.
- Disable original factor/macro/AUM inputs until explicitly selected; retain their analysis code and original files.
- Make investor views explicit inputs; no views means posterior equals prior, with accurate view-date metadata.
- Regenerate visible notebook outputs on the updated price history.

## 9 October 2026 — complete source-analysis reconciliation

- Correct notebook presentation: place all 32 calculation implementations directly in the notebook and retain executed submission tables/charts for GitHub reading. The notebook now has 92 cells, including 44 executable cells; parity tests check its callable Python counterparts.

- Review and map every one of the supplied notebook's 127 code cells, with hashes and destination IDs.
- Expand the maintained notebook to 50 cells with CAPM, rolling exposures, BL matrices/covariance, risk-aversion allocations, moment tensors, factor diagnostics and Kelly fraction comparisons.
- Place AUM, factor-tilt and quartile-spread experiments plus macro/provider context after research interpretation.
- Consolidate redundant displays and replace invalid formulas explicitly; preserve historical input files unchanged.
- Reject internal price gaps, debit short-borrow charges from the holdings cash ledger, and solve full Kelly with cash before scaling.
- Add regression tests for economic identities, chronology, monthly units, caps, source coverage and optional provider calls.

## 8 October 2026 — actual submission inputs

- Import the original report, notebook lineage, helper and four input files with hashes.
- Add offline submission mode as the notebook/report default.
- Restore inflation and BIS bank-credit charts with named-series selection.
- Fit factors for the full 21-ETF universe and evaluated strategies using the actual vintage.
- Exclude monthly boundaries, enforce adequate overlap and reject rank-deficient factor designs.
- Declare retrospective universe/view selection and preserve original code cells separately.

## 8 October 2026 — professional research consolidation

- Made `portfolio_construction.ipynb` the single authoritative analysis.
- Moved the untouched 2024 notebook and its environment record to `research_archive/`.
- Removed the beginner/companion/legacy split from the maintained workflow and documentation.
- Added tested Fama–French five-factor loading and regression with explicit units.
- Added a dedicated higher-moment optimizer using its own portfolio weights.
- Added fractional Kelly log-growth allocation with a cash sleeve.
- Added beta-neutral BAB construction with bounded gross exposure.
- Extended walk-forward accounting to cash, signed weights, financing, transaction costs and short-borrow costs.
- Renamed the launchers, validation record and report runner around the research project.

## 6 October 2026 — initial public methodology amendment

- Added per-symbol return preparation, consistent annualization and distinct covariance/correlation handling.
- Added checked Black–Litterman, minimum-variance, maximum-Sharpe and tracking-error objectives.
- Added expanding-window monthly walk-forward evaluation, turnover and transaction costs.
- Added reproducible environment launchers, deterministic validation and timestamped outputs.

## August 2024 — original study

The original notebook is preserved unchanged under `research_archive/` for provenance. Its contemporaneous calculations and interpretations are not the authority for the maintained implementation.
