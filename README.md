# PortfolioLab

## Authors

| Name | Contribution |
|------|--------------|
| Yuhao Ren | Quantitative models, data pipeline |
| James Wu | Python backend, FastAPI, React frontend (JavaScript/JSX) |

---

A full-stack quantitative finance platform for personal wealth planning. Combines mean-variance optimisation, Markov regime-switching, GARCH volatility modelling, and block-bootstrap Monte Carlo simulations into a single interactive dashboard.

---

## Architecture

```
portfoliolab/
├── backend/
│   ├── config.py              # Global parameters (tickers, client profile, sim config)
│   ├── data/
│   │   ├── fetcher.py         # Yahoo Finance monthly returns + CSV cache
│   │   └── crypto_fetcher.py  # BTC/ETH data handler
│   ├── client/
│   │   └── cashflows.py       # Savings schedule, contributions, loan amortisation
│   ├── models/
│   │   ├── portfolio_stats.py # Ann. return/vol/Sharpe/drawdown/skew/kurt
│   │   ├── efficient_frontier.py  # Tangency, min-var, efficient frontier (SLSQP)
│   │   ├── regime_model.py    # Hamilton 2-state Markov-switching (statsmodels)
│   │   ├── garch_model.py     # GARCH(1,1) per-asset + DCC rolling correlation
│   │   ├── factor_model.py    # CAPM + Fama-French 5-factor regressions
│   │   └── glide_path.py      # Linear equity→bond glide path weights
│   ├── simulation/
│   │   ├── bootstrap.py       # Block-bootstrap MC with rebalancing
│   │   ├── parametric.py      # Parametric, regime-conditional, GARCH MC
│   │   ├── stress.py          # 5 stress scenarios (GFC, COVID, stagflation, …)
│   │   └── engine.py          # Unified SimulationResult dispatcher
│   ├── analysis/
│   │   ├── risk_metrics.py    # Sharpe/Sortino/Calmar/VaR/CVaR/P(Goal)
│   │   ├── compare_strategies.py  # 9 pre-defined strategies
│   │   ├── sensitivity.py     # Window / crypto-cap / rebalancing sweeps
│   │   └── rebalancing.py     # Rebalancing frequency comparison
│   └── api/
│       └── server.py          # FastAPI — 12 endpoints, serves data/results/*.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Page routing (9 pages)
│   │   ├── components/
│   │   │   ├── Layout/        # Sidebar nav + regime pill
│   │   │   ├── Dashboard/     # Hero metrics + fan sparkline + donut
│   │   │   ├── ClientProfile/ # Editable sliders → POST /api/recalculate
│   │   │   ├── AssetUniverse/ # Cards / scatter / correlation heatmap
│   │   │   ├── EfficientFrontier/  # Interactive frontier + weight bars
│   │   │   ├── Simulation/    # Fan chart + terminal histogram (4 modes)
│   │   │   ├── RegimeAnalysis/# Probability timeline + transition matrix
│   │   │   ├── VolatilityDynamics/ # GARCH vol chart + term structure
│   │   │   ├── RiskAnalysis/  # Drawdown + VaR/CVaR + stress table
│   │   │   └── FactorAnalysis/# CAPM table + FF5 bars + rolling beta
│   │   ├── hooks/
│   │   │   └── usePortfolioData.js  # All API hooks + recalculate()
│   │   └── theme/
│   │       └── tokens.js      # Color tokens, chart series, design system
│   ├── package.json
│   └── vite.config.js         # /api proxy → localhost:8000
├── data/
│   ├── cache/                 # CSV price cache (auto-populated)
│   └── results/               # JSON exports from run_all.py
├── run_all.py                 # Master 11-step pipeline
└── requirements.txt
```

---

## Asset Universe

| Ticker | Name | Class |
|--------|------|-------|
| IVV | iShares S&P 500 | US Equity |
| QUAL | iShares MSCI Quality | US Equity Factor |
| USMV | iShares Min Volatility | US Equity Factor |
| VEA | Vanguard Developed | Intl Equity |
| VWO | Vanguard Emerging | Intl Equity |
| AGG | iShares Core US Agg Bond | Fixed Income |
| SHV | iShares Short Treasury | Fixed Income |
| TIP | iShares TIPS Bond | Inflation-Linked |
| VNQ | Vanguard REIT | Real Assets |
| GLD | SPDR Gold Shares | Commodities |
| BTC-USD | Bitcoin | Crypto (≤5%) |
| ETH-USD | Ethereum | Crypto (≤5%) |

---

## Quick Start

### 1. Python backend

```powershell
# Create and activate virtual environment
cd C:\Users\yuhao\Documents\portfolio_research\portfoliolab

# Run the full pipeline (50,000 paths — ~10 min)
.\.venv\Scripts\python run_all.py

# Or use dev mode (5,000 paths — ~1 min)
.\.venv\Scripts\python run_all.py --dev
```

This writes JSON files to `data/results/`:
- `asset_stats.json`, `efficient_frontier_3/5/12.json`
- `regime.json`, `garch.json`, `factor.json`
- `simulation_bootstrap/parametric/regime/garch.json`
- `comparison.json`, `risk.json`, `sensitivity.json`

### 2. Start the API server

```powershell
.\.venv\Scripts\python -m uvicorn backend.api.server:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend (requires Node.js ≥ 18)

Download Node.js from https://nodejs.org if not installed, then:

```powershell
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

The Vite dev server proxies `/api/*` → `localhost:8000`.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/client-profile` | Current client profile + savings schedule |
| GET | `/api/asset-stats` | Per-asset return/vol/Sharpe/drawdown |
| GET | `/api/efficient-frontier?universe=12` | Frontier points + portfolios |
| GET | `/api/regime` | Regime summary + smoothed probabilities |
| GET | `/api/garch` | GARCH conditional vol + forecasts |
| GET | `/api/simulation?mode=bootstrap&strategy=tangency_12` | MC fan chart data |
| GET | `/api/comparison` | Strategy comparison table |
| GET | `/api/risk?strategy=tangency_12` | Risk metrics + drawdown series |
| GET | `/api/factor` | CAPM + FF5 regression results |
| GET | `/api/sensitivity` | Parameter sweep results |
| POST | `/api/recalculate` | Rerun simulations with updated profile |

---

## Simulation Modes

| Mode | Description |
|------|-------------|
| `bootstrap` | Block-bootstrap (12-month blocks) — preserves autocorrelation |
| `parametric` | Multivariate normal with historical μ/Σ |
| `regime` | Markov chain–driven regime-conditional returns |
| `garch` | GARCH(1,1) forward simulation with Cholesky correlation |

---

## Development Notes

- Crypto allocation is capped at 5% by the optimiser constraint (`OPT_CONSTRAINTS`)
- Block-bootstrap uses 12-month blocks to preserve regime autocorrelation
- Regime model is fit on IVV (S&P 500 proxy) monthly excess returns over SHV
- FF5 factors are downloaded from Ken French's data library via `pandas_datareader`
- All heavy computation is done once by `run_all.py`; the API only serves cached JSON
