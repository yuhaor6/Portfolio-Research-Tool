import numpy as np
import pandas as pd
from dataclasses import dataclass, field
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SIMULATION_CONFIG, CLIENT_PROFILE


@dataclass
class SimulationResult:
    paths: np.ndarray            # (n_paths, horizon_months) nominal
    real_paths: np.ndarray       # (n_paths, horizon_months) inflation-adjusted
    terminal_wealth: np.ndarray  # (n_paths,) nominal
    real_terminal: np.ndarray    # (n_paths,) real
    weights_used: np.ndarray
    metadata: dict = field(default_factory=dict)
    regime_paths: np.ndarray | None = None  # only for regime MC

    def quantiles(self, percentiles=(5, 25, 50, 75, 95), real: bool = True) -> dict:
        """Return terminal wealth quantiles."""
        tw = self.real_terminal if real else self.terminal_wealth
        return {f"p{p}": float(np.percentile(tw, p)) for p in percentiles}

    def path_percentiles(self, percentiles=(5, 25, 50, 75, 95), real: bool = True) -> np.ndarray:
        """Return percentile bands over all time steps. Shape: (len(percentiles), horizon_months)."""
        arr = self.real_paths if real else self.paths
        return np.percentile(arr, percentiles, axis=0)


def run_simulation(
    mode: str = "bootstrap",
    *,
    # Shared
    weights: np.ndarray,
    contributions: np.ndarray,
    n_paths: int | None = None,
    horizon_years: int = 10,
    rebalance: str = "annual",
    initial_wealth: float | None = None,
    inflation: float = 0.025,
    seed: int = 42,
    # Bootstrap-specific
    returns_df: pd.DataFrame | None = None,
    block_size: int = 12,
    # Parametric-specific
    mu: np.ndarray | None = None,
    cov: np.ndarray | None = None,
    # Regime-specific
    regime_summary: dict | None = None,
    regime_cov_matrices: dict | None = None,
    # GARCH-specific
    garch_results: dict | None = None,
    correlation_matrix: np.ndarray | None = None,
    tickers: list[str] | None = None,
) -> SimulationResult:
    """
    Unified simulation dispatcher.

    Parameters
    ----------
    mode : 'bootstrap' | 'parametric' | 'regime' | 'garch'

    Returns
    -------
    SimulationResult
    """
    if n_paths is None:
        n_paths = SIMULATION_CONFIG["n_paths_dev"]  # safe default
    if initial_wealth is None:
        initial_wealth = CLIENT_PROFILE["initial_investment"]

    kwargs_common = dict(
        weights=weights,
        contributions=contributions,
        n_paths=n_paths,
        horizon_years=horizon_years,
        rebalance=rebalance,
        initial_wealth=initial_wealth,
        inflation=inflation,
        seed=seed,
    )

    if mode == "bootstrap":
        from simulation.bootstrap import block_bootstrap_mc
        if returns_df is None:
            raise ValueError("returns_df is required for bootstrap mode.")
        result = block_bootstrap_mc(
            returns_df=returns_df,
            block_size=block_size,
            **kwargs_common,
        )

    elif mode == "parametric":
        from simulation.parametric import parametric_mc
        if mu is None or cov is None:
            raise ValueError("mu and cov are required for parametric mode.")
        result = parametric_mc(mu=mu, cov=cov, **kwargs_common)

    elif mode == "regime":
        from simulation.parametric import regime_mc
        if regime_summary is None or regime_cov_matrices is None:
            raise ValueError("regime_summary and regime_cov_matrices required for regime mode.")
        result = regime_mc(
            regime_summary=regime_summary,
            regime_cov_matrices=regime_cov_matrices,
            **kwargs_common,
        )

    elif mode == "garch":
        from simulation.parametric import garch_mc
        if garch_results is None or correlation_matrix is None or tickers is None:
            raise ValueError("garch_results, correlation_matrix, tickers required for garch mode.")
        result = garch_mc(
            garch_results=garch_results,
            correlation_matrix=correlation_matrix,
            tickers=tickers,
            **kwargs_common,
        )

    else:
        raise ValueError(f"Unknown simulation mode: {mode}. Choose bootstrap/parametric/regime/garch.")

    return SimulationResult(
        paths=result["paths"],
        real_paths=result["real_paths"],
        terminal_wealth=result["terminal_wealth"],
        real_terminal=result["real_terminal"],
        weights_used=result["weights_used"],
        metadata=result.get("metadata", {}),
        regime_paths=result.get("regime_paths"),
    )
