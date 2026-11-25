"""Run the portfolio calculations on seeded, fictional prices only."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def _research_module():
    # Make the example runnable from any working directory in this checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    try:
        import portfolio_tools
    finally:
        sys.path.pop(0)
    return portfolio_tools


research = _research_module()
FIT_ROWS = 504
MAX_WEIGHT = 0.35
BENCHMARK = "Fictional benchmark"


@dataclass(frozen=True)
class DemoResult:
    seed: int
    fit_start: pd.Timestamp
    fit_end: pd.Timestamp
    evaluation_start: pd.Timestamp
    evaluation_end: pd.Timestamp
    weights: pd.DataFrame
    metrics: pd.DataFrame


def run_demo(seed: int = 42) -> DemoResult:
    prices, _ = research.load_prices(
        mode="synthetic", start="2020-01-01", end="2023-01-01", seed=seed
    )
    names = {symbol: f"Asset {chr(65 + i)}" for i, symbol in enumerate(research.ASSETS)}
    prices = prices.rename(columns={**names, research.BENCHMARK: BENCHMARK})
    returns = research.aligned_returns(prices)
    fit, evaluation = returns.iloc[:FIT_ROWS], returns.iloc[FIT_ROWS:]
    fit_assets = fit.drop(columns=BENCHMARK)
    covariance = fit_assets.cov() * research.PERIODS_PER_YEAR
    _, posterior, _ = research.black_litterman(
        covariance, views=[("Asset A", "Asset B", 0.04, 0.65)]
    )
    weights = research.optimize_weights(
        posterior, covariance, fit_assets, fit[BENCHMARK], cap=MAX_WEIGHT
    )

    # Multiplying each asset's growth by its initial weight models buy-and-hold.
    asset_growth = (1 + evaluation[weights.index]).cumprod()
    portfolio_growth = asset_growth @ weights
    realized = portfolio_growth.div(portfolio_growth.shift(fill_value=1.0)) - 1
    realized[BENCHMARK] = evaluation[BENCHMARK]
    metrics = pd.DataFrame(
        {name: research.historical_metrics(realized[name]) for name in realized}
    ).loc[["CAGR", "Annual volatility", "Max drawdown"]]
    return DemoResult(
        seed, fit.index[0], fit.index[-1], evaluation.index[0], evaluation.index[-1],
        weights, metrics,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="nonnegative random seed")
    args = parser.parse_args()
    if args.seed < 0:
        parser.error("--seed must be nonnegative")
    result = run_demo(args.seed)
    print(f"SYNTHETIC DATA ONLY | seed {result.seed}")
    print(f"Fit: {result.fit_start.date()} to {result.fit_end.date()} ({FIT_ROWS} daily returns)")
    print(f"Evaluation: {result.evaluation_start.date()} to {result.evaluation_end.date()}")
    print("\nInitial portfolio weights")
    print(result.weights.to_string(float_format="{:.1%}".format))
    print("\nLater-period metrics (hypothetical, before costs)")
    print(result.metrics.to_string(float_format="{:.2%}".format))


if __name__ == "__main__":
    main()
