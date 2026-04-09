import numpy as np
import pandas as pd
from arch import arch_model
import warnings
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def fit_garch(
    returns_series: pd.Series,
    p: int = 1,
    q: int = 1,
    rescale: bool = True,
) -> object:
    """
    Fit a GARCH(p,q) model to a monthly returns series.

    Parameters
    ----------
    returns_series : pd.Series  (monthly returns, e.g., 0.05 for 5%)
    p, q : GARCH lag orders
    rescale : bool  Multiply returns by 100 for numerical stability

    Returns
    -------
    arch model result object (or None if fitting fails)
    """
    s = returns_series.dropna()
    scale = 100.0 if rescale else 1.0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            am = arch_model(s * scale, vol="GARCH", p=p, q=q, dist="Normal", rescale=False)
            res = am.fit(disp="off", options={"maxiter": 500})
            res._scale = scale  # store scale for later use
            return res
        except Exception as exc:
            print(f"  GARCH fitting failed for {returns_series.name}: {exc}")
            return None


def conditional_volatility(model_result, annualize: bool = True) -> pd.Series:
    """
    Extract conditional volatility series from a fitted GARCH model.

    Returns annualized vol if annualize=True.
    """
    if model_result is None:
        return pd.Series(dtype=float)

    scale = getattr(model_result, "_scale", 1.0)
    cond_vol = model_result.conditional_volatility / scale  # monthly vol

    if annualize:
        cond_vol = cond_vol * np.sqrt(12)

    return cond_vol


def forecast_vol(
    model_result,
    horizon: int = 12,
    annualize: bool = True,
) -> np.ndarray:
    """
    Forecast conditional volatility for `horizon` steps ahead.

    Returns array of length `horizon`.
    """
    if model_result is None:
        return np.full(horizon, np.nan)

    scale = getattr(model_result, "_scale", 1.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fc = model_result.forecast(horizon=horizon, reindex=False)
    # variance forecasts → vol
    var_fc = fc.variance.values[-1] / (scale ** 2)
    vol_fc = np.sqrt(var_fc)

    if annualize:
        vol_fc = vol_fc * np.sqrt(12)

    return vol_fc


def fit_all_assets(returns_df: pd.DataFrame) -> dict:
    """
    Fit GARCH(1,1) for every column in returns_df.

    Returns dict of {ticker: model_result or None}
    """
    results = {}
    for col in returns_df.columns:
        print(f"  Fitting GARCH for {col}...")
        results[col] = fit_garch(returns_df[col])
    return results


def rolling_correlation_dcc_proxy(
    returns_df: pd.DataFrame,
    window: int = 36,
) -> dict:
    """
    Compute approximate dynamic correlations using rolling windows.
    This is a fallback when full DCC-GARCH estimation is too slow/unreliable
    for a 12-asset universe.

    Returns
    -------
    dict: {date: correlation_matrix (pd.DataFrame)}
    """
    corr_series = {}
    for date in returns_df.index[window:]:
        window_data = returns_df.loc[:date].iloc[-window:]
        corr_series[date] = window_data.corr()
    return corr_series


def garch_standardized_residuals(garch_results: dict, returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return standardized residuals (return / conditional_vol) for each asset.
    Used as input to DCC estimation.
    """
    std_resid = {}
    for ticker, result in garch_results.items():
        if result is None or ticker not in returns_df.columns:
            continue
        scale = getattr(result, "_scale", 1.0)
        cond_vol = result.conditional_volatility / scale
        raw = returns_df[ticker].dropna()
        common = raw.index.intersection(cond_vol.index)
        if len(common) < 10:
            continue
        std_resid[ticker] = raw.loc[common] / cond_vol.loc[common]

    return pd.DataFrame(std_resid)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.fetcher import fetch_returns
    from config import UNIVERSE_12, FULL_HISTORY_TICKERS

    print("Fetching returns (2005–2025)...")
    ret = fetch_returns(tickers=FULL_HISTORY_TICKERS, start="2005-01-01", end="2025-12-31")

    print("\nFitting GARCH for each asset...")
    garch_results = fit_all_assets(ret)

    print("\n=== Conditional Volatility (current vs historical avg) ===")
    print(f"{'Ticker':10s}  {'Current Ann Vol':>16s}  {'Hist Avg Ann Vol':>16s}  {'Percentile':>10s}")
    for ticker, res in garch_results.items():
        if res is None:
            continue
        cond_vol = conditional_volatility(res, annualize=True)
        if cond_vol.empty:
            continue
        current = cond_vol.iloc[-1]
        hist_avg = cond_vol.mean()
        pct = (cond_vol <= current).mean() * 100
        print(f"  {ticker:8s}  {current:16.2%}  {hist_avg:16.2%}  {pct:9.0f}th")
