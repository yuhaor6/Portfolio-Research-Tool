"""data/fetcher.py — Download and cache monthly total returns for all assets."""

import os
import pandas as pd
import yfinance as yf
import sys

# Ensure backend package root is importable when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ASSET_TICKERS, DATE_RANGE, RF_TICKER

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def _cache_path(ticker: str) -> str:
    safe = ticker.replace("-", "_")
    return os.path.join(CACHE_DIR, f"{safe}.csv")


def _load_from_cache(ticker: str) -> pd.Series | None:
    path = _cache_path(ticker)
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df.iloc[:, 0]
    return None


def _save_to_cache(ticker: str, series: pd.Series) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    series.to_frame(name="return").to_csv(_cache_path(ticker))


def _download_monthly_returns(ticker: str, start: str, end: str) -> pd.Series:
    """Download adjusted close prices and convert to monthly total returns."""
    raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"No data returned for {ticker}")
    close = raw["Close"]
    # yfinance ≥0.2 returns a DataFrame with ticker as column for single-ticker downloads
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    # Monthly resampling: last trading day of each month
    monthly = close.resample("ME").last()
    returns = monthly.pct_change().dropna()
    returns.name = ticker
    return returns


def fetch_returns(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Fetch monthly total returns for a list of tickers.

    Parameters
    ----------
    tickers : list of str, optional
        Defaults to all 12 asset tickers from config.
    start : str, optional
        Start date (YYYY-MM-DD). Defaults to config DATE_RANGE['start'].
    end : str, optional
        End date (YYYY-MM-DD). Defaults to config DATE_RANGE['end'].
    use_cache : bool
        Load from CSV cache if available.
    force_refresh : bool
        Ignore cache and re-download.

    Returns
    -------
    pd.DataFrame
        Monthly returns, columns = tickers, index = month-end dates.
        Forward-fills up to 3 consecutive NaN months per asset, then drops remaining.
    """
    if tickers is None:
        tickers = list(ASSET_TICKERS.keys())
    if start is None:
        start = DATE_RANGE["start"]
    if end is None:
        end = DATE_RANGE["end"]

    series_list = []
    for ticker in tickers:
        cached = None if force_refresh else (_load_from_cache(ticker) if use_cache else None)
        if cached is not None:
            s = cached
        else:
            try:
                s = _download_monthly_returns(ticker, start, end)
                if use_cache:
                    _save_to_cache(ticker, s)
            except Exception as exc:
                print(f"  WARNING: Could not fetch {ticker}: {exc}")
                continue
        s.name = ticker
        series_list.append(s)

    if not series_list:
        raise RuntimeError("No data could be fetched for any ticker.")

    df = pd.concat(series_list, axis=1)

    # Forward-fill gaps up to 3 consecutive months (handles thin-trading assets)
    df = df.ffill(limit=3)

    # Trim to requested date range
    df = df.loc[start:end]

    return df


def fetch_rf_rate(start: str | None = None, end: str | None = None) -> pd.Series:
    """Return monthly risk-free rate from SHV total returns."""
    returns = fetch_returns(tickers=[RF_TICKER], start=start, end=end)
    return returns[RF_TICKER]


if __name__ == "__main__":
    print("Fetching all asset returns...")
    df = fetch_returns()
    print(f"\nShape: {df.shape}  (rows=months, cols=assets)")
    print(f"Date range: {df.index[0].date()} → {df.index[-1].date()}")
    print("\nFirst available date per asset:")
    for col in df.columns:
        first = df[col].first_valid_index()
        last = df[col].last_valid_index()
        n = df[col].dropna().shape[0]
        print(f"  {col:10s}  first={first.date()}  last={last.date()}  n={n}")
    print("\nSample (last 5 rows):")
    print(df.tail().to_string())
