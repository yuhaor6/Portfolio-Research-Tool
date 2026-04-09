"""simulation/bootstrap.py — Block bootstrap Monte Carlo simulation engine."""

import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SIMULATION_CONFIG, CLIENT_PROFILE


def block_bootstrap_mc(
    returns_df: pd.DataFrame,
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int | None = None,
    block_size: int = 12,
    inflation: float = 0.025,
    horizon_years: int = 10,
    rebalance: str = "annual",
    initial_wealth: float | None = None,
    seed: int = 42,
) -> dict:
    """
    Block-bootstrap Monte Carlo simulation.

    Resamples contiguous `block_size`-month blocks of historical returns
    to generate realistic paths that preserve autocorrelation and
    cross-sectional dependence structure.

    Parameters
    ----------
    returns_df : pd.DataFrame
        Historical monthly returns. Rows with any NaN are dropped.
    weights : np.ndarray, shape (n_assets,)
        Portfolio weights (must sum to 1).
    contributions : np.ndarray, shape (horizon_months,)
        Monthly nominal investment contributions.
    n_paths : int
        Number of simulation paths.
    block_size : int
        Length of each resampled block in months.
    inflation : float
        Annual inflation rate for deflating terminal wealth to real terms.
    horizon_years : int
        Investment horizon.
    rebalance : str
        'none', 'quarterly', 'semi-annual', or 'annual'.
    initial_wealth : float
        Starting portfolio value.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with keys:
        paths           : np.ndarray (n_paths, horizon_months) nominal wealth
        real_paths      : np.ndarray (n_paths, horizon_months) inflation-adjusted
        terminal_wealth : np.ndarray (n_paths,) nominal
        real_terminal   : np.ndarray (n_paths,) real
        weights_used    : np.ndarray
        metadata        : dict
    """
    if n_paths is None:
        n_paths = SIMULATION_CONFIG["n_paths"]
    if initial_wealth is None:
        initial_wealth = CLIENT_PROFILE["initial_investment"]

    horizon_months = horizon_years * 12
    clean = returns_df.dropna()
    n_assets = returns_df.shape[1]
    w = np.array(weights, dtype=float)
    w = w / w.sum()

    # Map to clean data columns by position (assume same order)
    asset_cols = list(returns_df.columns)
    clean_arr = clean[asset_cols].values  # shape: (T, n_assets)
    T = len(clean_arr)

    # Rebalance schedule: month indices at which to rebalance
    if rebalance == "none":
        rebal_months = set()
    elif rebalance == "quarterly":
        rebal_months = set(range(2, horizon_months, 3))
    elif rebalance == "semi-annual":
        rebal_months = set(range(5, horizon_months, 6))
    else:  # annual
        rebal_months = set(range(11, horizon_months, 12))

    rng = np.random.default_rng(seed)
    paths = np.zeros((n_paths, horizon_months), dtype=np.float64)

    # Inflation deflator: monthly inflation
    monthly_inflation = (1 + inflation) ** (1 / 12)
    deflators = monthly_inflation ** np.arange(1, horizon_months + 1)

    for i in range(n_paths):
        wealth = initial_wealth
        current_weights = w.copy()

        for t in range(horizon_months):
            # Draw a random block
            block_start = rng.integers(0, T - block_size)
            block = clean_arr[block_start: block_start + block_size]
            month_return = block[t % block_size]  # one month from the block

            # Portfolio return for this month
            port_ret = float(current_weights @ month_return)
            wealth = wealth * (1 + port_ret) + contributions[t]

            # Rebalance if due
            if t in rebal_months:
                current_weights = w.copy()

            paths[i, t] = wealth

    real_paths = paths / deflators[np.newaxis, :]
    terminal_wealth = paths[:, -1]
    real_terminal = real_paths[:, -1]

    return {
        "paths":           paths,
        "real_paths":      real_paths,
        "terminal_wealth": terminal_wealth,
        "real_terminal":   real_terminal,
        "weights_used":    w,
        "metadata": {
            "method":       "block_bootstrap",
            "n_paths":      n_paths,
            "block_size":   block_size,
            "horizon_years": horizon_years,
            "rebalance":    rebalance,
            "inflation":    inflation,
        },
    }


if __name__ == "__main__":
    import time
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.fetcher import fetch_returns
    from client.cashflows import generate_savings_schedule, monthly_contributions
    from config import UNIVERSE_12, DATE_RANGE_12, RF_TICKER

    ret = fetch_returns(tickers=UNIVERSE_12, start=DATE_RANGE_12["start"], end="2025-12-31")
    sched = generate_savings_schedule()
    contrib = monthly_contributions(sched)

    # Equal-weight for quick test
    n = len(UNIVERSE_12)
    w = np.ones(n) / n

    print(f"Running 1,000-path block bootstrap...")
    t0 = time.time()
    result = block_bootstrap_mc(ret, w, contrib, n_paths=1000)
    elapsed = time.time() - t0

    tw = result["real_terminal"]
    print(f"Elapsed: {elapsed:.2f}s  |  paths: {result['paths'].shape}")
    print(f"Terminal wealth (real) quantiles:")
    for p in [5, 25, 50, 75, 95]:
        print(f"  P{p:2d}: ${np.percentile(tw, p):,.0f}")
