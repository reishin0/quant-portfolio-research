# Data inputs and provenance

## 16 October 2026 methodology inputs

`amendments_20261016/forecast_outcomes.json` records the Q3 diagnostic outcome proxy and Q4 pending outcome with source, availability time and comparability flags. Q3 uses issuer NAV-implied bullion, not a licensed matching spot series; neither entry is admitted to forecast-uncertainty calibration.

`paper_journal_20261016/` holds exclusive numbered research decision receipts. A receipt declares the new all-cash paper starting state, input/protocol hashes, actual recording time, intended future execution/return interval and targets. Never edit or backdate an entry. Historical reconstruction and future outcome files remain separate. No broker holding or trade is implied.

## 16 October 2026 dated additions

`refresh_20261016/` contains new adjusted prices and issuer valuations through October 15, SOFR and daily Treasury observations through October 14, and the latest available monthly factors through August. `refresh_manifest.json` and provider manifests record input hashes, actual observation dates and historical revision checks. Original and frozen input files remain unchanged.

`intraday_20261016/` contains separately sourced Yahoo one-minute bars for SPY, QQQ, DIA, IEF and SHY, October 1–15. The manifest retains retrieval times and raw-response hashes. These are retrospective aggregate bars, not native strategy receipts or measured Treasury yields.

Raw vendor workbooks, HTML, response files and redundant raw price exports remain local. The notebook runner requires every derived input hash; if raw sources are present it verifies them too, and records any absent optional raw source. A fresh download may differ and must use a new directory. No redistribution right is asserted by inclusion in this private research workspace.

The four original inputs are included unchanged in this private repository.
`manifest.json` records their SHA-256 hashes, sizes, units and coverage. Provider download timestamps are unknown.

**ORIGINAL 2024 SUBMISSION — inactive reference data by default.** Their notebook
configuration lines are commented and labelled as original. The active price run
uses the frozen Yahoo snapshot through 8 October 2026. `FACTOR_FILE` selects a new October 2026
factor download; `RUN_ORIGINAL_CONTEXT=False` disables the unchanged macro/AUM illustrations.
Explicitly selecting submission mode opts into the original price cache only.

| File | Content | Coverage | Use |
| --- | --- | --- | --- |
| `efts_dataset.csv` | 24,486 rows, 21 ETFs, 1,166 dates | 2 January 2020–20 August 2024 | Adjusted closes for allocation and full-universe diagnostics |
| `F-F_Research_Data_5_Factors_2x3_monthly.csv` | 732 monthly rows | July 1963–June 2024 | Five-factor excess-return attribution |
| `Inflation-data.xlsx` | World Bank inflation workbook | Aggregate global series, 1970–2023 | Annual inflation chart |
| `WS_GLI_csv_col.csv` | 225 BIS series | Selected series through 2023 Q2 | Quarterly bank-credit chart |

## Frozen prices and cash: 9 October 2026

- `etf_adjusted_20261009.csv`: 1,701 dates, nine ETFs, 2 January 2020–8 October 2026.
- `etf_actions_20261009.csv`: 258 current provider action records.
- `etf_snapshot_20261009.json`: requested/actual coverage, symbols, retrieval UTC,
  adjustment convention and SHA-256 hashes. Acquired with yfinance `auto_adjust=False`,
  `actions=True`; only `Adj Close` is used for returns. Dividends are not added again.
- `sofr_20261009.csv` and `sofr_provenance_20261009.json`: NY Fed SOFR downloaded
  through FRED, observation dates 20 December 2019–7 October 2026, with source URL,
  retrieval time, units and byte hash. Empty holiday observations remain in the raw CSV.

The price loader verifies both price/action hashes and refuses requests beyond the
snapshot's declared window. The notebook checks every expected NYSE session, rejects
missing or invalid quotes and flags adjusted moves over 10% with action metadata.
A corporate action annotation is context, not confirmation that an unusual move is correct.
Original submission mode audits its actual available window. Synthetic mode uses weekdays.

SOFR percent/year is divided by 100 and accrued ACT/360. Each overnight quote spans
calendar days until the next quote; interest is simple within that interval and compounds
at the next quote. The final quote covers at most four calendar days; longer extensions
fail. No rate is invented for uncovered dates. SOFR uses the
[NY Fed methodology](https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates)
and [FRED series](https://fred.stlouisfed.org/series/SOFR).

This current-vintage rate is a realized financing proxy published in arrears, not an
ex-ante input or a broker deposit product. Close-to-close application is an explicit
approximation. Debit/credit cash use the same rate; short borrow uses the separate
fixed annual assumption. A constant 3% replay holds target histories fixed and reports
financing sensitivity. Optimizer/CAPM forecast assumptions remain separate.

Revised adjusted prices and rates are frozen for reproducibility, not reconstructed
point-in-time histories. For newer dates, explicitly acquire a new dated snapshot and
manifest; retain this evidence. Yahoo mode exports the new run's price table separately.

## Current factors and views: 9 October 2026

- `F-F_Research_Data_5_Factors_2x3_monthly_20261009.csv`: 758 monthly rows,
  July 1963-August 2026, stored in percentage points.
- `ff5_source_20261009.zip`: unmodified official source download.
- `ff5_provenance_20261009.json`: URL, UTC retrieval time, hashes, coverage,
  units and exact cleaning rule. Keep only six-digit YYYYMM rows, strip field
  whitespace, retain numeric strings, and omit the annual table/footer.
- `professional_views_20261009.json`: dated source review and mapping decisions.
  This file contains research evidence, not executable numerical signals.

The factor loader divides percentages by 100 once. The notebook checks the
selected current CSV against its recorded hash. The new vintage replaces the
whole factor series for attribution; it is not appended to the 2024 snapshot.
The provider moved from CRSP FIZ to CIZ beginning with the January 2025 release,
and historical observations can change. These revised factors are descriptive
attribution inputs, not point-in-time data used for historical allocation.
No factor observations beyond the released August 2026 month are manufactured.

The JPM document located in Drive was uploaded on 9 October 2026 but published
on 9 June 2020. It remains a historical reference. The current official allocation
outlook is dated 1 October 2026; source URL, target horizon and ETF mapping
limitations are recorded in the JSON and displayed in the notebook. The source
index target is not an ETF total-return forecast or a relative ETF return spread.
No numerical confidence was supplied by the source. No active view is invented.

For explicit numerical views, publication must precede the fit cutoff at close t-2; execution occurs at close t-1
for a first earned return ending t. This conservatively excludes publication-day and
same-rebalance look-ahead. The report's October 1 publication cannot change the
October 1 target. `view_history.csv` records eligibility at every rebalance.

## ETF prices

The historical `efts` spelling is preserved. Columns are
`Date,Open,High,Low,Close,Adj Close,Volume,Market Cap,ETF`.
The maintained loader pivots `Adj Close` before calculating per-asset returns.
It rejects duplicate keys, invalid dates, missing requested symbols and
nonpositive/nonfinite prices. It does not fill gaps. End dates are exclusive.

`Market Cap` has one value per ETF repeated across all dates. The observation date of these capitalization/AUM values is unknown. It is excluded
from historical estimation. The cache does not include the separately queried
Treasury-bill yield. Allocation retains a stated constant cash-rate assumption.

The price data contain 21 ETFs. The eight allocation assets are VUG, SPHD, MTUM, ACWI, XLK, XLE, IEO and GLD.
SPY is the reference. The remaining 12 ETFs are retained in universe diagnostics
and attribution. The eight-ETF selection remains retrospective.

## Factors

Source: [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
The unnamed first column is `YYYYMM`; the other columns are `Mkt-RF,SMB,HML,RMW,CMA,RF`.
`FACTOR_UNIT="percent"` converts percentage points once: `1.0` becomes `0.01`.
New inputs must contain only monthly rows, without annual tables or footer text.

Attribution compounds daily returns, conservatively omits both boundary months,
and intersects dates with the factor vintage. It requires at least 24 aligned
months and a full-rank design. The original-input strategy sample was February 2022–June
2024 (29 months); full-universe attribution uses February 2020–June 2024 (53 months).
There are no July/August 2024 factors in the original file; the current file extends through August 2026. RF is used for monthly attribution
only; it is distinct from the SOFR realized-financing proxy and constant forecast assumption.

These are time-series OLS regressions with IID and three-lag HAC uncertainty,
plus Holm-adjusted alpha tests; they are not Fama–MacBeth cross-sectional estimates. Factor coefficients do not adjust weights.

## Macroeconomic context

Inflation source: [World Bank](https://www.worldbank.org/en/research/brief/inflation-database).
The `Aggregate` sheet is read by `HCPI_GLOBAL_MED`, `HCPI_GLOBAL_AVE` and
`HCPI_GLOBAL_AVE_GDP`, preserving annual percentage units rather than row offsets.

Liquidity source: [BIS](https://data.bis.org/topics/GLI).
The economic key is `FREQ=Q, CURR_DENOM=TO1, BORROWERS_CTY=5J,
BORROWERS_SECTOR=A, LENDERS_SECTOR=B, L_POS_TYPE=I, L_INSTR=A,
UNIT_MEASURE=770, UNIT_MULT=0`. The reader requires exactly one matching series,
never row 142. The chart retains percent-of-GDP units without min–max normalization.

These snapshots lack publication histories and are descriptive context only.
They do not feed earlier allocation decisions.

## Reuse

Inputs are included at the owner's request for private research. The project grants
no third-party data rights; review provider redistribution terms before making
them public.


## Executable view register

`view_register.json` stores disabled source records separately from numerical view
sets. Enabling a set requires source and mapping statements, publication/recording
and activation/expiry dates, a 12-month annual arithmetic total-return spread,
classification, and confidence with an uncertainty basis. Source facts and our
assumptions must be distinguishable. Current JPM records supply no eligible ETF
numerical mapping. The notebook validates the register and hashes it with each run.
Publication and mapping recording precede decisions. Activation is monthly; expiry
is exclusive at execution and adds a recorded exit rebalance. Newer available sets
supersede older sets, with no revival after expiry. Legacy fixed-view configuration
is not used by the main experiment runner.

## JPM research reviewed on 9 October 2026

`jpm_research_views_20261009.json` records six June–September research sources plus
GLD issuer information, source hashes when raw retrieval succeeded, rejection and
supersession decisions, and the explicit GLD scenario. The July revision is Reuters
attribution; the underlying JPM note was not available. No full copyrighted reports
are redistributed. Publication dates remain distinct from today's mapping date.
The 4,500 USD/oz Q4 average is not itself an ETF forecast or a terminal price.
All conversion, fee, quarterly observation and forecast-error assumptions are declared.
The file drives the separate reconstructed comparison, not the strict view register.


`gld_valuation_20261009.csv` contains 70 issuer NAV/ounces pairs from 1 July through
8 October, extracted from the issuer historical workbook. Two explicitly labelled
US holidays are excluded. The JSON source record pins the extracted CSV and the
retrieved workbook hash. NAV/ounces is an implied bullion proxy, not licensed LBMA
spot; the workbook itself stays in the ignored local research cache.

`forward_protocol_20261009.json` is the immutable first prospective specification.
It pins code, packages, policy and existing input vintages. Extended inputs go in
separate files, preserve frozen observations and are supplied explicitly to
`forward_evaluation.py`. Current files contain no subsequent evidence.
