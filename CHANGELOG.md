# Changelog

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
