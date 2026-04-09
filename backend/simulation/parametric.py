import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SIMULATION_CONFIG, CLIENT_PROFILE


def _run_paths(
    monthly_returns_sampler,
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int,
    horizon_months: int,
    rebalance: str,
    initial_wealth: float,
    inflation: float,
) -> dict:
    """Shared simulation loop: advance wealth paths given a return sampler."""
    w = np.array(weights)
    w = w / w.sum()

    if rebalance == "none":
        rebal_months = set()
    elif rebalance == "quarterly":
        rebal_months = set(range(2, horizon_months, 3))
    elif rebalance == "semi-annual":
        rebal_months = set(range(5, horizon_months, 6))
    else:
        rebal_months = set(range(11, horizon_months, 12))

    paths = np.zeros((n_paths, horizon_months))
    monthly_inflation = (1 + inflation) ** (1 / 12)
    deflators = monthly_inflation ** np.arange(1, horizon_months + 1)

    for i in range(n_paths):
        wealth = initial_wealth
        current_w = w.copy()
        for t in range(horizon_months):
            month_ret = monthly_returns_sampler(t)
            port_ret = float(current_w @ month_ret)
            wealth = wealth * (1 + port_ret) + contributions[t]
            if t in rebal_months:
                current_w = w.copy()
            paths[i, t] = wealth

    real_paths = paths / deflators[np.newaxis, :]
    return {
        "paths":           paths,
        "real_paths":      real_paths,
        "terminal_wealth": paths[:, -1],
        "real_terminal":   real_paths[:, -1],
        "weights_used":    w,
    }


def parametric_mc(
    mu: np.ndarray,
    cov: np.ndarray,
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int | None = None,
    horizon_years: int = 10,
    rebalance: str = "annual",
    initial_wealth: float | None = None,
    inflation: float = 0.025,
    seed: int = 42,
) -> dict:
    """
    Parametric (multivariate normal) Monte Carlo.

    Parameters
    ----------
    mu  : np.ndarray  annualized expected returns
    cov : np.ndarray  annualized covariance matrix
    """
    if n_paths is None:
        n_paths = SIMULATION_CONFIG["n_paths"]
    if initial_wealth is None:
        initial_wealth = CLIENT_PROFILE["initial_investment"]

    horizon_months = horizon_years * 12
    mu_monthly  = mu / 12
    cov_monthly = cov / 12

    rng = np.random.default_rng(seed)
    # Pre-sample all returns at once for vectorized speed
    all_returns = rng.multivariate_normal(mu_monthly, cov_monthly,
                                          size=(n_paths, horizon_months))
    # all_returns shape: (n_paths, horizon_months, n_assets)

    w = np.array(weights) / np.sum(weights)

    if rebalance == "none":
        rebal_months = set()
    elif rebalance == "quarterly":
        rebal_months = set(range(2, horizon_months, 3))
    elif rebalance == "semi-annual":
        rebal_months = set(range(5, horizon_months, 6))
    else:
        rebal_months = set(range(11, horizon_months, 12))

    monthly_inflation = (1 + inflation) ** (1 / 12)
    deflators = monthly_inflation ** np.arange(1, horizon_months + 1)

    # Vectorized over paths
    port_returns = all_returns @ w  # (n_paths, horizon_months)

    paths = np.zeros((n_paths, horizon_months))
    wealth = np.full(n_paths, float(initial_wealth))
    for t in range(horizon_months):
        wealth = wealth * (1 + port_returns[:, t]) + contributions[t]
        paths[:, t] = wealth

    real_paths = paths / deflators[np.newaxis, :]
    return {
        "paths":           paths,
        "real_paths":      real_paths,
        "terminal_wealth": paths[:, -1],
        "real_terminal":   real_paths[:, -1],
        "weights_used":    w,
        "metadata": {
            "method":       "parametric_normal",
            "n_paths":      n_paths,
            "horizon_years": horizon_years,
            "rebalance":    rebalance,
        },
    }


def regime_mc(
    regime_summary: dict,
    regime_cov_matrices: dict,
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int | None = None,
    horizon_years: int = 10,
    rebalance: str = "annual",
    initial_wealth: float | None = None,
    inflation: float = 0.025,
    seed: int = 42,
) -> dict:
    """
    Regime-conditional Markov-chain Monte Carlo.

    The Markov chain drives the regime at each step; returns are drawn from
    the regime-specific (mu, cov) distribution.

    Parameters
    ----------
    regime_summary   : output from models.regime_model.get_regime_summary()
    regime_cov_matrices : {regime_id: {"mean": np.ndarray, "cov": np.ndarray}}
    """
    if n_paths is None:
        n_paths = SIMULATION_CONFIG["n_paths"]
    if initial_wealth is None:
        initial_wealth = CLIENT_PROFILE["initial_investment"]

    horizon_months = horizon_years * 12
    trans = np.array(regime_summary["transition_matrix"])
    n_regimes = regime_summary["n_regimes"]
    current_regime = regime_summary["current_regime"]

    # Monthly mu/cov from annualized stats
    regime_params = {}
    for i in range(n_regimes):
        if i in regime_cov_matrices:
            regime_params[i] = {
                "mu":  regime_cov_matrices[i]["mean"] / 12,
                "cov": regime_cov_matrices[i]["cov"]  / 12,
            }

    w = np.array(weights) / np.sum(weights)
    monthly_inflation = (1 + inflation) ** (1 / 12)
    deflators = monthly_inflation ** np.arange(1, horizon_months + 1)

    if rebalance == "none":
        rebal_months = set()
    elif rebalance == "quarterly":
        rebal_months = set(range(2, horizon_months, 3))
    elif rebalance == "semi-annual":
        rebal_months = set(range(5, horizon_months, 6))
    else:
        rebal_months = set(range(11, horizon_months, 12))

    rng = np.random.default_rng(seed)
    paths = np.zeros((n_paths, horizon_months))
    regime_paths = np.zeros((n_paths, horizon_months), dtype=int)

    for i in range(n_paths):
        wealth = float(initial_wealth)
        regime = current_regime
        current_w = w.copy()

        for t in range(horizon_months):
            # Transition regime
            regime = rng.choice(n_regimes, p=trans[:, regime])
            regime_paths[i, t] = regime

            # Draw return from regime-specific distribution
            params = regime_params.get(regime, regime_params[0])
            month_ret = rng.multivariate_normal(params["mu"], params["cov"])

            port_ret = float(current_w @ month_ret)
            wealth = wealth * (1 + port_ret) + contributions[t]

            if t in rebal_months:
                current_w = w.copy()
            paths[i, t] = wealth

    real_paths = paths / deflators[np.newaxis, :]
    return {
        "paths":           paths,
        "real_paths":      real_paths,
        "terminal_wealth": paths[:, -1],
        "real_terminal":   real_paths[:, -1],
        "regime_paths":    regime_paths,
        "weights_used":    w,
        "metadata": {
            "method":       "regime_conditional",
            "n_paths":      n_paths,
            "horizon_years": horizon_years,
        },
    }


def garch_mc(
    garch_results: dict,
    correlation_matrix: np.ndarray,
    weights: np.ndarray,
    contributions: np.ndarray,
    tickers: list[str],
    n_paths: int | None = None,
    horizon_years: int = 10,
    rebalance: str = "annual",
    initial_wealth: float | None = None,
    inflation: float = 0.025,
    seed: int = 42,
) -> dict:
    """
    GARCH-filtered Monte Carlo.
    Simulates GARCH(1,1) process forward for each asset and applies
    a static correlation structure to generate correlated returns.
    """
    if n_paths is None:
        n_paths = SIMULATION_CONFIG["n_paths"]
    if initial_wealth is None:
        initial_wealth = CLIENT_PROFILE["initial_investment"]

    horizon_months = horizon_years * 12
    n_assets = len(tickers)
    w = np.array(weights) / np.sum(weights)
    monthly_inflation = (1 + inflation) ** (1 / 12)
    deflators = monthly_inflation ** np.arange(1, horizon_months + 1)

    if rebalance == "none":
        rebal_months = set()
    elif rebalance == "quarterly":
        rebal_months = set(range(2, horizon_months, 3))
    elif rebalance == "semi-annual":
        rebal_months = set(range(5, horizon_months, 6))
    else:
        rebal_months = set(range(11, horizon_months, 12))

    # Extract GARCH parameters for each ticker
    garch_params = []
    for ticker in tickers:
        res = garch_results.get(ticker)
        if res is not None:
            scale = getattr(res, "_scale", 1.0)
            omega = float(res.params["omega"]) / (scale ** 2)
            alpha = float(res.params["alpha[1]"])
            beta  = float(res.params["beta[1]"])
            # Initial conditional variance (last fitted value)
            init_var = float(res.conditional_volatility.iloc[-1] ** 2) / (scale ** 2) / 12
            mu_monthly = float(res.resid.mean()) / scale / 12 if hasattr(res, "resid") else 0.0
            garch_params.append({"omega": omega, "alpha": alpha, "beta": beta,
                                  "init_var": init_var, "mu": mu_monthly})
        else:
            garch_params.append({"omega": 1e-4, "alpha": 0.1, "beta": 0.85,
                                  "init_var": 0.001, "mu": 0.0})

    # Cholesky decomp of correlation matrix for correlated shocks
    try:
        L = np.linalg.cholesky(correlation_matrix + 1e-8 * np.eye(n_assets))
    except np.linalg.LinAlgError:
        L = np.eye(n_assets)

    rng = np.random.default_rng(seed)
    paths = np.zeros((n_paths, horizon_months))

    for i in range(n_paths):
        wealth = float(initial_wealth)
        current_w = w.copy()
        cond_vars = np.array([p["init_var"] for p in garch_params])

        for t in range(horizon_months):
            # Generate correlated standard normals
            z = L @ rng.standard_normal(n_assets)
            # Compute returns from GARCH process
            monthly_ret = np.array([
                garch_params[j]["mu"] + np.sqrt(cond_vars[j]) * z[j]
                for j in range(n_assets)
            ])
            # Update conditional variances
            for j, p in enumerate(garch_params):
                cond_vars[j] = (p["omega"]
                                + p["alpha"] * monthly_ret[j] ** 2
                                + p["beta"]  * cond_vars[j])

            port_ret = float(current_w @ monthly_ret)
            wealth = wealth * (1 + port_ret) + contributions[t]
            if t in rebal_months:
                current_w = w.copy()
            paths[i, t] = wealth

    real_paths = paths / deflators[np.newaxis, :]
    return {
        "paths":           paths,
        "real_paths":      real_paths,
        "terminal_wealth": paths[:, -1],
        "real_terminal":   real_paths[:, -1],
        "weights_used":    w,
        "metadata": {
            "method":       "garch_filtered",
            "n_paths":      n_paths,
            "horizon_years": horizon_years,
        },
    }
