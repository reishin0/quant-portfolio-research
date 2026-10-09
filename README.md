# Portfolio Construction Research

**Reishin · Maintained continuation of the August 2024 portfolio study**

This repository implements a reproducible multi-asset portfolio research workflow. It combines Black–Litterman expected returns with conventional and advanced allocation methods, evaluates every strategy chronologically, and records data provenance, turnover and modeled implementation costs.

**Disclaimer:** The code and information in this repository are for educational and informational purposes only and do not constitute financial, investment or trading advice.

The work originated as a CQF Final Project submission titled **Portfolio Construction using Black-Litterman Model and Factors**. The original brief required delegates to implement the model and numerical techniques without AI coding tools and submit working, documented code with an analytical report. This repository is a later documented research edition with subsequent methodology and software amendments. The maintained project is broader than the submission brief: its design is governed by methodological consistency and reproducibility rather than by reproducing the original report structure.

## Research contract

Compare seven allocation rules on the same universe and dated accounting contract,
using net CAGR, excess-return Sharpe, drawdown and turnover relative to equal weight,
SPY and cash. Do not choose a winner from one observed sample. The notebook now
separates retrospective evidence, model assumptions and the work needed for a
prospective claim. Stages 1–3 establish mathematical and reproducibility controls;
robust validation, statistical uncertainty and implementation stress remain next work.

## Implemented research

- Frozen, hash-verified Yahoo adjusted ETF prices through 8 October 2026, with explicit fresh-Yahoo, original-submission and synthetic alternatives.
- Per-asset simple returns, exchange-session coverage checks and corporate-action annotations for large adjusted moves.
- Separate annualized covariance and correlation calculations.
- Black–Litterman prior and optional dated relative views with variance-scaled uncertainty; original 2024 views are commented out.
- Equal-weight, minimum-variance, Black–Litterman maximum-Sharpe and minimum-tracking-error portfolios.
- Higher-moment utility using its own portfolio moments, with deterministic multistart feasibility diagnostics.
- Cash-aware full Kelly fitted to completed monthly holding periods, followed by fractional scaling.
- Betting-against-beta construction with low/high beta legs, zero estimated market beta and bounded gross exposure.
- Fama–French five-factor attribution using the October 2026 download through August 2026; the original June-2024 file stays inactive.
- Original World Bank inflation and BIS bank-credit charts retained behind an explicit historical-context opt-in.
- Expanding-window monthly evaluation: fit after close t-2, execute close t-1, earn the return ending t.
- Weight drift, one-way turnover, transaction costs, short-borrow costs, cash financing and timestamped outputs.
- Initial-window CAPM comparisons, rolling alpha/beta diagnostics and return-based window selection.
- Explicit Black–Litterman P/Q/Omega, posterior mean uncertainty and predictive covariance.
- Covariance-aware return-vector and risk-aversion allocation comparisons with cash.
- Third/fourth-order central-moment tensors checked against the actual portfolio return series.
- Sortino, tracking error, information ratio, factor-fit plots and net Kelly fraction comparisons.

The original 2024 notebook is retained at [`research_archive/portfolio_construction_2024.ipynb`](research_archive/portfolio_construction_2024.ipynb) for provenance. It is not needed by the maintained implementation. [`AMENDMENTS.md`](AMENDMENTS.md) maps the original calculation issues to their current corrections.

The actual [49-page submission report](research_archive/submission_report_2024.pdf)
and four original data files are included. The archive notebook was refreshed from
the actual submission with 127 code cells unchanged and saved outputs cleared.
[data/manifest.json](data/manifest.json) records original and imported hashes.
The report is a historical reference; its numerical conclusions are not the results
of the amended implementation.

All **127 code cells** from the supplied **213-cell source notebook** are reconciled
in the maintained notebook's **Source-code reconciliation** appendix. The expanded
notebook has 97 cells: repeated displays and equivalent calculations are consolidated,
and defective calculations are replaced with declared corrections. Each source cell
has a hash and destination cell IDs in notebook metadata.

The notebook includes **all 35 calculation functions directly in its code cells**,
as well as saved frozen-input tables and charts with actual coverage through 8 October 2026. It can be read on GitHub
without first running it or opening a separate report. It imports third-party
libraries, but no project calculation modules. The `.py` files retain matching
callable functions for tests and reuse; tests enforce agreement with the notebook.

After **Research interpretation and next work**, supplementary sections retain the
AUM snapshot illustration, factor-threshold weight heuristic, quartile beta spread,
inflation/bank-credit context, and optional equity-index/gold/yield/VIX acquisition.
These sections do not change the seven main strategies. Set `RUN_NETWORK_CONTEXT=True`
to execute the optional extra provider calls. After environment setup, the default snapshot run is offline. Yahoo mode explicitly
requests new provider prices; synthetic mode remains a software check.

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

For an end-to-end run on the frozen October 2026 inputs and an HTML report:

```powershell
# Windows
.\run_project.bat --check
```

```sh
# macOS / Linux
sh run_project.command --check
```

For the tested Windows Python 3.13 package versions, use:

```powershell
python launch.py --locked --check
```

The lock pins the complete tested environment. Portable Python 3.11–3.13 installs
use the version ranges in `requirements.txt`; their numerical results require fresh
validation. Each report records actual package versions and notebook code hash.
Setup may need network access; frozen input evaluation does not. Missing sessions,
quotes or hash mismatches stop a run. To refresh prices explicitly, use
`--check --mode yahoo`; outputs record that provider vintage separately.

Use `--report` instead of `--check` to open the completed report after execution.
Use `--check --mode synthetic` for a separate generated-data software check.
`--check --mode submission` explicitly opts into the original 2024 price cache;
it does not enable old factors, macro snapshots or investor views automatically.

## Research configuration

The notebook defaults to the October 2026 price update. Original settings are
commented and declared as original, rather than silently reused:

```python
# ORIGINAL 2024 SUBMISSION — inactive historical references:
# DATA_MODE = "submission"
# END_DATE = "2024-08-23"
# FACTOR_FILE = "data/F-F_Research_Data_5_Factors_2x3_monthly.csv"

DATA_MODE = "snapshot"
CASH_MODE = "sofr"
START_DATE = "2020-01-01"
END_DATE = "2026-10-09"  # Exclusive: request through 8 October 2026.
FACTOR_FILE = "data/F-F_Research_Data_5_Factors_2x3_monthly_20261009.csv"
INVESTOR_VIEWS = []
VIEWS_AS_OF = None
RUN_ORIGINAL_CONTEXT = False
```

Set `DATA_MODE = "synthetic"` for deterministic offline validation. The program never silently substitutes synthetic prices after a failed Yahoo request.
The supplied prices end on 20 August 2024; a later requested end does not extend
the data. Yahoo mode requests a current provider vintage, which can differ from
the submitted snapshot.

The main implementation assumptions are visible in the first notebook cell:

| Setting | Default | Interpretation |
| --- | ---: | --- |
| `ANNUAL_RISK_FREE_RATE` | 3% | Forecast assumption and constant-cash sensitivity |
| `CASH_MODE` | sofr | Historical realized SOFR financing; synthetic uses constant |
| `MAX_WEIGHT` | 35% | Per-asset cap for long-only optimized portfolios |
| `TRAINING_DAYS` | 504 | Observations before the first evaluated target |
| `TRANSACTION_COST_BPS` | 10 | Cost per unit of one-way turnover |
| `ANNUAL_SHORT_BORROW_BPS` | 100 | Annual cost against gross short exposure |
| `KELLY_FRACTION` | 50% | Scale of constrained full-Kelly risky weights; balance remains in cash |
| `BAB_GROSS_LIMIT` | 2.0 | Maximum absolute long-plus-short exposure |
| `ROLLING_WINDOWS` | 30, 60, 90 | Candidates scored only on common initial-training dates |
| `RISK_AVERSIONS` | 0.5, 1, 3.07 | Mean–variance utility scenarios, with cash permitted |
| `KELLY_COMPARISON_FRACTIONS` | 0.50, 0.66, 1.00 | Net walk-forward sensitivity comparison |
| `RUN_NETWORK_CONTEXT` | False | Explicit opt-in for appendix market context and current metadata |
| `RUN_ORIGINAL_CONTEXT` | False | Explicit opt-in for unchanged original AUM/macro illustrations |
| `INVESTOR_VIEWS` | Empty | No original views applied; posterior equals the equilibrium prior |
| `FACTOR_FILE` | October 2026 download | Current factor vintage through August 2026 |

## Factor data and professional views

The active [monthly factors](data/F-F_Research_Data_5_Factors_2x3_monthly_20261009.csv)
contain 758 observations from July 1963 through August 2026, downloaded from the
[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
on 9 October 2026. The source ZIP and hash/cleaning metadata are also in `data/`.
September/October values are not fabricated. Percentage points are converted once
to decimals. Current CIZ-based history may revise older returns: this is a current
vintage for retrospective attribution, not a historical release database. The
original June-2024 file is unchanged and its setting remains commented out.

The [professional-view evidence](data/professional_views_20261009.json) records
JPM's official 1 October 2026 allocation outlook and the June 2020 report found in
Drive. The Drive upload date is not the report's publication date. The notebook
shows source links, dates and the limitations of translating those views to this
ETF universe. No qualitative preference is silently converted into a numerical
ETF spread or confidence. `INVESTOR_VIEWS=[]` therefore retains the prior.

Nonempty numerical views require `VIEWS_AS_OF="YYYY-MM-DD"`. Each rebalance uses
only views published strictly before its fit cutoff (t-2). Date-only
publications are treated as available after their entire publication day. The
October 1 report cannot affect October's first-day target; no eligible monthly
rebalance occurs before this sample ends on October 8. Every run exports
`view_history.csv` and its first activation date. Fixed numerical scenarios persist
after activation; a time-limited forecast needs an explicit validity/review policy
before activation. See [data documentation](data/README.md) for provenance.

## Outputs

Each run creates a new folder under `outputs/` containing:

- latest target weights, including cash;
- the complete rebalance target history;
- rebalance-level turnover and implementation-cost summaries;
- expected and realized performance tables, plus constant-cash sensitivity;
- solver diagnostics, exchange-session coverage, corporate-action flags and exported input prices/cash returns;
- allocation and growth charts;
- Fama–French strategy and loaded-universe regression outputs when a factor file is selected;
- universe coverage and initial-training correlation; original inflation/credit charts only on explicit historical opt-in;
- restored diagnostic tables/figures, ordered moment tensors and `supplementary_info.json` with source reconciliation;
- `run_info.json` with price-table hash, date coverage and model assumptions.

Existing output folders are never overwritten.

## Repository structure

| Path | Purpose |
| --- | --- |
| [`portfolio_construction.ipynb`](portfolio_construction.ipynb) | Authoritative research notebook |
| [`portfolio_tools.py`](portfolio_tools.py) | Data, Black–Litterman, optimization, walk-forward and reporting code |
| [`research_extensions.py`](research_extensions.py) | Factor regression, higher moments, Kelly and BAB methods |
| [`research_diagnostics.py`](research_diagnostics.py) | Restored CAPM, rolling exposure, allocation sensitivity, tensor and factor diagnostics |
| [`submission_data.py`](submission_data.py) | Frozen prices, named macro series and input-hash verification |
| [`data_tools.py`](data_tools.py) | Snapshot verification, exchange-session audit and SOFR accrual |
| [`data/`](data/) | Original inputs, dated updated snapshots and source manifests |
| [`requirements-lock-windows-py313.txt`](requirements-lock-windows-py313.txt) | Exact package pins for tested Windows Python 3.13 environment |
| [`tests/`](tests/) | Offline behavioral and look-ahead checks |
| [`run_project.bat`](run_project.bat) / [`run_project.command`](run_project.command) | Reproducible environment launchers |
| [`run_analysis.py`](run_analysis.py) | Deterministic notebook execution and HTML export |
| [`VALIDATION.md`](VALIDATION.md) | Dated verification evidence and scope |
| [`AMENDMENTS.md`](AMENDMENTS.md) | Corrections from the 2024 implementation |
| [`CHANGELOG.md`](CHANGELOG.md) | Maintained implementation history |
| [`research_archive/`](research_archive/) | Original notebook and historical environment record |

## Interpretation limits

Parameter fitting is chronological, but the eight-ETF universe was selected in August 2024. Applying that selection to earlier dates remains retrospective. Original views are commented out; no October 2026 view forecasts have been invented. With no supplied views, the BL posterior equals its prior. The 3% forecast and cost parameters remain explicit assumptions. Historical SOFR supplies retrospective financing only; it is not a tradable deposit rate or a contemporaneously known forecast. Original macro snapshots lack release-date histories and are inactive descriptive references. The cost model excludes market impact, taxes and security-locate availability. Multiple-period validation, predeclared universes and dated view histories remain necessary for investment evaluation.

No repository license has been selected. Third-party code and data remain subject to their own terms. This project is quantitative research code, not personalized investment advice.
The inputs are currently included for private research; review provider redistribution
terms before changing repository visibility.
