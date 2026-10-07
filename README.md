# Portfolio Construction Research

**Reishin · Maintained continuation of the August 2024 portfolio study**

This repository implements a reproducible multi-asset portfolio research workflow. It combines Black–Litterman expected returns with conventional and advanced allocation methods, evaluates every strategy chronologically, and records data provenance, turnover and modeled implementation costs.

**Disclaimer:** The code and information in this repository are for educational and informational purposes only and do not constitute financial, investment or trading advice.

The work originated as a CQF Final Project submission titled **Portfolio Construction using Black-Litterman Model and Factors**. The original brief required delegates to implement the model and numerical techniques without AI coding tools and submit working, documented code with an analytical report. This repository is a later documented research edition with subsequent methodology and software amendments. The maintained project is broader than the submission brief: its design is governed by methodological consistency and reproducibility rather than by reproducing the original report structure.

## Implemented research

- Adjusted ETF prices from Yahoo Finance, with deterministic synthetic data available for offline validation.
- Per-asset simple returns with explicit missing-data alignment.
- Separate annualized covariance and correlation calculations.
- Black–Litterman prior, stated relative views and variance-scaled view uncertainty.
- Equal-weight, minimum-variance, Black–Litterman maximum-Sharpe and minimum-tracking-error portfolios.
- Higher-moment utility using the portfolio's own mean, variance, skewness and excess kurtosis.
- Fractional Kelly log-growth allocation with an explicit cash balance.
- Betting-against-beta construction with low/high beta legs, zero estimated market beta and bounded gross exposure.
- Optional Fama–French five-factor attribution with explicit percentage-point-to-decimal conversion.
- Expanding-window monthly walk-forward evaluation using only information available before each rebalance.
- Weight drift, one-way turnover, transaction costs, short-borrow costs, cash financing and timestamped outputs.

The original 2024 notebook is retained at [`research_archive/portfolio_construction_2024.ipynb`](research_archive/portfolio_construction_2024.ipynb) for provenance. It is not needed by the maintained implementation. [`AMENDMENTS.md`](AMENDMENTS.md) maps the original calculation issues to their current corrections.

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

For a deterministic end-to-end validation run and HTML report:

```powershell
# Windows
.\run_project.bat --check
```

```sh
# macOS / Linux
sh run_project.command --check
```

Use `--report` instead of `--check` to open the completed report after execution.

## Research configuration

The notebook defaults to adjusted Yahoo prices:

```python
DATA_MODE = "yahoo"
START_DATE = "2020-01-01"
END_DATE = "2024-08-23"
```

Set `DATA_MODE = "synthetic"` for deterministic offline validation. The program never silently substitutes synthetic prices after a failed Yahoo request.

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

Factor attribution is optional because the Kenneth French dataset is not redistributed. Place a permitted cleaned copy at:

```text
data/F-F_Research_Data_5_Factors_2x3_monthly.csv
```

Set `FACTOR_UNIT = "percent"` for the standard library convention where `1.0` means 1%, or `"decimal"` if the file has already been converted. The loader validates the date rows and required columns before regression. See [`data/README.md`](data/README.md).

## Outputs

Each run creates a new folder under `outputs/` containing:

- latest target weights, including cash;
- the complete rebalance target history;
- rebalance-level turnover and implementation-cost summaries;
- expected and realized performance tables;
- allocation and growth charts;
- optional Fama–French regression output;
- `run_info.json` with price-table hash, date coverage and model assumptions.

Existing output folders are never overwritten.

## Repository structure

| Path | Purpose |
| --- | --- |
| [`portfolio_construction.ipynb`](portfolio_construction.ipynb) | Authoritative research notebook |
| [`portfolio_tools.py`](portfolio_tools.py) | Data, Black–Litterman, optimization, walk-forward and reporting code |
| [`research_extensions.py`](research_extensions.py) | Factor regression, higher moments, Kelly and BAB methods |
| [`tests/`](tests/) | Offline behavioral and look-ahead checks |
| [`run_project.bat`](run_project.bat) / [`run_project.command`](run_project.command) | Reproducible environment launchers |
| [`run_analysis.py`](run_analysis.py) | Deterministic notebook execution and HTML export |
| [`VALIDATION.md`](VALIDATION.md) | Dated verification evidence and scope |
| [`AMENDMENTS.md`](AMENDMENTS.md) | Corrections from the 2024 implementation |
| [`CHANGELOG.md`](CHANGELOG.md) | Maintained implementation history |
| [`research_archive/`](research_archive/) | Original notebook and historical environment record |

## Interpretation limits

Walk-forward evaluation limits direct look-ahead but does not prove economic significance or future performance. The current views are fixed research scenarios. Yahoo data are convenient public data rather than a point-in-time institutional dataset. The cost model excludes market impact, taxes and security-locate availability. Strategy comparison across one sample can still reflect selection bias; the notebook identifies multiple-period validation and bootstrap uncertainty as future work.

No repository license has been selected. Third-party code and data remain subject to their own terms. This project is quantitative research code, not personalized investment advice.
