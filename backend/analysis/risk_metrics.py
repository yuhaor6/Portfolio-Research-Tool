"""analysis/risk_metrics.py — Portfolio risk and performance metrics."""

import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def compute_all_metrics(
    paths: np.ndarray,
    terminal_wealth: np.ndarray,
    goal: float,
    rf_rate: float = 0.04,
    horizon_years: int = 10,
    trading_periods: int = 12,
) -> dict:
    """
    Compute the full suite of risk and performance metrics from simulation output.

    Parameters
    ----------
    paths : np.ndarray (n_paths, horizon_months) — real (inflation-adjusted) paths
    terminal_wealth : np.ndarray (n_paths,) — real terminal wealth
    goal : float — target terminal wealth in real terms
    rf_rate : float — annualized risk-free rate
    horizon_years : int

    Returns
    -------
    dict of scalar metrics
    """
    horizon_months = paths.shape[1]
    n_paths = paths.shape[0]

    # Compute path returns (annualized)
    initial = paths[:, 0]  # Approximate: first month value
    final   = terminal_wealth
    with np.errstate(divide="ignore", invalid="ignore"):
        ann_returns = ((final / np.maximum(initial, 1e-10)) ** (1 / horizon_years)) - 1

    mean_ret   = float(np.nanmean(ann_returns))
    median_ret = float(np.nanmedian(ann_returns))
    vol        = float(np.nanstd(ann_returns))

    # Sharpe and Sortino (using distributional returns)
    excess = ann_returns - rf_rate
    sharpe  = float(np.nanmean(excess) / np.nanstd(excess)) if vol > 0 else 0.0
    downside = ann_returns[ann_returns < rf_rate] - rf_rate
    sortino_denom = float(np.sqrt(np.mean(downside ** 2))) if len(downside) > 0 else 0.0
    sortino = float(np.nanmean(excess) / sortino_denom) if sortino_denom > 0 else 0.0

    # Max drawdown — computed on median path
    median_path = np.median(paths, axis=0)
    running_max = np.maximum.accumulate(median_path)
    drawdown_series = (median_path - running_max) / np.maximum(running_max, 1e-10)
    max_dd = float(drawdown_series.min())

    # Max drawdown at 5th percentile path (worst-case perspective)
    p5_path = np.percentile(paths, 5, axis=0)
    running_max_p5 = np.maximum.accumulate(p5_path)
    dd_p5 = (p5_path - running_max_p5) / np.maximum(running_max_p5, 1e-10)
    max_dd_p5 = float(dd_p5.min())

    # Calmar ratio
    calmar = mean_ret / abs(max_dd) if max_dd != 0 else 0.0

    # VaR and CVaR (5%) on terminal wealth
    var_5  = float(np.percentile(terminal_wealth, 5))
    cvar_5 = float(terminal_wealth[terminal_wealth <= var_5].mean()) if (terminal_wealth <= var_5).any() else var_5

    # Goal attainment probability
    p_goal = float((terminal_wealth >= goal).mean())

    # Terminal wealth quantiles
    quantiles = {
        "p5":  float(np.percentile(terminal_wealth, 5)),
        "p25": float(np.percentile(terminal_wealth, 25)),
        "p50": float(np.percentile(terminal_wealth, 50)),
        "p75": float(np.percentile(terminal_wealth, 75)),
        "p95": float(np.percentile(terminal_wealth, 95)),
    }

    return {
        "sharpe":            sharpe,
        "sortino":           sortino,
        "calmar":            calmar,
        "mean_ann_return":   mean_ret,
        "median_ann_return": median_ret,
        "ann_vol":           vol,
        "max_drawdown_median": max_dd,
        "max_drawdown_p5":   max_dd_p5,
        "var_5":             var_5,
        "cvar_5":            cvar_5,
        "p_goal":            p_goal,
        "mean_terminal":     float(np.mean(terminal_wealth)),
        "median_terminal":   float(np.median(terminal_wealth)),
        **quantiles,
    }


def drawdown_series(paths: np.ndarray, percentile: float = 50) -> np.ndarray:
    """Return the drawdown time series for the path at a given percentile."""
    path = np.percentile(paths, percentile, axis=0)
    running_max = np.maximum.accumulate(path)
    return (path - running_max) / np.maximum(running_max, 1e-10)


if __name__ == "__main__":
    np.random.seed(42)
    fake_paths = np.cumprod(1 + np.random.normal(0.007, 0.04, (1000, 120)), axis=1) * 10000
    tw = fake_paths[:, -1]
    metrics = compute_all_metrics(fake_paths, tw, goal=1_000_000)
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
