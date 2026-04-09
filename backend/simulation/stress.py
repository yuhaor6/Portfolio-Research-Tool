import numpy as np
import pandas as pd


def inject_crash(
    paths: np.ndarray,
    crash_year: int,
    severity: float = -0.35,
    horizon_years: int = 10,
    duration_months: int = 3,
) -> np.ndarray:
    """
    Inject a market crash (sudden drop) at `crash_year` into all paths.

    The crash is spread over `duration_months` months.

    Parameters
    ----------
    paths : np.ndarray (n_paths, horizon_months)
    crash_year : int  (1-indexed relative to simulation start)
    severity : float  (total crash return, e.g., -0.35 for 35% drop)
    duration_months : number of months over which the crash unfolds

    Returns
    -------
    Modified paths array (copy).
    """
    modified = paths.copy()
    crash_month_start = (crash_year - 1) * 12

    # Monthly shock: distribute severity over duration_months
    monthly_shock = (1 + severity) ** (1 / duration_months) - 1

    for m in range(duration_months):
        idx = crash_month_start + m
        if idx >= paths.shape[1]:
            break
        # Scale all wealth values from this month onward by the monthly shock
        modified[:, idx:] *= (1 + monthly_shock)

    return modified


def inject_job_loss(
    contributions: np.ndarray,
    loss_year: int,
    duration_months: int = 12,
    reduced_fraction: float = 0.0,
) -> np.ndarray:
    """
    Simulate job loss: reduce contributions to `reduced_fraction` during the period.

    Parameters
    ----------
    contributions : np.ndarray (horizon_months,) monthly contribution amounts
    loss_year : int  (1-indexed)
    duration_months : how long the unemployment lasts
    reduced_fraction : fraction of normal contribution (0 = no income, 0.3 = 30%)

    Returns
    -------
    Modified contributions array.
    """
    modified = contributions.copy()
    start = (loss_year - 1) * 12
    end = min(start + duration_months, len(modified))
    modified[start:end] = modified[start:end] * reduced_fraction
    return modified


def inject_inflation_spike(
    paths: np.ndarray,
    spike_inflation: float = 0.08,
    horizon_years: int = 10,
) -> np.ndarray:
    """
    Re-deflate paths using a higher-than-baseline inflation assumption.
    Returns real-wealth paths under stressed inflation.

    Parameters
    ----------
    paths : np.ndarray (n_paths, horizon_months) — NOMINAL paths
    spike_inflation : annualized inflation rate (e.g., 0.08 for 8%)

    Returns
    -------
    Real paths deflated by spike inflation.
    """
    horizon_months = paths.shape[1]
    monthly_inflation = (1 + spike_inflation) ** (1 / 12)
    deflators = monthly_inflation ** np.arange(1, horizon_months + 1)
    return paths / deflators[np.newaxis, :]


STRESS_SCENARIOS = {
    "2008_gfc": {
        "label": "2008 Global Financial Crisis",
        "crash_year": 2,
        "severity": -0.50,
        "duration_months": 12,
    },
    "covid_crash": {
        "label": "COVID-19 Crash (2020)",
        "crash_year": 3,
        "severity": -0.35,
        "duration_months": 2,
    },
    "high_inflation": {
        "label": "Persistent High Inflation (8%)",
        "spike_inflation": 0.08,
    },
    "job_loss": {
        "label": "12-Month Job Loss (Year 2)",
        "loss_year": 2,
        "duration_months": 12,
        "reduced_fraction": 0.0,
    },
    "stagflation": {
        "label": "Stagflation (Crash + High Inflation)",
        "crash_year": 2,
        "severity": -0.25,
        "duration_months": 6,
        "spike_inflation": 0.07,
    },
}


def apply_stress_scenario(
    nominal_paths: np.ndarray,
    contributions: np.ndarray,
    scenario_name: str,
) -> dict:
    """
    Apply a named stress scenario to a set of simulation paths.

    Returns dict with: stressed_paths (nominal), real_paths (stressed inflation),
    terminal_wealth, real_terminal.
    """
    scenario = STRESS_SCENARIOS[scenario_name]
    paths = nominal_paths.copy()
    contribs = contributions.copy()

    if "crash_year" in scenario:
        paths = inject_crash(
            paths,
            scenario["crash_year"],
            scenario.get("severity", -0.35),
            duration_months=scenario.get("duration_months", 3),
        )

    if "loss_year" in scenario:
        # Job loss affects contributions — re-simulate would be ideal,
        # but here we approximate by scaling down path values in that period
        reduced_contrib = inject_job_loss(
            contribs,
            scenario["loss_year"],
            scenario.get("duration_months", 12),
            scenario.get("reduced_fraction", 0.0),
        )
        # Difference in contributions flows directly to/from wealth
        contrib_diff = reduced_contrib - contribs  # negative = less saved
        for t in range(len(contrib_diff)):
            if contrib_diff[t] != 0:
                paths[:, t:] += contrib_diff[t]

    inflation = scenario.get("spike_inflation", 0.025)
    real_paths = inject_inflation_spike(paths, spike_inflation=inflation)

    return {
        "stressed_paths":  paths,
        "real_paths":      real_paths,
        "terminal_wealth": paths[:, -1],
        "real_terminal":   real_paths[:, -1],
        "scenario":        scenario,
    }
