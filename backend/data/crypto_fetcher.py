"""data/crypto_fetcher.py — Crypto-specific data handling (BTC, ETH via yfinance)."""

import os
import pandas as pd
import yfinance as yf
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATE_RANGE

CRYPTO_TICKERS = ["BTC-USD", "ETH-USD"]
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def _cache_path(ticker: str) -> str:
    return os.path.join(CACHE_DIR, f"{ticker.replace('-', '_')}.csv")


def _download_crypto_monthly(ticker: str, start: str, end: str) -> pd.Series:
    """
    Download daily crypto prices from Yahoo Finance and resample to monthly returns.
    Crypto trades 24/7, so we use calendar month-end prices.
    """
    raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"No crypto data for {ticker}")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    # Use last available price in each calendar month
    monthly = close.resample("ME").last()
    returns = monthly.pct_change().dropna()
    returns.name = ticker
    return returns


def fetch_crypto_returns(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Fetch monthly returns for crypto assets.

    Returns a DataFrame aligned to calendar month-end dates.
    Returns start from each asset's inception date, so resulting DataFrame
    will have NaN for months before inception.
    """
    if tickers is None:
        tickers = CRYPTO_TICKERS
    if start is None:
        start = DATE_RANGE["start"]
    if end is None:
        end = DATE_RANGE["end"]

    series_list = []
    for ticker in tickers:
        cached_path = _cache_path(ticker)
        if use_cache and not force_refresh and os.path.exists(cached_path):
            df = pd.read_csv(cached_path, index_col=0, parse_dates=True)
            s = df.iloc[:, 0]
        else:
            try:
                s = _download_crypto_monthly(ticker, start, end)
                os.makedirs(CACHE_DIR, exist_ok=True)
                s.to_frame(name="return").to_csv(cached_path)
            except Exception as exc:
                print(f"  WARNING: Could not fetch {ticker}: {exc}")
                continue
        s.name = ticker
        series_list.append(s)

    if not series_list:
        return pd.DataFrame()

    df = pd.concat(series_list, axis=1)
    df = df.loc[start:end]
    return df


if __name__ == "__main__":
    print("Fetching crypto returns...")
    df = fetch_crypto_returns()
    print(f"Shape: {df.shape}")
    for col in df.columns:
        first = df[col].first_valid_index()
        n = df[col].dropna().shape[0]
        print(f"  {col}: first={first.date()}, n={n} months, "
              f"ann_ret={df[col].mean()*12:.1%}, ann_vol={df[col].std()*12**0.5:.1%}")
