from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
import pandas as pd
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "results")

app = FastAPI(
    title="PortfolioLab API",
    description="Research-grade portfolio simulation and optimization API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_result(filename: str) -> dict:
    """Load a pre-computed JSON result file."""
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail=f"Result file '{filename}' not found. Run run_all.py first."
        )
    with open(path, "r") as f:
        return json.load(f)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "PortfolioLab"}


@app.get("/api/client-profile")
def get_client_profile():
    """Return client profile and savings schedule."""
    return _load_result("client_profile.json")


@app.get("/api/asset-stats")
def get_asset_stats():
    """Return per-asset statistics: return, vol, Sharpe, correlation matrix."""
    return _load_result("asset_stats.json")


@app.get("/api/efficient-frontier")
def get_efficient_frontier(universe: str = Query("12", enum=["3", "5", "12"])):
    """Return efficient frontier points and tangency portfolio for a given universe."""
    return _load_result(f"efficient_frontier_{universe}.json")


@app.get("/api/regime")
def get_regime():
    """Return regime model results: probabilities, stats, transition matrix."""
    return _load_result("regime.json")


@app.get("/api/garch")
def get_garch():
    """Return GARCH conditional volatility series and current vol levels."""
    return _load_result("garch.json")


@app.get("/api/simulation")
def get_simulation(
    mode: str = Query("bootstrap", enum=["bootstrap", "parametric", "regime", "garch"]),
    strategy: str = Query("tangency_12"),
):
    """
    Return simulation results: percentile bands, terminal wealth distribution,
    and full metrics for the specified mode and strategy.
    """
    filename = f"simulation_{mode}_{strategy}.json"
    return _load_result(filename)


@app.get("/api/comparison")
def get_comparison():
    """Return full strategy comparison table across all metrics."""
    return _load_result("strategy_comparison.json")


@app.get("/api/risk")
def get_risk(strategy: str = Query("tangency_12")):
    """Return drawdown, VaR/CVaR, and stress test results for a strategy."""
    return _load_result(f"risk_{strategy}.json")


@app.get("/api/factor")
def get_factor(strategy: str = Query("tangency_12")):
    """Return CAPM alpha and FF5 factor loadings."""
    return _load_result(f"factor_{strategy}.json")


@app.get("/api/sensitivity")
def get_sensitivity(param: str = Query("window", enum=["window", "crypto_cap", "rebalancing"])):
    """Return sensitivity sweep results."""
    return _load_result(f"sensitivity_{param}.json")


@app.post("/api/recalculate")
def recalculate(profile: dict = Body(...)):
    """
    Accept a modified client profile, re-run cashflow projection,
    and re-run bootstrap simulation with the primary strategy.
    Returns updated simulation results.
    """
    import importlib
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    try:
        from client.cashflows import generate_savings_schedule, monthly_contributions
        from data.fetcher import fetch_returns
        from config import UNIVERSE_12, DATE_RANGE_12
        from simulation.bootstrap import block_bootstrap_mc
        from analysis.risk_metrics import compute_all_metrics

        # Fill in keys that the cashflow model requires but the frontend form doesn't expose
        full_profile = {
            "loan_min_payment": 500,
            "emergency_fund_target": profile.get("emergency_fund_months", 6)
                                     * profile.get("annual_expenses", 55000) / 12,
            **profile,
        }

        schedule = generate_savings_schedule(full_profile)
        contrib = monthly_contributions(schedule)

        # Load precomputed tangency weights (stored as {ticker: weight} dict)
        frontier_data = _load_result("efficient_frontier_12.json")
        w = np.array(list(frontier_data["tangency"]["weights"].values()))

        ret = fetch_returns(tickers=UNIVERSE_12,
                            start=DATE_RANGE_12["start"],
                            end=DATE_RANGE_12["end"])

        result = block_bootstrap_mc(
            returns_df=ret,
            weights=w,
            contributions=contrib,
            n_paths=5000,
            initial_wealth=profile.get("initial_investment", 10000),
        )

        metrics = compute_all_metrics(
            result["real_paths"],
            result["real_terminal"],
            goal=profile.get("goal_amount", 1_000_000),
        )

        # Build fan chart data (downsampled percentile bands)
        percentile_bands = {}
        for p in [5, 25, 50, 75, 95]:
            percentile_bands[f"p{p}"] = np.percentile(
                result["real_paths"], p, axis=0
            ).tolist()

        return {
            "metrics": metrics,
            "fan_chart": percentile_bands,
            "savings_schedule": schedule.to_dict(orient="records"),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
