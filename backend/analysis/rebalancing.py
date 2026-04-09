import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CLIENT_PROFILE


def compare_rebalancing_frequencies(
    returns_df: pd.DataFrame,
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int = 5000,
    goal: float | None = None,
) -> pd.DataFrame:
    """
    Compare bootstrap simulation outcomes across rebalancing frequencies.

    Returns a DataFrame with one row per frequency and columns for key metrics.
    """
    from simulation.bootstrap import block_bootstrap_mc
    from analysis.risk_metrics import compute_all_metrics

    if goal is None:
        goal = CLIENT_PROFILE["goal_amount"]

    freqs = ["none", "quarterly", "semi-annual", "annual"]
    records = []

    for freq in freqs:
        result = block_bootstrap_mc(
            returns_df=returns_df,
            weights=weights,
            contributions=contributions,
            n_paths=n_paths,
            rebalance=freq,
        )
        metrics = compute_all_metrics(
            result["real_paths"],
            result["real_terminal"],
            goal=goal,
        )
        metrics["rebalance"] = freq
        records.append(metrics)

    df = pd.DataFrame(records).set_index("rebalance")
    return df[["p_goal", "median_terminal", "p5", "p95", "sharpe", "max_drawdown_median"]]
