"""models/efficient_frontier.py — Mean-variance optimization and efficient frontier."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import OPT_CONSTRAINTS


def _portfolio_perf(weights: np.ndarray, mu: np.ndarray, cov: np.ndarray):
    """Return (annualized_return, annualized_vol) for given weights."""
    ret = float(weights @ mu)
    vol = float(np.sqrt(weights @ cov @ weights))
    return ret, vol


def tangency_portfolio(
    mu: np.ndarray,
    cov: np.ndarray,
    rf: float,
    bounds: list[tuple] | None = None,
    crypto_indices: list[int] | None = None,
    max_crypto: float = 0.05,
) -> dict:
    """
    Maximize Sharpe ratio (tangency portfolio).

    Parameters
    ----------
    mu : np.ndarray  shape (n,)  annualized expected returns
    cov : np.ndarray shape (n,n) annualized covariance matrix
    rf : float       annualized risk-free rate
    bounds : list of (min, max) per asset. Defaults to (0, 1) — long-only.
    crypto_indices : list of int
        Column indices of crypto assets; capped at max_crypto total.
    max_crypto : float
        Maximum total allocation to crypto assets.

    Returns
    -------
    dict with keys: weights, sharpe, ann_return, ann_vol
    """
    n = len(mu)
    if bounds is None:
        bounds = [(OPT_CONSTRAINTS["min_weight"], OPT_CONSTRAINTS["max_weight"])] * n

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if crypto_indices:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, ci=crypto_indices: max_crypto - np.sum(w[ci]),
        })

    def neg_sharpe(w):
        r, v = _portfolio_perf(w, mu, cov)
        return -(r - rf) / v if v > 1e-10 else 1e6

    best_result = None
    best_sharpe = -np.inf

    # Multiple random starts to avoid local minima
    rng = np.random.default_rng(42)
    for _ in range(20):
        w0 = rng.dirichlet(np.ones(n))
        res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds,
                       constraints=constraints,
                       options={"ftol": 1e-12, "maxiter": 1000})
        if res.success and -res.fun > best_sharpe:
            best_sharpe = -res.fun
            best_result = res

    if best_result is None:
        raise RuntimeError("Tangency portfolio optimization failed.")

    w = best_result.x
    w = np.clip(w, 0, 1)
    w /= w.sum()
    ret, vol = _portfolio_perf(w, mu, cov)
    return {
        "weights": w,
        "sharpe":  (ret - rf) / vol,
        "ann_return": ret,
        "ann_vol":    vol,
    }


def minimum_variance_portfolio(
    cov: np.ndarray,
    bounds: list[tuple] | None = None,
) -> dict:
    """Portfolio with minimum variance (ignores return)."""
    n = cov.shape[0]
    if bounds is None:
        bounds = [(0.0, 1.0)] * n

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def portfolio_var(w):
        return float(w @ cov @ w)

    w0 = np.ones(n) / n
    res = minimize(portfolio_var, w0, method="SLSQP", bounds=bounds,
                   constraints=constraints, options={"ftol": 1e-12})
    w = np.clip(res.x, 0, 1)
    w /= w.sum()
    return {"weights": w, "ann_vol": float(np.sqrt(w @ cov @ w))}


def efficient_frontier(
    mu: np.ndarray,
    cov: np.ndarray,
    rf: float,
    n_points: int = 100,
    bounds: list[tuple] | None = None,
    crypto_indices: list[int] | None = None,
    max_crypto: float = 0.05,
) -> list[dict]:
    """
    Trace the efficient frontier by minimizing volatility at target return levels.

    Returns
    -------
    list of dicts: [{vol, return, weights, sharpe}, ...]  sorted by vol ascending.
    """
    n = len(mu)
    if bounds is None:
        bounds = [(0.0, 1.0)] * n

    # Determine return range from min-variance to max-return feasible portfolios
    mv = minimum_variance_portfolio(cov, bounds)
    mv_ret = float(mv["weights"] @ mu)
    max_ret = float(np.max(mu))  # upper bound: 100% in highest-return asset

    target_returns = np.linspace(mv_ret, max_ret * 0.99, n_points)

    frontier_points = []
    rng = np.random.default_rng(0)

    for target in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target: float(w @ mu) - t},
        ]
        if crypto_indices:
            constraints.append({
                "type": "ineq",
                "fun": lambda w, ci=crypto_indices: max_crypto - np.sum(w[ci]),
            })

        def port_vol(w):
            return float(np.sqrt(w @ cov @ w))

        best_res = None
        best_vol = np.inf
        for _ in range(5):
            w0 = rng.dirichlet(np.ones(n))
            res = minimize(port_vol, w0, method="SLSQP", bounds=bounds,
                           constraints=constraints,
                           options={"ftol": 1e-12, "maxiter": 500})
            if res.success and res.fun < best_vol:
                best_vol = res.fun
                best_res = res

        if best_res is not None:
            w = np.clip(best_res.x, 0, 1)
            w /= w.sum()
            ret, vol = _portfolio_perf(w, mu, cov)
            frontier_points.append({
                "ann_vol":    vol,
                "ann_return": ret,
                "sharpe":     (ret - rf) / vol if vol > 0 else 0.0,
                "weights":    w.tolist(),
            })

    frontier_points.sort(key=lambda x: x["ann_vol"])
    return frontier_points


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.fetcher import fetch_returns
    from models.portfolio_stats import compute_stats, compute_covariance
    from config import UNIVERSE_3, UNIVERSE_5, UNIVERSE_12, DATE_RANGE_12, RF_TICKER

    for universe_name, tickers in [("3-asset", UNIVERSE_3), ("5-asset", UNIVERSE_5), ("12-asset", UNIVERSE_12)]:
        start = "2017-01-01" if universe_name == "12-asset" else "2013-01-01"
        ret = fetch_returns(tickers=tickers, start=start, end="2025-12-31")
        stats = compute_stats(ret)
        cov = compute_covariance(ret)
        mu = stats["ann_return"].values
        rf = stats.loc[RF_TICKER, "ann_return"] if RF_TICKER in stats.index else 0.04

        crypto_idx = [tickers.index(t) for t in ["BTC-USD", "ETH-USD"] if t in tickers]
        tang = tangency_portfolio(mu, cov, rf, crypto_indices=crypto_idx or None)

        print(f"\n=== Tangency Portfolio ({universe_name}) ===")
        print(f"  Sharpe: {tang['sharpe']:.4f}")
        print(f"  Return: {tang['ann_return']:.2%}")
        print(f"  Vol:    {tang['ann_vol']:.2%}")
        print("  Weights:")
        for t, w in zip(tickers, tang["weights"]):
            if w > 0.001:
                print(f"    {t:10s}: {w:.3f}")
