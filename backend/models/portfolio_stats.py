"""models/portfolio_stats.py — Core portfolio statistics utilities."""

import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import RF_TICKER


def compute_stats(
    returns_df: pd.DataFrame,
    rf_ticker: str = RF_TICKER,
    trading_periods: int = 12,
) -> pd.DataFrame:
    """
    Compute annualized return, volatility, and Sharpe for each asset.

    Parameters
    ----------
    returns_df : pd.DataFrame
        Monthly total returns. NaN allowed (asset not yet available).
    rf_ticker : str
        Column to use as risk-free rate.
    trading_periods : int
        Periods per year (12 for monthly).

    Returns
    -------
    pd.DataFrame indexed by ticker with columns:
        ann_return, ann_vol, sharpe, max_drawdown, skewness, kurtosis, n_months
    """
    rf = returns_df[rf_ticker].mean() * trading_periods if rf_ticker in returns_df.columns else 0.0

    rows = []
    for col in returns_df.columns:
        s = returns_df[col].dropna()
        if s.empty:
            continue
        ann_ret = s.mean() * trading_periods
        ann_vol = s.std() * np.sqrt(trading_periods)
        sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0
        cum = (1 + s).cumprod()
        mdd = max_drawdown(cum)
        rows.append({
            "ticker":       col,
            "ann_return":   ann_ret,
            "ann_vol":      ann_vol,
            "sharpe":       sharpe,
            "max_drawdown": mdd,
            "skewness":     float(s.skew()),
            "kurtosis":     float(s.kurtosis()),
            "n_months":     len(s),
        })

    df = pd.DataFrame(rows).set_index("ticker")
    return df


def compute_covariance(
    returns_df: pd.DataFrame,
    trading_periods: int = 12,
) -> pd.DataFrame:
    """Return annualized covariance matrix (drops rows with any NaN first)."""
    clean = returns_df.dropna()
    return clean.cov() * trading_periods


def compute_correlation(returns_df: pd.DataFrame) -> pd.DataFrame:
    """Return Pearson correlation matrix (pairwise complete observations)."""
    return returns_df.corr()


def max_drawdown(cumulative_returns: pd.Series) -> float:
    """
    Compute maximum drawdown from a series of cumulative returns.

    Parameters
    ----------
    cumulative_returns : pd.Series
        Running product of (1 + r), starting near 1.0.
    """
    running_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - running_max) / running_max
    return float(drawdown.min())


def rolling_sharpe(
    returns: pd.Series,
    rf_series: pd.Series | None = None,
    window: int = 12,
    trading_periods: int = 12,
) -> pd.Series:
    """Rolling annualized Sharpe over `window` months."""
    if rf_series is not None:
        excess = returns - rf_series
    else:
        excess = returns
    roll_mean = excess.rolling(window).mean() * trading_periods
    roll_vol  = excess.rolling(window).std() * np.sqrt(trading_periods)
    return roll_mean / roll_vol


if __name__ == "__main__":
    import importlib, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.fetcher import fetch_returns
    from config import UNIVERSE_12, DATE_RANGE_12

    print("Fetching returns for 12-asset universe (2017–2025)...")
    ret = fetch_returns(tickers=UNIVERSE_12, start=DATE_RANGE_12["start"], end=DATE_RANGE_12["end"])
    stats = compute_stats(ret)
    print("\n=== Asset Statistics ===")
    print(stats.to_string(float_format="{:.4f}".format))

    cov = compute_covariance(ret)
    print(f"\nCovariance matrix shape: {cov.shape}")
    corr = compute_correlation(ret)
    print("\nCorrelation matrix (IVV row):")
    print(corr.loc["IVV"].to_string(float_format="{:.3f}".format))
