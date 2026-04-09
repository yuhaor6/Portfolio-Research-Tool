import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import UNIVERSE_12, RF_TICKER, CLIENT_PROFILE, SIMULATION_CONFIG


def sweep_estimation_window(
    returns_df: pd.DataFrame,
    contributions: np.ndarray,
    windows: list[tuple[str, str]] | None = None,
    n_paths: int = 2000,
    goal: float | None = None,
) -> pd.DataFrame:
    """
    Re-run tangency 12-asset simulation for different estimation windows.

    Parameters
    ----------
    windows : list of (start_date, end_date) tuples
    """
    from models.portfolio_stats import compute_stats, compute_covariance
    from models.efficient_frontier import tangency_portfolio
    from simulation.bootstrap import block_bootstrap_mc
    from analysis.risk_metrics import compute_all_metrics

    if windows is None:
        windows = [
            ("2005-01-01", "2025-12-31"),
            ("2010-01-01", "2025-12-31"),
            ("2015-01-01", "2025-12-31"),
            ("2017-01-01", "2025-12-31"),
        ]

    if goal is None:
        goal = CLIENT_PROFILE["goal_amount"]

    records = []
    for start, end in windows:
        tickers = [t for t in UNIVERSE_12 if t in returns_df.columns]
        ret = returns_df[tickers].loc[start:end].dropna()
        if len(ret) < 24:
            continue

        stats = compute_stats(ret)
        cov = compute_covariance(ret)
        mu = stats["ann_return"].values
        rf = stats.loc[RF_TICKER, "ann_return"] if RF_TICKER in stats.index else 0.04

        crypto_idx = [tickers.index(t) for t in ["BTC-USD", "ETH-USD"] if t in tickers]
        tang = tangency_portfolio(mu, cov, rf, crypto_indices=crypto_idx or None)

        result = block_bootstrap_mc(
            returns_df=ret,
            weights=tang["weights"],
            contributions=contributions,
            n_paths=n_paths,
        )
        metrics = compute_all_metrics(result["real_paths"], result["real_terminal"], goal=goal)
        metrics["window"] = f"{start[:4]}–{end[:4]}"
        metrics["tangency_sharpe"] = tang["sharpe"]
        records.append(metrics)

    return pd.DataFrame(records)


def sweep_crypto_cap(
    returns_df: pd.DataFrame,
    contributions: np.ndarray,
    caps: list[float] | None = None,
    n_paths: int = 2000,
    goal: float | None = None,
) -> pd.DataFrame:
    """Sweep maximum crypto allocation constraint."""
    from models.portfolio_stats import compute_stats, compute_covariance
    from models.efficient_frontier import tangency_portfolio
    from simulation.bootstrap import block_bootstrap_mc
    from analysis.risk_metrics import compute_all_metrics

    if caps is None:
        caps = [0.0, 0.02, 0.05, 0.10]
    if goal is None:
        goal = CLIENT_PROFILE["goal_amount"]

    tickers = [t for t in UNIVERSE_12 if t in returns_df.columns]
    ret = returns_df[tickers].dropna()
    stats = compute_stats(ret)
    cov = compute_covariance(ret)
    mu = stats["ann_return"].values
    rf = stats.loc[RF_TICKER, "ann_return"] if RF_TICKER in stats.index else 0.04
    crypto_idx = [tickers.index(t) for t in ["BTC-USD", "ETH-USD"] if t in tickers]

    records = []
    for cap in caps:
        tang = tangency_portfolio(mu, cov, rf, crypto_indices=crypto_idx or None, max_crypto=cap)
        result = block_bootstrap_mc(ret, tang["weights"], contributions, n_paths=n_paths)
        metrics = compute_all_metrics(result["real_paths"], result["real_terminal"], goal=goal)
        metrics["crypto_cap"] = cap
        metrics["crypto_alloc"] = float(tang["weights"][crypto_idx].sum()) if crypto_idx else 0.0
        metrics["tangency_sharpe"] = tang["sharpe"]
        records.append(metrics)

    return pd.DataFrame(records)


def sweep_rebalancing(
    returns_df: pd.DataFrame,
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int = 2000,
    goal: float | None = None,
) -> pd.DataFrame:
    """Sweep rebalancing frequency."""
    from simulation.bootstrap import block_bootstrap_mc
    from analysis.risk_metrics import compute_all_metrics

    if goal is None:
        goal = CLIENT_PROFILE["goal_amount"]

    records = []
    for freq in ["none", "quarterly", "semi-annual", "annual"]:
        result = block_bootstrap_mc(
            returns_df=returns_df,
            weights=weights,
            contributions=contributions,
            n_paths=n_paths,
            rebalance=freq,
        )
        metrics = compute_all_metrics(result["real_paths"], result["real_terminal"], goal=goal)
        metrics["rebalance_freq"] = freq
        records.append(metrics)

    return pd.DataFrame(records)
