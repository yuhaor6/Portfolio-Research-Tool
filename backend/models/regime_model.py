"""models/regime_model.py — Hamilton 2-state Markov-switching regime model."""

import numpy as np
import pandas as pd
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import RF_TICKER


def fit_regime_model(
    equity_returns: pd.Series,
    rf_returns: pd.Series | None = None,
    n_regimes: int = 2,
) -> object:
    """
    Fit a Hamilton Markov-switching model on equity excess returns.

    Parameters
    ----------
    equity_returns : pd.Series
        Monthly total returns for the equity benchmark (e.g., IVV).
    rf_returns : pd.Series, optional
        Monthly risk-free returns (SHV). If provided, uses excess returns.
    n_regimes : int
        Number of regimes (fixed at 2: bull and bear).

    Returns
    -------
    Fitted MarkovRegression result object.
    """
    if rf_returns is not None:
        # Align and compute excess returns
        aligned = pd.concat([equity_returns, rf_returns], axis=1).dropna()
        excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    else:
        excess = equity_returns.dropna()

    model = MarkovRegression(
        excess,
        k_regimes=n_regimes,
        trend="c",           # regime-dependent intercept (mean)
        switching_variance=True,  # regime-dependent variance
    )
    result = model.fit(disp=False, maxiter=500)
    return result


def get_regime_summary(result) -> dict:
    """
    Extract key statistics from a fitted regime model.

    Returns dict with:
        regime_means : list[float]
        regime_vols  : list[float]  (annualized)
        transition_matrix : np.ndarray (n_regimes × n_regimes)
        smoothed_probs : pd.DataFrame (dates × regimes)
        current_regime : int  (highest-prob regime at last date)
        current_prob   : float
    """
    n = result.k_regimes
    regime_means = []
    regime_vols  = []

    for i in range(n):
        # Monthly mean → annualize
        mean_monthly = float(result.params[f"const[{i}]"])
        var_monthly  = float(result.params[f"sigma2[{i}]"])
        regime_means.append(mean_monthly * 12)
        regime_vols.append(np.sqrt(var_monthly * 12))

    # Identify bull (higher mean) vs bear (lower mean)
    bull_regime = int(np.argmax(regime_means))
    bear_regime = int(np.argmin(regime_means))

    trans_matrix = result.regime_transition  # shape: (n, n) or (n, n, nobs)
    if trans_matrix.ndim == 3:
        # Time-varying — take the mean
        trans_matrix = trans_matrix.mean(axis=2)

    smoothed_probs = result.smoothed_marginal_probabilities
    if isinstance(smoothed_probs, np.ndarray):
        smoothed_probs = pd.DataFrame(
            smoothed_probs,
            index=result.model.endog_names if hasattr(result.model, 'endog_names') else None,
            columns=[f"regime_{i}" for i in range(n)],
        )
    else:
        smoothed_probs.columns = [f"regime_{i}" for i in range(n)]

    last_probs = smoothed_probs.iloc[-1].values
    current_regime = int(np.argmax(last_probs))
    current_prob   = float(last_probs[current_regime])

    return {
        "n_regimes":        n,
        "bull_regime":      bull_regime,
        "bear_regime":      bear_regime,
        "regime_means":     regime_means,
        "regime_vols":      regime_vols,
        "transition_matrix": trans_matrix,
        "smoothed_probs":   smoothed_probs,
        "current_regime":   current_regime,
        "current_prob":     current_prob,
    }


def regime_conditional_stats(
    all_returns: pd.DataFrame,
    smoothed_probs: pd.DataFrame,
    n_regimes: int = 2,
    threshold: float = 0.8,
    trading_periods: int = 12,
) -> dict:
    """
    Compute regime-conditional mean vectors and covariance matrices.

    Uses only periods where one regime's smoothed probability exceeds `threshold`.

    Returns
    -------
    dict: {regime_id: {"mean": np.ndarray, "cov": np.ndarray, "n_obs": int}}
    """
    # Align dates
    common_idx = all_returns.index.intersection(smoothed_probs.index)
    ret_aligned = all_returns.loc[common_idx].dropna()
    probs_aligned = smoothed_probs.loc[ret_aligned.index]

    result = {}
    for i in range(n_regimes):
        col = f"regime_{i}"
        mask = probs_aligned[col] >= threshold
        subset = ret_aligned[mask]
        if len(subset) < 10:
            # Not enough observations — skip threshold filter
            subset = ret_aligned
        result[i] = {
            "mean":  subset.mean().values * trading_periods,
            "cov":   subset.cov().values * trading_periods,
            "n_obs": len(subset),
        }
    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.fetcher import fetch_returns
    from config import FULL_HISTORY_TICKERS

    print("Fetching IVV and SHV returns (2005–2025)...")
    ret = fetch_returns(tickers=["IVV", "SHV", "AGG"], start="2005-01-01", end="2025-12-31")

    print("Fitting regime model on IVV excess returns...")
    result = fit_regime_model(ret["IVV"], ret["SHV"])
    summary = get_regime_summary(result)

    print(f"\nBull regime (#{summary['bull_regime']}): "
          f"mean={summary['regime_means'][summary['bull_regime']]:.2%}, "
          f"vol={summary['regime_vols'][summary['bull_regime']]:.2%}")
    print(f"Bear regime (#{summary['bear_regime']}): "
          f"mean={summary['regime_means'][summary['bear_regime']]:.2%}, "
          f"vol={summary['regime_vols'][summary['bear_regime']]:.2%}")
    print(f"\nTransition matrix:\n{summary['transition_matrix'].round(3)}")
    print(f"\nCurrent regime: #{summary['current_regime']} "
          f"(prob={summary['current_prob']:.1%})")

    # Show regime-conditional correlations
    common_tickers = ["IVV", "AGG"]
    cond_stats = regime_conditional_stats(ret[common_tickers], summary["smoothed_probs"])
    for i in range(2):
        label = "BULL" if i == summary["bull_regime"] else "BEAR"
        cov = cond_stats[i]["cov"]
        vols = np.sqrt(np.diag(cov))
        corr = cov / np.outer(vols, vols)
        print(f"\n{label} regime IVV-AGG correlation: {corr[0,1]:.3f} "
              f"(n={cond_stats[i]['n_obs']})")
