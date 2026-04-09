"""
PortfolioLab — Integration Test Suite

Tests:
  1. Data files  — all 17 JSON result files exist and are non-empty
  2. Backend API — all GET endpoints return 200 and expected keys
  3. Backend API — POST /api/recalculate works with a custom profile
  4. Frontend    — npm / node are available and node_modules exist

Run with:  .venv/Scripts/python test_project.py
"""

import sys
import os
import json
import subprocess
import pathlib

# Force UTF-8 output so Unicode symbols work in all terminals/pipes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── colour helpers ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = failed = skipped = 0

def ok(msg):
    global passed; passed += 1
    print(f"  {GREEN}✓{RESET}  {msg}")

def fail(msg, detail=""):
    global failed; failed += 1
    print(f"  {RED}✗{RESET}  {msg}")
    if detail:
        print(f"       {RED}{detail}{RESET}")

def skip(msg):
    global skipped; skipped += 1
    print(f"  {YELLOW}~{RESET}  {msg}")

def section(title):
    print(f"\n{BOLD}{title}{RESET}")
    print("─" * 50)


# ── 1. Data files ─────────────────────────────────────────────────────────────
section("1 · Data files (data/results/)")

RESULTS = pathlib.Path(__file__).parent / "data" / "results"

EXPECTED_FILES = [
    "client_profile.json",
    "asset_stats.json",
    "efficient_frontier_3.json",
    "efficient_frontier_5.json",
    "efficient_frontier_12.json",
    "regime.json",
    "garch.json",
    "simulation_bootstrap_tangency_12.json",
    "simulation_parametric_tangency_12.json",
    "simulation_regime_tangency_12.json",
    "simulation_garch_tangency_12.json",
    "strategy_comparison.json",
    "risk_tangency_12.json",
    "factor_tangency_12.json",
    "sensitivity_window.json",
    "sensitivity_crypto_cap.json",
    "sensitivity_rebalancing.json",
]

for fname in EXPECTED_FILES:
    p = RESULTS / fname
    if not p.exists():
        fail(fname, "File missing — run:  .venv\\Scripts\\python run_all.py --dev")
    elif p.stat().st_size < 10:
        fail(fname, "File is empty")
    else:
        ok(fname)

# spot-check key fields
checks = {
    "regime.json": ["ivv_cumulative", "smoothed_probs", "transition_matrix"],
    "garch.json":  ["tickers", "conditional_vol", "dcc_correlation"],
    "efficient_frontier_12.json": ["tangency", "frontier"],
    "risk_tangency_12.json": ["metrics", "stress_scenarios", "drawdown_series"],
    "strategy_comparison.json": ["strategies"],
}
for fname, keys in checks.items():
    p = RESULTS / fname
    if not p.exists():
        continue
    data = json.loads(p.read_text())
    missing = [k for k in keys if k not in data]
    if missing:
        fail(f"{fname} — missing keys: {missing}")
    else:
        ok(f"{fname} — required keys present")


# ── 2. Backend API ─────────────────────────────────────────────────────────────
section("2 · Backend API (http://localhost:8000)")

try:
    import urllib.request, urllib.error

    def get(path, timeout=2):
        req = urllib.request.Request(f"http://localhost:8000{path}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())

    def post(path, payload, timeout=15):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"http://localhost:8000{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())

    # health
    status, body = get("/api/health")
    if status == 200 and body.get("status") == "ok":
        ok("GET /api/health → 200 ok")
    else:
        fail("GET /api/health", f"status={status}")

    # all GET endpoints
    ENDPOINTS = [
        ("/api/client-profile",                       ["profile"]),
        ("/api/asset-stats",                          ["tickers", "stats", "correlation"]),
        ("/api/efficient-frontier?universe=12",       ["tangency", "frontier"]),
        ("/api/regime",                               ["smoothed_probs", "ivv_cumulative"]),
        ("/api/garch",                                ["tickers", "conditional_vol"]),
        ("/api/simulation?mode=bootstrap&strategy=tangency_12", ["metrics", "fan_chart"]),
        ("/api/comparison",                           ["strategies"]),
        ("/api/risk?strategy=tangency_12",            ["metrics", "stress_scenarios"]),
        ("/api/factor?strategy=tangency_12",          ["capm"]),
        ("/api/sensitivity?param=window",             []),
    ]

    for path, required_keys in ENDPOINTS:
        try:
            status, body = get(path)
            if status != 200:
                fail(f"GET {path}", f"HTTP {status}")
                continue
            missing = [k for k in required_keys if k not in body]
            if missing:
                fail(f"GET {path}", f"missing keys: {missing}")
            else:
                ok(f"GET {path}")
        except (urllib.error.URLError, OSError) as e:
            fail(f"GET {path}", str(e))

    # POST /api/recalculate (skipped by default — slow: downloads live prices)
    # To enable:  python test_project.py --recalculate
    if "--recalculate" in sys.argv:
        try:
            custom_profile = {
                "starting_salary": 120000,
                "salary_growth_rate": 0.05,
                "tax_rate": 0.30,
                "annual_expenses": 60000,
                "loan_balance": 30000,
                "loan_rate": 0.065,
                "emergency_fund_months": 6,
                "goal_amount": 2000000,
                "investment_horizon_years": 10,
                "initial_investment": 50000,
            }
            status, body = post("/api/recalculate", custom_profile, timeout=90)
            if status != 200:
                fail("POST /api/recalculate", f"HTTP {status}")
            elif "metrics" not in body or "fan_chart" not in body:
                fail("POST /api/recalculate", f"missing keys: {list(body.keys())}")
            else:
                ok("POST /api/recalculate → metrics, fan_chart present")
        except Exception as e:
            fail("POST /api/recalculate", str(e))
    else:
        skip("POST /api/recalculate (add --recalculate flag to test this)")

except (urllib.error.URLError, OSError):
    skip("API server not reachable — start it first:")
    skip("  .venv/Scripts/python -m uvicorn backend.api.server:app --reload --port 8000")


# ── 3. Frontend build ──────────────────────────────────────────────────────────
section("3 · Frontend (Node.js / npm)")

FRONTEND = pathlib.Path(__file__).parent / "frontend"

# Node.js installed?
try:
    r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        ok(f"node {r.stdout.strip()} found")
    else:
        fail("node not found", "Install from https://nodejs.org (LTS)")
except FileNotFoundError:
    fail("node not found", "Install from https://nodejs.org (LTS)")

# npm installed?
npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
try:
    r = subprocess.run([npm_cmd, "--version"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        ok(f"npm {r.stdout.strip()} found")
    else:
        fail("npm not found")
except FileNotFoundError:
    fail("npm not found")

# node_modules exist?
nm = FRONTEND / "node_modules"
if nm.exists() and any(nm.iterdir()):
    ok("node_modules/ present")
else:
    fail("node_modules/ missing", "Run:  cd frontend && npm install")

# vite config present?
if (FRONTEND / "vite.config.js").exists():
    ok("vite.config.js present")
else:
    fail("vite.config.js missing")


# ── Summary ────────────────────────────────────────────────────────────────────
total = passed + failed + skipped
print(f"\n{'─'*50}")
print(f"{BOLD}Results:{RESET}  "
      f"{GREEN}{passed} passed{RESET}  "
      f"{RED}{failed} failed{RESET}  "
      f"{YELLOW}{skipped} skipped{RESET}  "
      f"(total {total})")

if failed > 0:
    print(f"\n{RED}Some checks failed — see details above.{RESET}")
    sys.exit(1)
else:
    print(f"\n{GREEN}All checks passed.{RESET}")
