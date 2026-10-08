# Submission inputs and provenance

The four original inputs are included unchanged in this private repository.
`manifest.json` records their SHA-256 hashes, sizes, units and coverage, plus
the report and original notebook lineage. Provider download timestamps are unknown.

| File | Content | Coverage | Use |
| --- | --- | --- | --- |
| `efts_dataset.csv` | 24,486 rows, 21 ETFs, 1,166 dates | 2 January 2020–20 August 2024 | Adjusted closes for allocation and full-universe diagnostics |
| `F-F_Research_Data_5_Factors_2x3_monthly.csv` | 732 monthly rows | July 1963–June 2024 | Five-factor excess-return attribution |
| `Inflation-data.xlsx` | World Bank inflation workbook | Aggregate global series, 1970–2023 | Annual inflation chart |
| `WS_GLI_csv_col.csv` | 225 BIS series | Selected series through 2023 Q2 | Quarterly bank-credit chart |

## ETF prices

The historical `efts` spelling is preserved. Columns are
`Date,Open,High,Low,Close,Adj Close,Volume,Market Cap,ETF`.
The maintained loader pivots `Adj Close` before calculating per-asset returns.
It rejects duplicate keys, invalid dates, missing requested symbols and
nonpositive/nonfinite prices. It does not fill gaps. End dates are exclusive.

`Market Cap` has one value per ETF repeated across all dates. The report describes
scraped capitalization/AUM, but the observation date is unknown. It is excluded
from historical estimation. The cache does not include the separately queried
Treasury-bill yield. Allocation retains a stated constant cash-rate assumption.

Report Table 1 lists 21 ETFs and one separate risk-free series, rather than 22 ETFs.
Its eight allocation assets are VUG, SPHD, MTUM, ACWI, XLK, XLE, IEO and GLD.
SPY is the reference. The remaining 12 ETFs are retained in universe diagnostics
and attribution. The eight-ETF selection remains retrospective.

## Factors

Source: [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
The unnamed first column is `YYYYMM`; the other columns are `Mkt-RF,SMB,HML,RMW,CMA,RF`.
`FACTOR_UNIT="percent"` converts percentage points once: `1.0` becomes `0.01`.
New inputs must contain only monthly rows, without annual tables or footer text.

Attribution compounds daily returns, conservatively omits both boundary months,
and intersects dates with the factor vintage. It requires at least 24 aligned
months and a full-rank design. The default strategy sample is February 2022–June
2024 (29 months); full-universe attribution uses February 2020–June 2024 (53 months).
There are no July/August 2024 factors in this file. RF is used for monthly attribution
only, not silently substituted for the simulation's stated cash-rate assumption.

These are time-series OLS regressions with classical IID standard errors, not
Fama–MacBeth cross-sectional estimates. Factor coefficients do not adjust weights.

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
They do not feed earlier allocation decisions. The report's growth and risk-appetite
interpretations are not treated as extra supplied time-series datasets.

## Reuse

Inputs are included at the owner's request for private research. The project grants
no third-party data rights; review provider redistribution terms before making
them public. The declaration, duplicate report DOCX, exported notebook HTML and
bytecode cache are excluded. The PDF and notebook source retain the historical record.
