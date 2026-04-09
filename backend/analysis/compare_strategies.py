import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    UNIVERSE_3, UNIVERSE_5, UNIVERSE_12, RF_TICKER,
    DATE_RANGE_12, CLIENT_PROFILE, SIMULATION_CONFIG
)


STRATEGY_DEFINITIONS = {
    "all_cash": {
        "label": "All Cash (100% SHV)",
        "tickers": ["SHV"],
        "weights": [1.0],
        "description": "100% short-term Treasury — baseline risk-free benchmark",
    },
    "all_equity": {
        "label": "All Equity (100% IVV)",
        "tickers": UNIVERSE_12,
        "weights_fn": lambda tickers, mu, cov, rf: _single_asset_weights(tickers, "IVV"),
        "description": "100% S&P 500 — high-risk equity benchmark",
    },
    "60_40": {
        "label": "60/40 IVV/AGG",
        "tickers": UNIVERSE_12,
        "weights_fn": lambda tickers, mu, cov, rf: _fixed_weights(tickers, {"IVV": 0.6, "AGG": 0.4}),
        "description": "Classic 60/40 balanced portfolio",
    },
    "equal_weight": {
        "label": "Equal Weight 12-asset",
        "tickers": UNIVERSE_12,
        "weights_fn": lambda tickers, mu, cov, rf: np.ones(len(tickers)) / len(tickers),
        "description": "1/N equal-weight allocation",
    },
    "risk_parity": {
        "label": "Risk Parity 12-asset",
        "tickers": UNIVERSE_12,
        "weights_fn": lambda tickers, mu, cov, rf: _risk_parity_weights(np.sqrt(np.diag(cov))),
        "description": "Inverse-vol weighting (risk parity proxy)",
    },
    "tangency_3": {
        "label": "Tangency 3-asset",
        "tickers": UNIVERSE_3,
        "weights_fn": "tangency",
        "universe": "3",
        "description": "MV-optimal: IVV, AGG, SHV",
    },
    "tangency_5": {
        "label": "Tangency 5-asset",
        "tickers": UNIVERSE_5,
        "weights_fn": "tangency",
        "universe": "5",
        "description": "MV-optimal: adds QUAL and USMV",
    },
    "tangency_12": {
        "label": "Tangency 12-asset",
        "tickers": UNIVERSE_12,
        "weights_fn": "tangency",
        "universe": "12",
        "description": "MV-optimal: full 12-asset universe (crypto ≤ 5%)",
    },
    "tangency_12_glide": {
        "label": "Tangency 12-asset + Glide Path",
        "tickers": UNIVERSE_12,
        "weights_fn": "tangency_glide",
        "universe": "12",
        "description": "Starts at tangency, glides toward bonds over 10 years",
    },
}


def _single_asset_weights(tickers: list[str], target: str) -> np.ndarray:
    w = np.zeros(len(tickers))
    if target in tickers:
        w[tickers.index(target)] = 1.0
    return w


def _fixed_weights(tickers: list[str], weight_map: dict) -> np.ndarray:
    w = np.zeros(len(tickers))
    for t, wt in weight_map.items():
        if t in tickers:
            w[tickers.index(t)] = wt
    return w / w.sum()


def _risk_parity_weights(vols: np.ndarray) -> np.ndarray:
    inv_vol = 1.0 / np.maximum(vols, 1e-8)
    return inv_vol / inv_vol.sum()


def _compute_tangency_weights(
    returns_df: pd.DataFrame,
    tickers: list[str],
) -> np.ndarray:
    from models.portfolio_stats import compute_stats, compute_covariance
    from models.efficient_frontier import tangency_portfolio

    ret = returns_df[tickers].dropna()
    stats = compute_stats(ret)
    cov = compute_covariance(ret)
    mu = stats["ann_return"].values
    rf = stats.loc[RF_TICKER, "ann_return"] if RF_TICKER in stats.index else 0.04

    crypto_idx = [tickers.index(t) for t in ["BTC-USD", "ETH-USD"] if t in tickers]
    tang = tangency_portfolio(mu, cov, rf, crypto_indices=crypto_idx or None)
    return tang["weights"]


def build_strategy_weights(
    returns_df: pd.DataFrame,
    strategy_key: str,
) -> tuple[list[str], np.ndarray]:
    """
    Resolve weights for a given strategy key.

    Returns (tickers, weights_array).
    """
    defn = STRATEGY_DEFINITIONS[strategy_key]
    tickers = defn["tickers"]

    weights_fn = defn.get("weights_fn")
    if weights_fn == "tangency" or weights_fn == "tangency_glide":
        # Need to compute tangency on the available data
        w = _compute_tangency_weights(returns_df, tickers)
    elif callable(weights_fn):
        # Need mu, cov for those that require it
        from models.portfolio_stats import compute_stats, compute_covariance
        ret = returns_df[tickers].dropna()
        stats = compute_stats(ret)
        cov = compute_covariance(ret)
        mu = stats["ann_return"].values
        rf = stats.loc[RF_TICKER, "ann_return"] if RF_TICKER in stats.index else 0.04
        w = weights_fn(tickers, mu, cov, rf)
    else:
        w = np.array(defn.get("weights", []))

    return tickers, w


def run_all_strategies(
    returns_df: pd.DataFrame,
    contributions: np.ndarray,
    simulation_mode: str = "bootstrap",
    n_paths: int | None = None,
    goal: float | None = None,
    rf_rate: float = 0.04,
    horizon_years: int = 10,
    **sim_kwargs,
) -> pd.DataFrame:
    """
    Run all strategies through simulation and collect metrics.

    Returns
    -------
    pd.DataFrame indexed by strategy_key, columns = metric names.
    """
    from simulation.engine import run_simulation
    from analysis.risk_metrics import compute_all_metrics

    if n_paths is None:
        n_paths = SIMULATION_CONFIG["n_paths_dev"]
    if goal is None:
        goal = CLIENT_PROFILE["goal_amount"]

    records = []
    for key, defn in STRATEGY_DEFINITIONS.items():
        print(f"  Strategy: {defn['label']}...")
        tickers, w = build_strategy_weights(returns_df, key)

        # Get the subset of returns for this strategy
        available = [t for t in tickers if t in returns_df.columns]
        w_map = dict(zip(tickers, w))
        w_sub = np.array([w_map[t] for t in available])
        if w_sub.sum() > 0:
            w_sub /= w_sub.sum()
        ret_sub = returns_df[available]

        try:
            result = run_simulation(
                mode=simulation_mode,
                weights=w_sub,
                contributions=contributions,
                n_paths=n_paths,
                horizon_years=horizon_years,
                returns_df=ret_sub if simulation_mode == "bootstrap" else None,
                **sim_kwargs,
            )
            metrics = compute_all_metrics(
                result.real_paths,
                result.real_terminal,
                goal=goal,
                rf_rate=rf_rate,
                horizon_years=horizon_years,
            )
            metrics["strategy"]    = key
            metrics["label"]       = defn["label"]
            metrics["description"] = defn["description"]
            records.append(metrics)
        except Exception as exc:
            print(f"    ERROR for {key}: {exc}")

    return pd.DataFrame(records).set_index("strategy")
