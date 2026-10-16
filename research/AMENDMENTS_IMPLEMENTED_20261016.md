# Implemented improvements — 16 October 2026

This amendment supersedes the outstanding-work status in the earlier same-day review. The frozen October 9 notebook, source modules, input files and forward protocol remain unchanged. The new notebook contains the additional implementation inline and executes it after the original research sections. Historical refresh outputs remain reproducible separately.

## Changes implemented

1. **Decision capture and outcome separation.** `paper_research.py` verifies the new protocol, source/runtime/data hashes and latest completed NYSE close, then records a research allocation before the next execution close. Exclusive numbered files and a hash chain detect accidental modification or missing entries. Capture time comes from the wall clock; callers cannot backdate it. Duplicate decisions, unavailable inputs, expired execution windows and invalid targets are rejected. The first paper account starts from cash explicitly. Its subsequent return is evaluated only in a separate function/command after the recorded interval completes; no outcome is invented now. The local chain is tamper-evident under a retained head hash, not an externally notarized ledger or a broker receipt. A complete rewrite or tail deletion requires comparing with the recorded external head/hash; this limitation is explicit.

2. **Horizon-aware rules.** Quarter-average forecast error is scored only after quarter completion and outcome availability. Longer-run strategy inference requires at least 60 genuinely subsequent sessions and eight completed comparable forecast cycles in the new design. Those are declared research minimums, not a guarantee of statistical power. For a paper entry captured before the October 16 close, only **32 active return sessions** remain before the existing December 2 execution-expiry boundary. Calendar calculation handles weekends, holidays and early closes. The 60-session rule is not lowered to make this quarter pass. A qualified cycle registry and continued recording are still required before either gate can pass.

3. **A common-risk control that actually matches.** Both risky portfolio directions are determined using data through decision close t-2 and the same trailing 252-session annual covariance. At execution close t-1, a predeclared scalar cash overlay uses the then-current holdings and frozen covariance/directions. Linear programs find each sleeve's feasible exposure interval under the same 27.5% asset cap, 10% one-way turnover limit including cash, no leverage and an explicit initial cash-entry exception. The overlap defines the highest jointly feasible volatility. If there is no overlap, both hold and the audit exposes the mismatch. No expected return is refitted at execution. Equal risk is a rebalance property under the prior covariance, not guaranteed realized or continuous risk equality.

4. **Prior-only uncertainty diagnostics and admission gates.** A forecast-error estimator accepts only completed, available, distinct quarters with comparable forecast lead horizons and verified outcome definitions. It shrinks mean squared forecast errors toward the existing 10% assumption after the declared minimum of eight qualifying quarters; below that, the assumption is retained and labelled uncalibrated. Daily close/NAV basis diagnostics use only prior observations, with 40 initial pairs and a 40-pair variance prior at 2%. The empirical basis estimate is not inserted into Omega because daily timing basis does not identify the full remaining-quarter conversion error.

5. **Traceability.** The amendment design is recorded before the new retrospective comparison. The paper protocol is separately frozen after validation, with the original protocol as a dependency. Notebook source hashes, test results, data identities, decision receipt and outputs are recorded. No baseline pin was relaxed, historical observations spliced, parameter selected for a better result, or trading integration activated.

## Results and what they mean

The new paired experiment starts both accounts in cash before the first active return on **3 August**, charges their initial investment costs, and runs through **15 October, 53 sessions**. This is a distinct experiment from taking a slice of portfolios already operating since 2024; the old and new return figures cannot be treated as a pure one-variable attribution.

| Paired account | Net cumulative return | Initial risky exposure | Later one-way turnover |
|---|---:|---:|---:|
| JPM-mapped scenario at common risk | 5.5597% | 95.7870% | 3.0781%, 1.6502% |
| Equal weight at common risk | 5.7420% | 100.0000% | 1.4943%, 2.0892% |

The scenario trails by about **0.1823 percentage points**. Both accounts have equal ex ante volatility at the three rebalances: approximately **12.2030%, 12.1452%, 12.3888%** annualized. Maximum numerical risk gap is below 1e-8; no rebalance was infeasible. Independent portfolio accounting agrees with the execution turnover ledger. Cash earns the same realized SOFR proxy, and both pay 10 bp per unit of one-way turnover. The initial deployment exception is reported, not hidden. This does not establish source-view alpha or prospective profitability.

The basis data contain **75 aligned issuer/ETF observations**. After 40 training pairs, **35 subsequent observations** are checked chronologically. Full-sample diagnostic RMSE is **0.7304%** and standard deviation **0.7343%**; the last prior-only shrunk sigma is **1.3236%**. All 35 observed basis values fall within the assumed normal 1.96-sigma bands. These observations are serially dependent, the distribution is not proven normal, and 100% sample coverage does not validate a nominal 95% forecast band. The issuer NAV time and market close differ. The existing 2% mapping basis assumption therefore remains active.

Reuters syndications explicitly describe the July 3 forecasts as quarterly averages: **$4,300 for Q3 and $4,500 for Q4**. The Q3 issuer NAV-implied bullion weekday-average proxy is approximately **$4,266.40**, a **-0.7813%** diagnostic error versus $4,300. It is excluded from comparable calibration: that forecast was issued after the quarter started, and neither the provider's exact averaging calendar nor a matching licensed bullion outcome is established. Q4 is unfinished. There are **zero eligible calibration quarters**, so the 10% forecast-error assumption stays unchanged. This is a completed data-admission check, not a claim that uncertainty has been calibrated. [Reuters via Kitco](https://www.kitco.com/news/off-the-wire/2026-07-03/jp-morgan-says-weaker-demand-may-cap-gold-gains-near-term-sees-rebound)

## What remains data-dependent

The first paper decision was captured at **2026-10-16 05:49:05 UTC** and its hash chain verifies. Both new accounts have estimated volatility **12.1120%** under the same prior covariance. The scenario target holds approximately **13.9561% GLD** and **1.6544% cash**; the equal-weight account holds 12.5% in each ETF and no cash. These targets differ from the historical portfolio's latest target because the new paper accounts explicitly start in cash. The receipt is `data/paper_journal_20261016/000001.json`, with hash `5808c1f3bcfb7c85202cd42ab552675f6605f3d2c4d9a1bb0d27b80a16cfdc66`. No paper return has been observed.

- Completed, dated, comparable forecast/outcome vintages are needed before fitting forecast uncertainty or testing its interval coverage.
- A qualified price pair after the paper execution and first holding interval is needed before recording even one subsequent paper return. The first intended execution is **October 16, 20:00 UTC**; the first interval ends **October 19, 20:00 UTC**. Neither is an observed fill or return at capture time.
- Continuing beyond the first paper interval requires new verified data vintages and drifted paper holdings, not repeated all-cash resets. The current journal entry explicitly scopes itself to the first interval. No continuous track record is claimed.
- Native intraday arrival timestamps, original session/trade logs and measured yields are still absent. The earlier macro-proxy negative result remains intact; no live/shadow change is justified by these portfolio amendments.

## Reproduction

Validation ran **113 tests: 112 passed, one existing optional HMM test skipped**. New checks include closed-form risk scaling, infeasible risk intervals, cash turnover, future-data independence, calibration admission, calendar boundaries, journal integrity and independent outcome arithmetic. Notebook construction also verifies that all 54 refreshed baseline code cells are unchanged and that the new inline functions exactly match their tested module definitions.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -q
.venv\Scripts\python.exe run_amended_analysis.py

# Explicit capture only. An existing identical decision ID is rejected.
.venv\Scripts\python.exe paper_research.py record --protocol research/paper_protocol_20261016.json --journal data/paper_journal_20261016
```

The amended runner creates a new executed notebook and HTML report in a timestamped output directory. The notebook only reads the journal; rerunning analysis never appends a paper decision. Later, the separate `paper_research.py evaluate` command requires a two-row Date-indexed close file matching the recorded dates and the realized interval cash return. It refuses unfinished outcomes and saves new outcome files without modifying the decision. These commands operate only on local research files.
