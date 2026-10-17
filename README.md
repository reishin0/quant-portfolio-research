# Portfolio Construction Research

## Credit and funding extension — 17 October 2026

The separate [executed credit/funding notebook](credit_funding_research.ipynb) adds dated issuer disclosures, credit-versus-peer rules, sector/index separation and monthly cash-funding scenarios. It preserves both portfolio notebooks and their frozen protocols. Run `python run_credit_funding.py`; see [data contracts and evidence limits](research/credit_funding/README.md). The included case supports a funding watch, while issuer spread history and a usable company cash forecast remain unavailable. Synthetic scenarios validate accounting; no historical trading advantage or live integration is claimed.

## Reviewed executable notebook

Open [portfolio_construction_amended.ipynb](portfolio_construction_amended.ipynb) for the reviewed October 16 amendment, including saved results through October 15 and explicit amendment declarations. Reproduce it with `python run_reviewed_analysis.py` after the environment setup below. This verifies both frozen protocols, input hashes and the retained paper journal before executing. See [review fixes](research/REVIEW_FIXES_20261016.md).

The separate [frozen baseline](portfolio_construction.ipynb) and its pinned calculations are unchanged. The older runners below reproduce earlier stages; use the reviewed runner for the current amendment. The paper record remains pending, with no completed prospective outcome in the published snapshot.

## Implemented methodology improvements — 16 October 2026

`python run_amended_analysis.py` executes the refreshed baseline plus a separate common-risk experiment, prior-only uncertainty diagnostics, horizon rules and a read-only view of the paper decision journal. All added calculation functions are embedded in its generated notebook. See the [implementation and results](research/AMENDMENTS_IMPLEMENTED_20261016.md).

The common-risk experiment matches ex ante volatility at each rebalance; the scenario still trails equal weight. The journal records a pending paper decision before outcomes and evaluates outcomes separately. Forecast uncertainty remains explicitly uncalibrated because there are no qualifying completed comparable quarters. The frozen notebook and original protocol remain unchanged.

## 16 October 2026 refresh

The [dated research review](research/REFRESH_20261016.md) reports a completed notebook run with prices and issuer valuations through **15 October 2026**. Factors remain available only through August; SOFR and daily Treasury rates end on October 14. New input vintages are in `data/refresh_20261016/`. The frozen baseline described below remains unchanged.

Run `python run_updated_analysis.py --inputs data/refresh_20261016` to produce an executed derivative notebook and HTML report with the updated interpretation embedded. Historical Yahoo revisions mean this run is a current-vintage reconstruction, not an accepted extension of the frozen forward test. The five outstanding methodological improvements are reassessed in the review.

The [isolated intraday investigation](research/macro_regime/REVIEW_20261016.md) reports the macro-proxy/HMM tests, source gaps and negative findings. It does not change the portfolio model or live trading system.

**Reishin · Maintained continuation of the August 2024 portfolio study**

This repository implements a reproducible multi-asset portfolio research workflow. It combines Black–Litterman expected returns with conventional and advanced allocation methods, evaluates every strategy chronologically, and records data provenance, turnover and modeled implementation costs.

**Disclaimer:** The code and information in this repository are for educational and informational purposes only and do not constitute financial, investment or trading advice.

The work originated as a CQF Final Project submission titled **Portfolio Construction using Black-Litterman Model and Factors**. The original brief required delegates to implement the model and numerical techniques without AI coding tools and submit working, documented code with an analytical report. This repository is a later documented research edition with subsequent methodology and software amendments. The maintained project is broader than the submission brief: its design is governed by methodological consistency and reproducibility rather than by reproducing the original report structure.

## Research contract

Compare seven allocation rules on the same universe and dated accounting contract,
using net CAGR, excess-return Sharpe, drawdown and turnover relative to equal weight,
SPY and cash. Do not choose a winner from one observed sample. The notebook now
separates retrospective evidence, model assumptions and the work needed for a
prospective claim. Stages 1–7 implement mathematical controls, dated views, chronological selection,
uncertainty and bounded sensitivity experiments. Results remain retrospective; no
prospective performance or guaranteed research grade is claimed.

## Implemented research

- Frozen, hash-verified Yahoo adjusted ETF prices through 8 October 2026, with explicit fresh-Yahoo, original-submission and synthetic alternatives.
- Per-asset simple returns, exchange-session coverage checks and corporate-action annotations for large adjusted moves.
- Separate annualized covariance and correlation calculations.
- Black–Litterman prior and optional dated relative views with variance-scaled uncertainty; original 2024 views are commented out.
- Equal-weight, minimum-variance, Black–Litterman maximum-Sharpe and minimum-tracking-error portfolios.
- Higher-moment utility using its own portfolio moments, with deterministic multistart feasibility diagnostics.
- Cash-aware full Kelly fitted to completed monthly holding periods, followed by fractional scaling.
- BAB construction with beta-balanced legs and bounded gross exposure; the experiment explicitly holds cash and reports windows with ineligible leg betas.
- Fama–French five-factor attribution using the October 2026 download through August 2026; the original June-2024 file stays inactive.
- Original World Bank inflation and BIS bank-credit charts retained behind an explicit historical-context opt-in.
- Development-selected expanding/rolling-window evaluation: fit after close t-2, execute close t-1, earn the return ending t.
- Weight drift, one-way turnover, transaction costs, short-borrow costs, cash financing and timestamped outputs.
- Initial-window CAPM comparisons, rolling alpha/beta diagnostics and return-based window selection.
- Explicit Black–Litterman P/Q/Omega, posterior mean uncertainty and predictive covariance.
- Covariance-aware return-vector and risk-aversion allocation comparisons with cash.
- Third/fourth-order central-moment tensors checked against the actual portfolio return series.
- Sortino, tracking error, information ratio, factor-fit plots and net Kelly fraction comparisons.
- Prior-only versus dated-view controls with source/mapping separation, supersession and exclusive expiry.
- Absolute BL views and a separately labelled JPM-sourced GLD reconstruction, with quarterly observation, forecast-error and conversion-basis sensitivity.
- Four development/evaluation configurations, Ledoit–Wolf shrinkage, paired block-bootstrap intervals and HAC/Holm factor uncertainty.
- Cap, transaction/borrow-cost and confidence sensitivity; target exposures, signed variance contributions and drawdown duration.
- Results-derived interpretation and exported code/runtime/input specification hashes.

[`AMENDMENTS.md`](AMENDMENTS.md) documents the methodology corrections.

The four original data files are included. [data/manifest.json](data/manifest.json) records their hashes.

The notebook includes **all 51 calculation functions directly in its code cells**,
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

## JPM research review and GLD scenario

The notebook now audits June–September research in
[data/jpm_research_views_20261009.json](data/jpm_research_views_20261009.json).
The June 9 / July 1 public gold forecasts of USD 6,000 were superseded by a
[July 3 Reuters report of JPM's USD 4,500 Q4 average](https://www.investing.com/news/commodities-news/jp-morgan-says-weaker-demand-may-cap-gold-gains-nearterm-sees-rebound-in-late-2026-and-2027-4775299).
The underlying institutional note was unavailable. July equity, August factor and
September investor updates provide context, not unsupported numerical ETF spreads.

An absolute GLD view models the **quarterly average** directly. It conditions on already observed quarter valuations and solves a linear expected bullion path across the remaining weekdays. Same-date issuer NAV and ounces per share replace the mismatched July quotes. NAV-implied bullion remains a proxy, with an explicit intraday ETF/NAV basis term and 0.40% annual fee decay.

The model propagates a 10% quarterly forecast-error standard deviation and 2% basis-error standard deviation into annual-return Omega. These are uncalibrated research assumptions, not JPM probabilities. Half/double error and plus/minus 2% basis cases expose sensitivity. Increasing annualized uncertainty tempers short-horizon targets. Views expire 30 calendar days before quarter end.

Allocation maximizes mean/variance utility after modeled trading costs. Target weights stay within 15 percentage points of equal prior weights and the 35% asset cap (effective maximum 27.5%). Actual one-way turnover including cash is capped at 10% per rebalance, except initial deployment. Market drift and partial execution can leave actual holdings beyond target bounds; the audit reports this explicitly.

Five common-date, common-cost controls compare the scenario with its prior, a fixed five-point GLD overweight, GLD-matched exposure and cash-scaled equal-weight risk. The latter cannot lever up, and turnover limits can prevent exact exposure matching. Actual gaps are exported. Source publication first affects the return ending 3 August; this replay remains **retrospective**, because the rules were developed on 9 October. No sensitivity winner was selected. Synthetic and original-submission data skip the real 2026 scenario.

### Frozen forward evaluation

`data/forward_protocol_20261009.json` pins calculation code, policy, source inputs, runtime versions and the last examined observations. Verify it with:

```text
python forward_evaluation.py
```

To evaluate subsequently obtained observations, supply extended adjusted prices, issuer NAV/ounces and decimal realized cash returns:

```text
python forward_evaluation.py --prices data/extended_prices.csv --cash data/extended_cash.csv --valuations data/extended_gold_valuations.csv
```

`--help` specifies each CSV schema. Preserve every frozen historical row; revised Yahoo histories require a new dated protocol, not silent splicing. The evaluator rejects altered code/configuration, missing exchange sessions, revised input history and unfinished/future US closes. It starts with a fit strictly after the freeze date, executes at the next close and earns the following return. It creates a new output folder for every evaluation. All five controls start in cash together, with the same initial-entry exception.

No new observations are supplied in the current snapshot, so forward evidence is **pending**. This is an evaluator, not a scheduled refresh or trading system. Extended data provenance must be documented by its supplier. A changed design requires a separately named protocol using `--freeze --protocol data/<new-name>.json`; an existing freeze cannot be overwritten.

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
VIEW_REGISTER_FILE = "data/view_register.json"
DEVELOPMENT_END = "2023-12-31"
EVALUATION_START = "2024-01-01"
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
| `VIEW_REGISTER_FILE` | data/view_register.json | Dated view sets; all current sets disabled pending numerical mapping |
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
ETF spread or confidence. The strict recorded-date sets in `data/view_register.json` retain the prior.
The JPM source audit and explicit GLD reconstruction above provide a separate numerical scenario.

Enabled sets in `data/view_register.json` require an ID, source URL/title,
publication and mapping-record dates, activation, exclusive expiry, a 12-month
annual arithmetic total-return definition, numerical long/short ETF spreads,
confidence and its basis. Provider forecasts and mapping assumptions are separate.
Publication and recording must both precede the decision date. Monthly activation
and explicit expiry exits prevent a view being used before availability or retained
past validity. The latest available set supersedes older sets; an expired newer set
does not revive an older forecast. The prior-only control uses identical rebalance dates.

No set is enabled in the strict recorded-date register. That comparison is an
identity control: no contemporaneously recorded numerical view has been evaluated.
The separate JPM reconstruction reports mapped-view performance and sensitivity,
with its retrospective status and assumptions explicit.

## Experimental design and inference

The four fixed configurations are expanding/sample, 252-session/sample,
504-session/sample and 504-session/Ledoit–Wolf. Development runs cover January 2022
through December 2023. Minimum-variance portfolio volatility determines the selected
configuration; a stable label resolves ties. Evaluation starts in January 2024, from
cash with initial turnover charged. All candidates' later results remain visible.
These already inspected dates are retrospective, not an untouched holdout. Every
fit uses only prior observations and records its window, estimator and shrinkage.

The experiment's BAB eligibility rule holds cash when either leg has average beta
at or below 0.05; every occurrence is exported. The low-level API defaults to raising
unless `bab_failure_policy="cash"` is explicitly chosen. This avoids forcing leverage
through an invalid construction. Fully invested strategies, fractional Kelly and BAB
have different cash/leverage exposures; target averages and realized beta are shown.

Paired circular moving-block bootstrap uses 2,000 samples with block lengths 5, 21
and 63 sessions. It pairs strategies and cash on identical resampled dates, but
conditions on the fitted strategy paths. Its percentile intervals are pointwise,
exploratory and unadjusted for all research comparisons. Factor attribution adds
three-lag Bartlett/Newey–West HAC uncertainty and Holm-adjusted alpha p-values for
the displayed portfolio family; monthly gaps and samples below 24 months are rejected.
See [HAC documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)
and [Ledoit–Wolf documentation](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html).

The sensitivity registry records caps 25/35/50%, transaction costs 0/10/25 bps,
borrow costs 0/100/300 bps, and confidence 25/50/75%. Cost scenarios replay fixed
targets rather than reoptimizing. Confidence scenarios remain unavailable without
numerical views. Calendar-year slices include partial years and are descriptive.

The run exports a timestamped `research_specification.json`, source-code hash,
actual runtime configuration and its hash, input hashes, package versions and every
case's status. Prospective evidence requires an unchanged design frozen before new
observations; none is claimed here. Allow several minutes for the full experiment grid.

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
- restored diagnostic tables/figures, ordered moment tensors and `supplementary_info.json` with diagnostic settings;
- `run_info.json` with price-table hash, date coverage and model assumptions;
- configuration/case registries, candidate return/target/timing histories, bootstrap intervals, HAC attribution, sensitivities and a single research headline table;
- `research_specification.json` with the saved-source hash and actual runtime configuration;
- JPM source/mapping audits, P/Q/Omega, latest research weights and all five sensitivity cases and five allocation-control paths when real post-publication prices are available.

Existing output folders are never overwritten.

## Repository structure

| Path | Purpose |
| --- | --- |
| [`portfolio_construction.ipynb`](portfolio_construction.ipynb) | Authoritative research notebook |
| [`portfolio_tools.py`](portfolio_tools.py) | Data, Black–Litterman, optimization, walk-forward and reporting code |
| [`research_extensions.py`](research_extensions.py) | Factor regression, higher moments, Kelly and BAB methods |
| [`jpm_views.py`](jpm_views.py) | Sourced bullion-to-GLD mapping, matched reconstruction and sensitivity |
| [`forward_evaluation.py`](forward_evaluation.py) | Frozen-protocol verification and subsequent-data evaluation |
| [`research_validation.py`](research_validation.py) | Development selection, bootstrap, risk and sensitivity experiments |
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

## Interpretation limits

Parameter fitting is chronological, but the eight-ETF universe was selected in August 2024. Applying that selection to earlier dates remains retrospective. Original views are commented out; no October 2026 view forecasts have been invented. With no supplied views, the BL posterior equals its prior. The 3% forecast and cost parameters remain explicit assumptions. Historical SOFR supplies retrospective financing only; it is not a tradable deposit rate or a contemporaneously known forecast. Original macro snapshots lack release-date histories and are inactive descriptive references. The cost model excludes market impact, taxes and security-locate availability. Further genuinely forward evidence, point-in-time universes and realistic impact/funding/borrow models remain necessary for investment evaluation.

No repository license has been selected. Third-party code and data remain subject to their own terms. This project is quantitative research code, not personalized investment advice.
The inputs are currently included for private research; review provider redistribution
terms before changing repository visibility.
