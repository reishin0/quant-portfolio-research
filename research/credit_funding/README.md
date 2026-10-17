# Daily credit and funding research

Open [the executed notebook](../../credit_funding_research.ipynb), or run from the repository root:

```powershell
.venv\Scripts\python.exe run_credit_funding.py
.venv\Scripts\python.exe -m unittest discover -s tests -p test_credit_funding.py -v
```

The runner creates a timestamped notebook, HTML report and receipt under `outputs/`. The root notebook is the reviewed copy. The extension does not alter either portfolio notebook, either frozen protocol, the paper journal, allocations or any trading process. Its source and input hashes are in `data/credit_funding_20261017/manifest.json`.

## What runs

- `funding_assessment` reads one issuer's dated disclosures and financing events. It separates historical investment funding needs, renewal exposure and evidence of successful financing. It never estimates current cash by adding financing proceeds to an old balance.
- `credit_assessment` requires one qualified daily OAS observation for a fixed issuer curve and comparable peer basket. The initial benchmark uses 20 prior observations and three persistent observations, with widening of at least 100 bp and peer-relative widening of at least 50 bp. These untuned assumptions are software research rules, not fitted probabilities. Raw yields, stale observations, changing baskets and insufficient coverage produce `UNKNOWN`.
- `combine_assessments` retains issuer, sector and broad-market states independently. Broad-market stress needs broad credit stress and separately qualified current equity breadth. Issuer stress alone cannot become a SPY signal. All outputs are research-only and expose `trading_permission=NOT_CONNECTED`.
- `funding_path` reconciles a monthly cash path for one legally usable cash pool. Separate scenario assumptions change unhedged floating and refinanced-fixed costs, discretionary spending, committed access and collateral capacity. Explicit monthly receipt shortfalls model delays or weaker renewals. Cash flows, principal and facility draws reconcile independently.

## Input contracts

The October 17 review corrected three edge cases: a later filing for an older accounting period no longer overrides a newer period; cached credit/sector states cannot cross decision times or assessment types; and facility list order no longer determines which drawable capacity is exhausted. Facilities now draw in earliest-expiry order, with a stable ID tie-break. This is an explicit liquidity convention, not a global cost optimum. `remaining_nominal_capacity` can include unusable future/expired commitments; only `drawable_capacity` passes the current whole-month availability check. Missing dates and nonnumeric or boolean cash inputs are rejected.

Issuer, broad and sector inputs to `combine_assessments` must be complete assessment dictionaries returned by `credit_assessment`, stamped at the funding decision's `asof_utc`. Sector entries are keyed by issuer; bare state strings, stale/future evaluations or incorrect assessment types remain unknown. A same-period financial revision enters only from its eligibility timestamp, while newer accounting periods retain priority over older restatements.

Disclosure records require an issuer, accounting period, publication date, timezone-aware `eligible_at`, source URL and availability basis. The included date-only announcements use the following local midnight as a conservative research boundary; this does not establish actual historical arrival or an observed warning time. A stale financial period is not carried forward indefinitely.

Credit records require `observed_at`, `eligible_at`, `spread_bp`, `peer_spread_bp` for issuer comparisons, `qualified=true`, `spread_kind=OAS_BP`, and a stable `comparison_id`. Qualification must establish maturity, seniority, currency, credit-quality and option comparability and document a consistent aggregation method. Boolean qualification is an explicit caller assertion, not an automatic data licence or instrument audit. Outliers and illiquid prints need to be screened upstream. Daily aggregates must preserve data corrections as newly available vintages, not overwrite historical observations.

The cash engine requires all `CASH_COLUMNS`, in the declared order, on unique consecutive month ends for 1–24 months. Units are USD millions. Operating cash flow must already deduct baseline interest and operating leases. Add only incremental interest shocks, finance-lease principal and other non-operating payments. Floating and refinanced-fixed balances must be disjoint. Hedges and refinancing enter through monthly exposed balances; no hedge is assumed to continue beyond its declared schedule.

Facilities require a unique ID, same cash pool, verified drawable capacity and availability dates. Capacity is consumed once and must cover the whole month to be admitted. An expired facility cannot be drawn. Restricted subsidiary cash or uncommitted financing cannot be entered as usable parent cash. Draw-related baseline interest must be included in supplied OCF or exposure balances. Monthly balances can conceal intra-month shortfalls; this is a bounded cash stress engine, not a complete treasury forecast.

## Current evidence and limitations

The source-checked case yields `FUNDING_VULNERABILITY` and `RECENT_COMPLETED_FINANCING`. Issuer credit, sector and broad-market states remain `UNKNOWN`. The broad-credit file contains five descriptive current-vintage values, not a qualified historical release panel. Source dates are not converted into invented precise market timestamps. Missing monthly company inputs prevent a real forward funding-gap calculation.

Seven fictional cash scenarios exercise the implementation. They are not estimates of CoreWeave's future. The source facts and URLs are retained in [source_observations.json](../../data/credit_funding_20261017/source_observations.json). The media-reported roughly 15% bond yield is not used as a substitute for instrument-level OAS observations.

The requested three-way comparison is `NOT_EVALUATED_MISSING_QUALIFIED_HISTORY_AND_EXPOSURE_POLICY`. Completing it requires a qualified issuer/peer credit panel, historical publication/arrival vintages, matched daily equity inputs and an explicit exposure policy. Measure lead time, missed losses, false alerts and foregone gains after costs on identical coverage, with non-overlapping event labels and untouched issuer/period holdouts. This known case cannot establish out-of-sample early-warning accuracy. A complex state model does not repair missing inputs.

This extension adds no subscriptions, scheduled capture, broker calls, live/shadow controls or default-probability estimates.
