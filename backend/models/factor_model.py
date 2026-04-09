import io
import zipfile
import numpy as np
import pandas as pd
import statsmodels.api as sm
import os
import sys
import warnings

try:
    import requests as _req
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    from urllib.request import urlretrieve as _urlretrieve
except ImportError:
    _urlretrieve = None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATE_RANGE

FF5_CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "cache", "ff5_factors.csv")
FF5_URL   = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"


def fetch_ff5_factors(start: str = "2005-01-01", end: str = "2025-12-31") -> pd.DataFrame:
    """
    Download Fama-French 5-factor monthly data from Ken French's library.
    Columns: Mkt-RF, SMB, HML, RMW, CMA, RF
    Returns as decimals (divided by 100).
    Falls back to cache if download fails.
    """
    cache_path = os.path.normpath(FF5_CACHE)
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df.loc[start:end]

    try:
        if _HAS_REQUESTS:
            resp = _req.get(FF5_URL, timeout=30)
            resp.raise_for_status()
            raw_bytes = resp.content
        else:
            import urllib.request
            with urllib.request.urlopen(FF5_URL, timeout=30) as u:
                raw_bytes = u.read()

        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            csv_name = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")][0]
            with zf.open(csv_name) as f:
                content = f.read().decode("utf-8", errors="replace")

        lines = content.splitlines()
        # Find the monthly table header (line containing "Mkt-RF")
        header_idx = next(i for i, l in enumerate(lines) if "Mkt-RF" in l)
        data_lines = []
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if not stripped or stripped.startswith(" "):
                continue
            parts = stripped.split(",")
            if len(parts) < 6:
                break
            try:
                int(parts[0].strip())  # date column — stop when not int
            except ValueError:
                break
            data_lines.append(stripped)

        from io import StringIO
        col_line = lines[header_idx].strip()
        csv_text = col_line + "\n" + "\n".join(data_lines)
        ff = pd.read_csv(StringIO(csv_text), index_col=0)
        ff.index = pd.to_datetime(ff.index.astype(str), format="%Y%m")
        ff.index = ff.index + pd.offsets.MonthEnd(0)  # align to month-end
        ff = ff / 100.0
        ff.columns = [c.strip() for c in ff.columns]

        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        ff.to_csv(cache_path)
        return ff.loc[start:end]

    except Exception as exc:
        print(f"  WARNING: Could not fetch FF5 factors: {exc}")
        return pd.DataFrame()


def capm_regression(
    portfolio_returns: pd.Series,
    market_returns: pd.Series,
    rf_returns: pd.Series,
) -> dict:
    """
    Run CAPM regression: r_p - r_f = alpha + beta * (r_mkt - r_f) + eps

    Returns dict with: alpha, beta, alpha_tstat, beta_tstat, r_squared,
    annualized_alpha, annualized_alpha_tstat
    """
    common = portfolio_returns.index.intersection(
        market_returns.index.intersection(rf_returns.index)
    )
    rp = portfolio_returns.loc[common].values
    rm = market_returns.loc[common].values
    rf = rf_returns.loc[common].values

    excess_p = rp - rf
    excess_m = rm - rf

    X = sm.add_constant(excess_m)
    model = sm.OLS(excess_p, X).fit()

    alpha_monthly = model.params[0]
    beta          = model.params[1]
    se_alpha      = model.bse[0]

    return {
        "alpha":            alpha_monthly,
        "alpha_annualized": alpha_monthly * 12,
        "beta":             beta,
        "alpha_tstat":      model.tvalues[0],
        "beta_tstat":       model.tvalues[1],
        "alpha_pvalue":     model.pvalues[0],
        "r_squared":        model.rsquared,
        "n_obs":            model.nobs,
    }


def ff5_regression(
    portfolio_returns: pd.Series,
    ff5_factors: pd.DataFrame,
    rf_col: str = "RF",
) -> dict:
    """
    Run Fama-French 5-factor regression.
    ff5_factors must have columns: Mkt-RF, SMB, HML, RMW, CMA, RF

    Returns dict with factor loadings, t-stats, and alpha.
    """
    factors = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
    common = portfolio_returns.index.intersection(ff5_factors.index)
    rp = portfolio_returns.loc[common]
    ff = ff5_factors.loc[common]

    # Excess portfolio return
    excess_p = rp.values - ff[rf_col].values

    X = sm.add_constant(ff[factors].values)
    model = sm.OLS(excess_p, X).fit()

    result = {
        "alpha":            model.params[0],
        "alpha_annualized": model.params[0] * 12,
        "alpha_tstat":      model.tvalues[0],
        "alpha_pvalue":     model.pvalues[0],
        "r_squared":        model.rsquared,
        "n_obs":            int(model.nobs),
    }
    for i, factor in enumerate(factors):
        result[f"loading_{factor}"] = model.params[i + 1]
        result[f"tstat_{factor}"]   = model.tvalues[i + 1]
        result[f"pvalue_{factor}"]  = model.pvalues[i + 1]

    return result


def rolling_beta(
    portfolio_returns: pd.Series,
    market_returns: pd.Series,
    rf_returns: pd.Series,
    window: int = 12,
) -> pd.Series:
    """Compute rolling OLS beta over `window` months."""
    common = portfolio_returns.index.intersection(
        market_returns.index.intersection(rf_returns.index)
    )
    rp = (portfolio_returns - rf_returns).loc[common]
    rm = (market_returns - rf_returns).loc[common]

    betas = {}
    for end_idx in range(window, len(common) + 1):
        window_rp = rp.iloc[end_idx - window:end_idx].values
        window_rm = rm.iloc[end_idx - window:end_idx].values
        # Simple OLS slope
        cov = np.cov(window_rp, window_rm)
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else np.nan
        betas[common[end_idx - 1]] = beta

    return pd.Series(betas, name="rolling_beta")


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.fetcher import fetch_returns
    from models.efficient_frontier import tangency_portfolio
    from models.portfolio_stats import compute_stats, compute_covariance
    from config import UNIVERSE_12, DATE_RANGE_12, RF_TICKER

    ret = fetch_returns(tickers=UNIVERSE_12, start=DATE_RANGE_12["start"], end=DATE_RANGE_12["end"])
    stats = compute_stats(ret)
    cov = compute_covariance(ret)
    mu = stats["ann_return"].values
    rf_val = stats.loc[RF_TICKER, "ann_return"]

    crypto_idx = [UNIVERSE_12.index(t) for t in ["BTC-USD", "ETH-USD"]]
    tang = tangency_portfolio(mu, cov, rf_val, crypto_indices=crypto_idx)
    port_ret = (ret[UNIVERSE_12] * tang["weights"]).sum(axis=1).dropna()

    print("\n=== CAPM Regression (Tangency 12-asset vs IVV) ===")
    capm = capm_regression(port_ret, ret["IVV"], ret["SHV"])
    for k, v in capm.items():
        print(f"  {k}: {v:.4f}")
