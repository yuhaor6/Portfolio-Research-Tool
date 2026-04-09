import numpy as np
import pandas as pd
import sys
import os


def linear_glide_path(
    start_weights: np.ndarray,
    end_weights: np.ndarray,
    horizon_months: int,
) -> np.ndarray:
    """
    Interpolate linearly between start and end weights over the horizon.

    Returns
    -------
    np.ndarray of shape (horizon_months, n_assets)
    """
    n = len(start_weights)
    t = np.linspace(0, 1, horizon_months)
    weights = np.outer(1 - t, start_weights) + np.outer(t, end_weights)
    return weights


def equity_to_bonds_glide(
    equity_tickers: list[str],
    bond_tickers: list[str],
    all_tickers: list[str],
    horizon_months: int,
    start_equity_fraction: float = 0.80,
    end_equity_fraction: float = 0.40,
) -> np.ndarray:
    """
    Classic equity-to-bonds glide path. Reduces equity, increases bonds over time.

    Parameters
    ----------
    equity_tickers : subset of all_tickers to treat as equity
    bond_tickers   : subset of all_tickers to treat as bonds (receives equity's shed weight)
    all_tickers    : full ordered list of assets in the portfolio
    horizon_months : length of path
    start_equity_fraction : fraction in equity at start
    end_equity_fraction   : fraction in equity at end

    Returns
    -------
    np.ndarray of shape (horizon_months, len(all_tickers))
    """
    n = len(all_tickers)
    eq_idx = [all_tickers.index(t) for t in equity_tickers if t in all_tickers]
    bd_idx = [all_tickers.index(t) for t in bond_tickers if t in all_tickers]

    start_w = np.zeros(n)
    end_w   = np.zeros(n)

    if eq_idx:
        start_w[eq_idx] = start_equity_fraction / len(eq_idx)
        end_w[eq_idx]   = end_equity_fraction   / len(eq_idx)
    if bd_idx:
        start_bond = 1.0 - start_equity_fraction
        end_bond   = 1.0 - end_equity_fraction
        start_w[bd_idx] = start_bond / len(bd_idx)
        end_w[bd_idx]   = end_bond   / len(bd_idx)

    return linear_glide_path(start_w, end_w, horizon_months)


if __name__ == "__main__":
    from config import UNIVERSE_12

    eq = ["IVV", "QUAL", "USMV", "VEA", "VWO"]
    bd = ["AGG", "SHV", "TIP"]
    path = equity_to_bonds_glide(eq, bd, UNIVERSE_12, horizon_months=120)

    print(f"Glide path shape: {path.shape}")
    print(f"Month 1  weights sum: {path[0].sum():.4f}")
    print(f"Month 60 weights sum: {path[59].sum():.4f}")
    print(f"Month 120 weights sum: {path[-1].sum():.4f}")

    equity_alloc = path[:, [UNIVERSE_12.index(t) for t in eq if t in UNIVERSE_12]].sum(axis=1)
    print(f"\nEquity fraction: {equity_alloc[0]:.1%} → {equity_alloc[-1]:.1%}")
