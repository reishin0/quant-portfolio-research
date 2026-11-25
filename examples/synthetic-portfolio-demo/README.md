# Portfolio Construction: Synthetic Data Demo

Compare an equal-weight portfolio, minimum-variance allocation, Black-Litterman
maximum-Sharpe allocation, and minimum-tracking-error allocation on the same
fictional prices. No credentials, downloads, or data files are used by the demo.

## Run the demo

From the repository root, activate a Python 3.11-3.13 environment and run:

```sh
python -m pip install -r examples/synthetic-portfolio-demo/requirements.txt
python examples/synthetic-portfolio-demo/demo.py
```

Dependency installation may need an internet connection. Once the dependencies
are installed, the demo runs offline. Use `--seed 7` to try another generated
scenario. The default seed is 42. The script prints its results without writing
reports or datasets. For the notebook version, open `start_here.ipynb` from this folder in
an existing Jupyter environment with the same dependencies installed.

## Read the output

1. The seeded generator makes eight fictional assets and a fictional benchmark.
   Dates are weekday labels, not a market calendar.
2. The first 504 daily returns are used to estimate covariance and fit weights.
   In the Black-Litterman example, a hypothetical view says Asset A will
   outperform Asset B by four percentage points per year. The confidence input
   is an assumption, not an estimated probability of being correct.
3. Each allocation starts the later period fully invested and long-only.
   Optimized allocations start with at most 35% in any one asset. Weights then
   drift with returns; there is no rebalancing or trading-cost model.
4. Compare annualized compound return, annualized volatility, and maximum
   drawdown. The benchmark column in the metrics table uses the same later
   period. Maximum drawdown includes the initial portfolio value.

This example reuses the repository's calculation functions, not its historical
inputs or research protocols. The later synthetic period is a software example,
not validation of a market strategy. None of the results are investment advice.

To check repeatability, allocation constraints, and the fit/evaluation split:

```sh
python -m unittest discover -s examples/synthetic-portfolio-demo -p "test_demo.py"
```
