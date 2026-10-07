# Data preparation

Third-party input files are deliberately not bundled. The maintained notebook obtains adjusted prices through Yahoo by default and uses the factor file below when available. Other historical inputs are documented for provenance and possible future extensions. Downloading a current file does not guarantee compatibility with a historical 2024 export.

## Daily ETF cache: `efts_dataset.csv`

The `efts` spelling is retained from the original project. The CSV uses one row per date and ETF, with these headers:

```text
Date,Open,High,Low,Close,Adj Close,Volume,Market Cap,ETF
```

- `Date`: ISO date, such as `2024-08-22`; no duplicate `(Date, ETF)` pairs.
- OHLC and `Adj Close`: numeric prices; preserve the provider's documented adjustment convention.
- `Volume`: numeric trading volume.
- `Market Cap`: numeric ETF AUM snapshot in a consistent currency, despite the historical column name. Record its observation date separately; repeating one snapshot down all rows does not create historical AUM data.
- `ETF`: one of the 21 symbols listed in the notebook, including SPY.

Obtain historical prices through a permitted provider. The notebook's fresh-download branch uses `yfinance` with `auto_adjust=False` and `multi_level_index=False`; the historical AUM scraper needs replacement or verification. Missing AUM must not be fabricated. Supply a documented snapshot before attempting AUM-weighted analyses.

For a changed sample window, ensure every symbol has coverage and review missing adjusted prices. The cache loader checks column presence, duplicate observations and per-symbol coverage; it is not a complete data-quality validator.

## Monthly factors: `F-F_Research_Data_5_Factors_2x3_monthly.csv`

Source: [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), Fama/French 5 Factors (2x3), monthly.

The original notebook expects a cleaned CSV with an **unnamed first column** holding `YYYYMM` codes:

```text
,Mkt-RF,SMB,HML,RMW,CMA,RF
```

Remove provider description lines, blank/footer blocks and the annual table, keeping only monthly six-digit date rows. Preserve the header spelling. Do not mix monthly and annual observations.

Set `FACTOR_UNIT = "percent"` when values follow the standard percentage-point convention, such as `1.0` for 1%. Set it to `"decimal"` only when the file has already been converted. The maintained loader converts once, validates the required columns and rejects implausible decimal values before regression.

The source library documents changes to its US return inputs beginning in 2025. Retain the download date and release vintage; a current download may revise historical observations.

## Inflation: `Inflation-data.xlsx`

Source: [World Bank inflation database](https://www.worldbank.org/en/research/brief/inflation-database).

The research reads worksheet `Aggregate`, columns `B:BG`, first five data rows, then transposes, promotes a row to headers and assigns four labels: `Year`, `Median`, `Average`, `GDP-weighted Average`. This is a positional assumption about the historical workbook. Inspect the workbook before running; a renamed current download alone is insufficient. Adapt the reader if the sheet layout changed and record the transformation.

## Global liquidity: `WS_GLI_csv_col.csv`

Source: [BIS global liquidity indicators](https://data.bis.org/topics/GLI).

The original input is a wide CSV containing metadata columns `L_POS_TYPE`, `BORROWERS_CTY`, `BORROWERS_SECTOR`, `UNIT_MEASURE`, and quarterly columns such as `1996-Q1`.

The code filters those metadata fields to `I`, `5J`, `A`, and `770`, respectively. Later it directly selects row label `142`. This row identity is not stable across exports. Verify the intended series by its metadata and stable series key; adapt that selection rather than assuming a fresh export has the same row order.

## Provenance record for a future reproducible release

For each input, record source URL, download timestamp, release/vintage, units, currency where relevant, observation window, adjustment settings, transformations and SHA-256 hash. Preserve the original input alongside any cleaned derivative outside the public repository unless redistribution is permitted. No data license is granted by this project.
