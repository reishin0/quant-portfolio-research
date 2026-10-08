# Portfolio Construction Research

**Reishin · Maintained continuation of the August 2024 portfolio study**

This repository implements a reproducible multi-asset portfolio research workflow. It combines Black–Litterman expected returns with conventional and advanced allocation methods, evaluates every strategy chronologically, and records data provenance, turnover and modeled implementation costs.

**Disclaimer:** The code and information in this repository are for educational and informational purposes only and do not constitute financial, investment or trading advice.

The work originated as a CQF Final Project submission titled **Portfolio Construction using Black-Litterman Model and Factors**. The original brief required delegates to implement the model and numerical techniques without AI coding tools and submit working, documented code with an analytical report. This repository is a later documented research edition with subsequent methodology and software amendments. The maintained project is broader than the submission brief: its design is governed by methodological consistency and reproducibility rather than by reproducing the original report structure.

## Implemented research

- Frozen adjusted ETF prices from the 2024 submission, with explicit Yahoo and synthetic alternatives.
- Per-asset simple returns with explicit missing-data alignment.
- Separate annualized covariance and correlation calculations.
- Black–Litterman prior, stated relative views and variance-scaled view uncertainty.
- Equal-weight, minimum-variance, Black–Litterman maximum-Sharpe and minimum-tracking-error portfolios.
- Higher-moment utility using the portfolio's own mean, variance, skewness and excess kurtosis.
- Fractional Kelly log-growth allocation with an explicit cash balance.
- Betting-against-beta construction with low/high beta legs, zero estimated market beta and bounded gross exposure.
- Fama–French five-factor attribution using the supplied vintage, for all 21 ETFs and the evaluated strategies.
- World Bank inflation and BIS bank-credit charts selected by named series and economic metadata.
- Expanding-window monthly walk-forward evaluation using only information available before each rebalance.
- Weight drift, one-way turnover, transaction costs, short-borrow costs, cash financing and timestamped outputs.

The original 2024 notebook is retained at [`research_archive/portfolio_construction_2024.ipynb`](research_archive/portfolio_construction_2024.ipynb) for provenance. It is not needed by the maintained implementation. [`AMENDMENTS.md`](AMENDMENTS.md) maps the original calculation issues to their current corrections.

The actual [49-page submission report](research_archive/submission_report_2024.pdf)
and four original data files are included. The archive notebook was refreshed from
the actual submission with 127 code cells unchanged and saved outputs cleared.
[data/manifest.json](data/manifest.json) records original and imported hashes.
The report is a historical reference; its numerical conclusions are not the results
of the amended implementation.

## Run the project

Install 64-bit Python 3.11, 3.12 or 3.13. Download and extract the repository, then open its `portfolio-construction` folder.

On Windows, double-click:

```text
run_project.bat
```

On macOS or Linux:

```sh
sh run_project.command
```

The launcher creates a local `.venv`, installs the declared dependencies, registers the project kernel and opens [`portfolio_construction.ipynb`](portfolio_construction.ipynb). It does not install into the system Python environment.

For an end-to-end run on the actual submission inputs and an HTML report:

```powershell
# Windows
.\run_project.bat --check
```

```sh
# macOS / Linux
sh run_project.command --check
```

Use `--report` instead of `--check` to open the completed report after execution.
Use `--check --mode synthetic` for a separate generated-data software check, or
`--check --mode yahoo` for fresh prices. After dependency installation, submission
mode requires no network access.

## Research configuration

The notebook defaults to the supplied adjusted-price snapshot:

```python
DATA_MODE = "submission"
START_DATE = "2020-01-01"
END_DATE = "2024-08-23"
```

Set `DATA_MODE = "synthetic"` for deterministic offline validation. The program never silently substitutes synthetic prices after a failed Yahoo request.
The supplied prices end on 20 August 2024; a later requested end does not extend
the data. Yahoo mode requests a current provider vintage, which can differ from
the submitted snapshot.

The main implementation assumptions are visible in the first notebook cell:

| Setting | Default | Interpretation |
| --- | ---: | --- |
| `ANNUAL_RISK_FREE_RATE` | 3% | Constant annual cash/financing assumption |
| `MAX_WEIGHT` | 35% | Per-asset cap for long-only optimized portfolios |
| `TRAINING_DAYS` | 504 | Observations before the first evaluated target |
| `TRANSACTION_COST_BPS` | 10 | Cost per unit of one-way turnover |
| `ANNUAL_SHORT_BORROW_BPS` | 100 | Annual cost against gross short exposure |
| `KELLY_FRACTION` | 50% | Risky sleeve size; balance remains in cash |
| `BAB_GROSS_LIMIT` | 2.0 | Maximum absolute long-plus-short exposure |

## Factor data

The supplied Kenneth French factor file is included at:

```text
data/F-F_Research_Data_5_Factors_2x3_monthly.csv
```

Set `FACTOR_UNIT = "percent"` for the standard library convention where `1.0` means 1%, or `"decimal"` if the file has already been converted. The loader validates the date rows and required columns before regression. See [`data/README.md`](data/README.md).
This vintage ends in June 2024. Attribution omits boundary months and reports the
actual overlapping dates. Synthetic mode skips regressions against real factors.

## Outputs

Each run creates a new folder under `outputs/` containing:

- latest target weights, including cash;
- the complete rebalance target history;
- rebalance-level turnover and implementation-cost summaries;
- expected and realized performance tables;
- allocation and growth charts;
- Fama–French strategy and 21-ETF regression outputs in submission mode;
- universe coverage, initial-training correlation, inflation and bank-credit tables and charts;
- `run_info.json` with price-table hash, date coverage and model assumptions.

Existing output folders are never overwritten.

## Repository structure

| Path | Purpose |
| --- | --- |
| [`portfolio_construction.ipynb`](portfolio_construction.ipynb) | Authoritative research notebook |
| [`portfolio_tools.py`](portfolio_tools.py) | Data, Black–Litterman, optimization, walk-forward and reporting code |
| [`research_extensions.py`](research_extensions.py) | Factor regression, higher moments, Kelly and BAB methods |
| [`submission_data.py`](submission_data.py) | Frozen prices, named macro series and input-hash verification |
| [`data/`](data/) | Four original inputs and provenance manifest |
| [`tests/`](tests/) | Offline behavioral and look-ahead checks |
| [`run_project.bat`](run_project.bat) / [`run_project.command`](run_project.command) | Reproducible environment launchers |
| [`run_analysis.py`](run_analysis.py) | Deterministic notebook execution and HTML export |
| [`VALIDATION.md`](VALIDATION.md) | Dated verification evidence and scope |
| [`AMENDMENTS.md`](AMENDMENTS.md) | Corrections from the 2024 implementation |
| [`CHANGELOG.md`](CHANGELOG.md) | Maintained implementation history |
| [`research_archive/`](research_archive/) | Original notebook and historical environment record |

## Interpretation limits

Parameter fitting is chronological, but the eight-ETF universe and views were chosen in August 2024. The report dates the views to 21 August, after the supplied prices end. Applying those choices to earlier dates is a retrospective scenario, not a point-in-time out-of-sample strategy test. Macro snapshots lack release-date histories and are descriptive context only. The cost model excludes market impact, taxes and security-locate availability. Multiple-period validation, predeclared universes and dated view histories remain necessary for investment evaluation.

No repository license has been selected. Third-party code and data remain subject to their own terms. This project is quantitative research code, not personalized investment advice.
The inputs are currently included for private research; review provider redistribution
terms before changing repository visibility.
