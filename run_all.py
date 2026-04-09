"""run_all.py — Master pipeline: fetch → fit models → simulate → analyze → export JSON."""

import os
import sys
import json
import time
import numpy as np
import pandas as pd

# Force UTF-8 output on Windows to support arrow/special chars in print()
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure backend package root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _save(filename: str, data) -> None:
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=_json_default)
    print(f"  Saved → {filename}")


def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj.date())
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    raise TypeError(f"Not serializable: {type(obj)}")


# ---------------------------------------------------------------------------
# Step 1: Fetch data
# ---------------------------------------------------------------------------
def step_fetch():
    print("\n=== Step 1: Fetch Data ===")
    from data.fetcher import fetch_returns
    from config import UNIVERSE_12, DATE_RANGE_12, DATE_RANGE, FULL_HISTORY_TICKERS

    # Full-history assets
    print("  Fetching full history (2005–2025)...")
    ret_full = fetch_returns(tickers=FULL_HISTORY_TICKERS,
                             start=DATE_RANGE["start"], end=DATE_RANGE["end"])
    print(f"  Full history shape: {ret_full.shape}")

    # 12-asset universe (2017+)
    print("  Fetching 12-asset universe (2017–2025)...")
    ret_12 = fetch_returns(tickers=UNIVERSE_12,
                           start=DATE_RANGE_12["start"], end=DATE_RANGE_12["end"])
    print(f"  12-asset shape: {ret_12.shape}")

    return ret_full, ret_12


# ---------------------------------------------------------------------------
# Step 2: Client profile & cashflows
# ---------------------------------------------------------------------------
def step_cashflows():
    print("\n=== Step 2: Client Profile & Cashflows ===")
    from client.cashflows import generate_savings_schedule, monthly_contributions
    from config import CLIENT_PROFILE

    schedule = generate_savings_schedule()
    contrib = monthly_contributions(schedule)
    print(f"  Savings schedule: {len(schedule)} years, total=${schedule['investable_savings'].sum():,.0f}")

    profile_data = {
        "profile":          CLIENT_PROFILE,
        "savings_schedule": schedule.to_dict(orient="records"),
    }
    _save("client_profile.json", profile_data)
    return contrib, schedule


# ---------------------------------------------------------------------------
# Step 3: Asset statistics
# ---------------------------------------------------------------------------
def step_asset_stats(ret_12):
    print("\n=== Step 3: Asset Statistics ===")
    from models.portfolio_stats import compute_stats, compute_covariance, compute_correlation
    from config import UNIVERSE_12

    stats = compute_stats(ret_12)
    cov = compute_covariance(ret_12)
    corr = compute_correlation(ret_12)

    tickers = list(ret_12.columns)
    data = {
        "tickers": tickers,
        "stats": {
            t: {k: float(v) for k, v in row.items()}
            for t, row in stats.iterrows()
        },
        "covariance":   cov.to_dict(),
        "correlation":  corr.to_dict(),
    }
    _save("asset_stats.json", data)
    return stats, cov, corr


# ---------------------------------------------------------------------------
# Step 4: Efficient frontiers
# ---------------------------------------------------------------------------
def step_efficient_frontiers(ret_12):
    print("\n=== Step 4: Efficient Frontiers ===")
    from models.portfolio_stats import compute_stats, compute_covariance
    from models.efficient_frontier import efficient_frontier, tangency_portfolio
    from config import UNIVERSE_3, UNIVERSE_5, UNIVERSE_12, RF_TICKER

    universes = [("3", UNIVERSE_3), ("5", UNIVERSE_5), ("12", UNIVERSE_12)]
    results = {}

    for size, tickers in universes:
        print(f"  Universe {size}: {tickers[:4]}...")
        # Use the 12-asset returns but filter columns
        available = [t for t in tickers if t in ret_12.columns]
        ret = ret_12[available].dropna()

        stats = compute_stats(ret)
        cov = compute_covariance(ret)
        mu = stats["ann_return"].values
        rf = float(stats.loc[RF_TICKER, "ann_return"]) if RF_TICKER in stats.index else 0.04

        crypto_idx = [available.index(t) for t in ["BTC-USD", "ETH-USD"] if t in available]
        tang = tangency_portfolio(mu, cov, rf, crypto_indices=crypto_idx or None)
        frontier_pts = efficient_frontier(mu, cov, rf, n_points=80,
                                          crypto_indices=crypto_idx or None)

        data = {
            "universe": size,
            "tickers":  available,
            "tangency": {
                "weights":    dict(zip(available, tang["weights"].tolist())),
                "sharpe":     tang["sharpe"],
                "ann_return": tang["ann_return"],
                "ann_vol":    tang["ann_vol"],
            },
            "frontier": frontier_pts,
            "assets": {
                t: {
                    "ann_return": float(stats.loc[t, "ann_return"]),
                    "ann_vol":    float(stats.loc[t, "ann_vol"]),
                }
                for t in available if t in stats.index
            },
        }
        results[size] = data
        _save(f"efficient_frontier_{size}.json", data)
        print(f"    Tangency ({size}-asset): Sharpe={tang['sharpe']:.3f}, "
              f"Return={tang['ann_return']:.2%}, Vol={tang['ann_vol']:.2%}")

    return results


# ---------------------------------------------------------------------------
# Step 5: Regime model
# ---------------------------------------------------------------------------
def step_regime(ret_full):
    print("\n=== Step 5: Regime Model ===")
    from models.regime_model import fit_regime_model, get_regime_summary, regime_conditional_stats

    print("  Fitting Markov-switching model on IVV excess returns...")
    result = fit_regime_model(ret_full["IVV"], ret_full.get("SHV"))
    summary = get_regime_summary(result)

    # Regime-conditional stats on all full-history assets
    available = [c for c in ret_full.columns]
    cond_stats = regime_conditional_stats(ret_full[available], summary["smoothed_probs"])

    probs_df = summary["smoothed_probs"]

    # IVV cumulative log-return series (normalised to 1.0) for overlay chart
    ivv = ret_full["IVV"].dropna()
    ivv_aligned = ivv.reindex(probs_df.index).ffill()
    ivv_cum = (1 + ivv_aligned).cumprod()
    ivv_cum = ivv_cum / ivv_cum.iloc[0]  # rebase to 1.0

    data = {
        "n_regimes":      summary["n_regimes"],
        "bull_regime":    summary["bull_regime"],
        "bear_regime":    summary["bear_regime"],
        "regime_means":   summary["regime_means"],
        "regime_vols":    summary["regime_vols"],
        "transition_matrix": summary["transition_matrix"].tolist(),
        "current_regime": summary["current_regime"],
        "current_prob":   summary["current_prob"],
        "smoothed_probs": {
            str(d.date()): list(row)
            for d, row in zip(probs_df.index, probs_df.values)
        },
        "ivv_cumulative": {
            str(d.date()): round(float(v), 4)
            for d, v in zip(ivv_cum.index, ivv_cum.values)
        },
        "conditional_stats": {
            str(i): {
                "mean": cond_stats[i]["mean"].tolist(),
                "cov":  cond_stats[i]["cov"].tolist(),
                "n_obs": cond_stats[i]["n_obs"],
            }
            for i in cond_stats
        },
    }
    _save("regime.json", data)
    print(f"  Bull: mean={summary['regime_means'][summary['bull_regime']]:.2%}, "
          f"Bear: mean={summary['regime_means'][summary['bear_regime']]:.2%}")
    print(f"  Current regime: #{summary['current_regime']} "
          f"(prob={summary['current_prob']:.1%})")

    return summary, cond_stats


# ---------------------------------------------------------------------------
# Step 6: GARCH models
# ---------------------------------------------------------------------------
def step_garch(ret_full):
    print("\n=== Step 6: GARCH Models ===")
    from models.garch_model import fit_all_assets, conditional_volatility, forecast_vol, rolling_correlation_dcc_proxy

    garch_results = fit_all_assets(ret_full)

    cond_vols = {}
    forecasts = {}
    for ticker, res in garch_results.items():
        if res is None:
            continue
        cv = conditional_volatility(res, annualize=True)
        fv = forecast_vol(res, horizon=12, annualize=True)
        cond_vols[ticker] = {
            "dates":   [str(d.date()) for d in cv.index],
            "vol":     cv.values.tolist(),
            "current": float(cv.iloc[-1]),
            "hist_avg": float(cv.mean()),
            "percentile": float((cv <= cv.iloc[-1]).mean() * 100),
        }
        forecasts[ticker] = fv.tolist()

    # Rolling-window DCC proxy (36-month windows) on subset for dashboard
    dcc_subset = ret_full[[c for c in ["IVV", "AGG", "GLD", "VEA"] if c in ret_full.columns]]
    dcc_corr = rolling_correlation_dcc_proxy(dcc_subset, window=36)
    dcc_data = {
        str(d.date()): corr.values.tolist()
        for d, corr in list(dcc_corr.items())[-60:]  # last 5 years
    }

    data = {
        "tickers":         list(cond_vols.keys()),
        "conditional_vol": cond_vols,
        "forecasts":       forecasts,
        "dcc_tickers":     list(dcc_subset.columns),
        "dcc_correlation": dcc_data,
    }
    _save("garch.json", data)
    return garch_results


# ---------------------------------------------------------------------------
# Step 7: Simulations
# ---------------------------------------------------------------------------
def step_simulations(ret_12, frontier_results, contrib, regime_summary, regime_cond_stats, garch_results):
    print("\n=== Step 7: Simulations ===")
    from simulation.engine import run_simulation
    from analysis.risk_metrics import compute_all_metrics
    from config import CLIENT_PROFILE, UNIVERSE_12, DATE_RANGE_12
    from data.fetcher import fetch_returns

    goal = CLIENT_PROFILE["goal_amount"]
    rf_rate = 0.04
    n_paths = SIMULATION_CONFIG_PROD

    tangency_weights_12 = np.array(list(frontier_results["12"]["tangency"]["weights"][t]
                                        for t in frontier_results["12"]["tickers"]))
    tickers_12 = frontier_results["12"]["tickers"]

    modes = ["bootstrap", "parametric"]  # regime and garch added if regime_summary available
    if regime_summary is not None:
        modes.append("regime")
    if garch_results is not None:
        modes.append("garch")

    stats_12 = None
    cov_12 = None
    for mode in modes:
        print(f"  Running {mode} simulation (n={n_paths})...")
        t0 = time.time()

        if mode == "bootstrap":
            sim = run_simulation(
                mode="bootstrap",
                weights=tangency_weights_12,
                contributions=contrib,
                n_paths=n_paths,
                returns_df=ret_12[tickers_12],
            )

        elif mode == "parametric":
            if stats_12 is None:
                from models.portfolio_stats import compute_stats, compute_covariance
                stats_12 = compute_stats(ret_12[tickers_12])
                cov_12 = compute_covariance(ret_12[tickers_12])
            mu = stats_12["ann_return"].values
            cov = cov_12.values
            sim = run_simulation(
                mode="parametric",
                weights=tangency_weights_12,
                contributions=contrib,
                n_paths=n_paths,
                mu=mu,
                cov=cov,
            )

        elif mode == "regime":
            if stats_12 is None:
                from models.portfolio_stats import compute_stats, compute_covariance
                stats_12 = compute_stats(ret_12[tickers_12])
                cov_12 = compute_covariance(ret_12[tickers_12])
            # Map regime conditional stats to the tickers in use
            from models.regime_model import regime_conditional_stats
            from data.fetcher import fetch_returns as fr
            ret_full_sub = fr(tickers=["IVV", "SHV"], start="2005-01-01", end="2025-12-31")
            from models.regime_model import fit_regime_model, get_regime_summary
            re_result = fit_regime_model(ret_full_sub["IVV"], ret_full_sub.get("SHV"))
            re_summary = get_regime_summary(re_result)
            cond = regime_conditional_stats(ret_12[tickers_12], re_summary["smoothed_probs"])
            sim = run_simulation(
                mode="regime",
                weights=tangency_weights_12,
                contributions=contrib,
                n_paths=n_paths,
                regime_summary=re_summary,
                regime_cov_matrices=cond,
            )

        elif mode == "garch":
            from models.portfolio_stats import compute_correlation
            corr = compute_correlation(ret_12[tickers_12]).values
            sim = run_simulation(
                mode="garch",
                weights=tangency_weights_12,
                contributions=contrib,
                n_paths=n_paths,
                garch_results={t: garch_results.get(t) for t in tickers_12},
                correlation_matrix=corr,
                tickers=tickers_12,
            )

        elapsed = time.time() - t0
        metrics = compute_all_metrics(sim.real_paths, sim.real_terminal, goal=goal, rf_rate=rf_rate)
        bands = {
            f"p{p}": np.percentile(sim.real_paths, p, axis=0).tolist()
            for p in [5, 25, 50, 75, 95]
        }
        # Downsample paths for frontend (500 paths × every 6 months)
        sample_idx = np.random.choice(n_paths, min(500, n_paths), replace=False)
        downsample = sim.real_paths[sample_idx, ::6].tolist()

        data = {
            "mode":             mode,
            "strategy":         "tangency_12",
            "metrics":          metrics,
            "fan_chart":        bands,
            "paths_sample":     downsample,
            "terminal_hist": {
                "values": np.percentile(sim.real_terminal,
                                        np.linspace(1, 99, 100)).tolist(),
                "percentiles": np.linspace(1, 99, 100).tolist(),
            },
        }
        _save(f"simulation_{mode}_tangency_12.json", data)
        print(f"    Done in {elapsed:.1f}s — P(Goal)={metrics['p_goal']:.1%}, "
              f"Median=${metrics['median_terminal']:,.0f}")


# ---------------------------------------------------------------------------
# Step 8: Strategy comparison
# ---------------------------------------------------------------------------
def step_comparison(ret_12, contrib):
    print("\n=== Step 8: Strategy Comparison ===")
    from analysis.compare_strategies import run_all_strategies
    from config import SIMULATION_CONFIG

    df = run_all_strategies(
        returns_df=ret_12,
        contributions=contrib,
        simulation_mode="bootstrap",
        n_paths=SIMULATION_CONFIG["n_paths_dev"],
    )

    data = {
        "strategies": df.reset_index().to_dict(orient="records"),
        "columns": list(df.columns),
    }
    _save("strategy_comparison.json", data)
    print("  Comparison table saved.")
    return df


# ---------------------------------------------------------------------------
# Step 9: Risk analysis (primary strategy)
# ---------------------------------------------------------------------------
def step_risk(ret_12, contrib, frontier_results):
    print("\n=== Step 9: Risk Analysis ===")
    from simulation.bootstrap import block_bootstrap_mc
    from simulation.stress import apply_stress_scenario, STRESS_SCENARIOS
    from analysis.risk_metrics import compute_all_metrics, drawdown_series
    from config import CLIENT_PROFILE

    tickers = frontier_results["12"]["tickers"]
    w = np.array([frontier_results["12"]["tangency"]["weights"][t] for t in tickers])
    goal = CLIENT_PROFILE["goal_amount"]

    result = block_bootstrap_mc(ret_12[tickers], w, contrib, n_paths=10000)
    metrics = compute_all_metrics(result["real_paths"], result["real_terminal"], goal=goal)
    dd = drawdown_series(result["real_paths"])

    stress_results = {}
    for name in STRESS_SCENARIOS:
        try:
            sr = apply_stress_scenario(result["paths"], contrib, name)
            sr_metrics = compute_all_metrics(sr["real_paths"], sr["real_terminal"], goal=goal)
            stress_results[name] = {
                "label":  STRESS_SCENARIOS[name]["label"],
                "metrics": sr_metrics,
                "median_path": np.percentile(sr["real_paths"], 50, axis=0).tolist(),
            }
        except Exception as exc:
            print(f"    WARNING: stress scenario '{name}' failed: {exc}")

    data = {
        "strategy": "tangency_12",
        "metrics":  metrics,
        "drawdown_series": dd.tolist(),
        "stress_scenarios": stress_results,
    }
    _save("risk_tangency_12.json", data)


# ---------------------------------------------------------------------------
# Step 10: Factor analysis
# ---------------------------------------------------------------------------
def step_factor(ret_12, frontier_results):
    print("\n=== Step 10: Factor Analysis ===")
    from models.factor_model import capm_regression, ff5_regression, fetch_ff5_factors, rolling_beta
    from config import DATE_RANGE_12

    tickers = frontier_results["12"]["tickers"]
    w = np.array([frontier_results["12"]["tangency"]["weights"][t] for t in tickers])
    port_ret = (ret_12[tickers] * w).sum(axis=1).dropna()

    capm = capm_regression(port_ret, ret_12["IVV"], ret_12["SHV"])

    ff5 = fetch_ff5_factors(start=DATE_RANGE_12["start"])
    if not ff5.empty:
        ff5_result = ff5_regression(port_ret, ff5)
    else:
        ff5_result = {}

    roll_beta = rolling_beta(port_ret, ret_12["IVV"], ret_12["SHV"])

    data = {
        "strategy": "tangency_12",
        "capm": capm,
        "ff5":  ff5_result,
        "rolling_beta": {
            "dates":  [str(d.date()) for d in roll_beta.index],
            "values": roll_beta.values.tolist(),
        },
    }
    _save("factor_tangency_12.json", data)
    print(f"  CAPM alpha (ann): {capm.get('alpha_annualized', 0):.2%}, "
          f"tstat={capm.get('alpha_tstat', 0):.2f}")


# ---------------------------------------------------------------------------
# Step 11: Sensitivity sweeps
# ---------------------------------------------------------------------------
def step_sensitivity(ret_12, contrib, frontier_results):
    print("\n=== Step 11: Sensitivity Sweeps ===")
    from analysis.sensitivity import sweep_estimation_window, sweep_crypto_cap, sweep_rebalancing

    tickers = frontier_results["12"]["tickers"]
    w = np.array([frontier_results["12"]["tangency"]["weights"][t] for t in tickers])

    print("  Window sweep...")
    df_window = sweep_estimation_window(ret_12, contrib, n_paths=1000)
    _save("sensitivity_window.json", df_window.to_dict(orient="records"))

    print("  Crypto cap sweep...")
    df_crypto = sweep_crypto_cap(ret_12, contrib, n_paths=1000)
    _save("sensitivity_crypto_cap.json", df_crypto.to_dict(orient="records"))

    print("  Rebalancing sweep...")
    df_rebal = sweep_rebalancing(ret_12[tickers], w, contrib, n_paths=1000)
    _save("sensitivity_rebalancing.json", df_rebal.reset_index().to_dict(orient="records"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
SIMULATION_CONFIG_PROD = 50_000


def main(n_paths_override: int | None = None):
    global SIMULATION_CONFIG_PROD
    if n_paths_override is not None:
        SIMULATION_CONFIG_PROD = n_paths_override

    print("=" * 60)
    print("PortfolioLab — Full Pipeline")
    print("=" * 60)

    t_start = time.time()

    ret_full, ret_12     = step_fetch()
    contrib, schedule    = step_cashflows()
    stats, cov, corr     = step_asset_stats(ret_12)
    frontier_results     = step_efficient_frontiers(ret_12)
    regime_summary, cond = step_regime(ret_full)
    garch_results        = step_garch(ret_full)
    step_simulations(ret_12, frontier_results, contrib, regime_summary, cond, garch_results)
    step_comparison(ret_12, contrib)
    step_risk(ret_12, contrib, frontier_results)
    step_factor(ret_12, frontier_results)
    step_sensitivity(ret_12, contrib, frontier_results)

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Pipeline complete in {elapsed/60:.1f} minutes.")
    print(f"Results written to: {RESULTS_DIR}")
    print("\nTo start the API server, run:")
    print("  cd portfoliolab && .venv/Scripts/python -m uvicorn backend.api.server:app --reload --port 8000")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PortfolioLab master pipeline")
    parser.add_argument("--dev", action="store_true",
                        help="Use reduced n_paths=5000 for faster development runs")
    args = parser.parse_args()
    main(n_paths_override=5000 if args.dev else None)
