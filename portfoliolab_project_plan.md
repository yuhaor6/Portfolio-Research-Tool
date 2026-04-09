# PortfolioLab — Advanced Portfolio Optimization & Simulation Platform
## Project Plan for AI Agent Execution

---

## 0. Project Identity

**Name:** PortfolioLab  
**Tagline:** Research-grade portfolio simulation with institutional-quality visualization  
**Repo:** `portfoliolab`  
**What it is:** A Python backend that runs serious quantitative portfolio analysis (regime-switching models, GARCH volatility, multi-asset optimization, Monte Carlo with 50k+ paths) paired with a React dashboard that makes the results explorable and visually stunning.  
**Target audience:** Quant finance recruiting portfolio piece. Should look like something a systematic fund's research team would build internally.

---

## 1. Architecture Overview

```
portfoliolab/
│
├── backend/                     # Pure Python — all computation
│   ├── config.py                # Global parameters, asset universe, client profile
│   ├── data/
│   │   ├── fetcher.py           # Download & cache return data (yfinance, FRED, French library)
│   │   ├── crypto_fetcher.py    # Crypto-specific data (BTC, ETH via yfinance or CoinGecko)
│   │   └── cache/               # Local CSV cache so we don't re-download
│   │
│   ├── client/
│   │   └── cashflows.py         # Income, tax, expenses, loan, savings projection
│   │
│   ├── models/
│   │   ├── portfolio_stats.py   # Mean, vol, cov, corr, Sharpe, drawdown utilities
│   │   ├── efficient_frontier.py # MV optimization, tangency, Black-Litterman (optional)
│   │   ├── regime_model.py      # Hamilton 2-state Markov-switching model
│   │   ├── garch_model.py       # GARCH(1,1) and DCC-GARCH for dynamic vol/corr
│   │   ├── factor_model.py      # CAPM alpha, FF5 regressions
│   │   └── glide_path.py        # Time-varying allocation schedules
│   │
│   ├── simulation/
│   │   ├── bootstrap.py         # Block bootstrap Monte Carlo engine
│   │   ├── parametric.py        # Parametric MC (normal, regime-conditional, GARCH-filtered)
│   │   ├── stress.py            # Stress scenario injection
│   │   └── engine.py            # Unified simulation interface — dispatches to bootstrap or parametric
│   │
│   ├── analysis/
│   │   ├── compare_strategies.py # Run N strategies through simulation, collect metrics
│   │   ├── risk_metrics.py      # VaR, CVaR, max drawdown, Sortino, Calmar
│   │   ├── sensitivity.py       # Estimation window, parameter sweep
│   │   └── rebalancing.py       # Rebalancing frequency comparison
│   │
│   ├── api/
│   │   └── server.py            # FastAPI server — exposes all results as JSON endpoints
│   │
│   └── run_all.py               # Master script: fetch data → fit models → run simulations → export JSON
│
├── frontend/                    # React + Recharts/D3 dashboard
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── theme/               # Design tokens, colors, fonts
│   │   ├── components/
│   │   │   ├── Layout/          # Shell, sidebar, nav
│   │   │   ├── Dashboard/       # Main overview page
│   │   │   ├── ClientProfile/   # Editable income/expense/goal inputs
│   │   │   ├── AssetUniverse/   # Asset cards, return stats, correlation heatmap
│   │   │   ├── EfficientFrontier/ # Interactive frontier plot
│   │   │   ├── Simulation/      # Wealth fan chart, terminal distribution
│   │   │   ├── RegimeAnalysis/  # Regime probability timeline, regime-conditional stats
│   │   │   ├── RiskAnalysis/    # Drawdown, VaR/CVaR, stress tests
│   │   │   ├── StrategyComparison/ # Side-by-side strategy table + charts
│   │   │   └── FactorAnalysis/  # CAPM alpha, FF5 decomposition
│   │   └── hooks/
│   │       └── usePortfolioData.js # Fetch from FastAPI backend
│   │
│   └── public/
│
├── data/                        # Shared data directory (backend writes, frontend reads)
│   └── results/                 # JSON exports from backend
│
├── requirements.txt             # Python deps
├── README.md
└── .gitignore
```

---

## 2. Expanded Asset Universe (12 Assets)

### Core Equities
| Ticker | Name | Role | Justification |
|--------|------|------|---------------|
| IVV | iShares S&P 500 | U.S. large-cap equity | Market portfolio proxy, CAPM benchmark |
| QUAL | iShares MSCI USA Quality | Quality factor tilt | Positive historical alpha (Hollifield slide 21) |
| USMV | iShares MSCI USA Min Vol | Low-vol factor tilt | Highest single-asset Sharpe in original analysis |
| VEA | Vanguard FTSE Developed Markets | International developed equity | Diversification beyond U.S.; different business cycle exposure |
| VWO | Vanguard FTSE Emerging Markets | Emerging market equity | Low correlation with U.S., higher growth potential, higher vol |

### Fixed Income
| Ticker | Name | Role | Justification |
|--------|------|------|---------------|
| AGG | iShares Core U.S. Agg Bond | Investment-grade bonds | Core bond diversifier, near-zero equity correlation |
| SHV | iShares Short Treasury | Risk-free / cash proxy | Emergency fund, risk-free allocation |
| TIP | iShares TIPS Bond | Inflation-protected | Direct inflation hedge — addresses the inflation stress test |

### Alternatives
| Ticker | Name | Role | Justification |
|--------|------|------|---------------|
| VNQ | Vanguard Real Estate | U.S. REITs | Real asset exposure, income-generating, moderate equity correlation |
| GLD | SPDR Gold Shares | Gold / commodity | Crisis hedge, low/negative equity correlation in stress periods |
| BTC-USD | Bitcoin | Crypto (large-cap) | High return, high vol, low-but-unstable correlation with traditional assets. Inception: 2014 on Yahoo Finance |
| ETH-USD | Ethereum | Crypto (smart contract) | Second-largest crypto, different risk profile from BTC. Inception: 2017 |

### Data Availability & Handling
- **Full history (2005–2025):** IVV, AGG, SHV, VEA, VWO, VNQ, GLD, TIP — 20 years
- **Partial history:** QUAL (2013+), USMV (2011+), BTC-USD (2014+), ETH-USD (2017+)
- **Strategy:** Use the longest available common window for each analysis. For the full 12-asset MV optimization, use 2017–2025 (all assets available). For regime and GARCH models, use IVV/AGG/GLD/VEA with the full 2005–2025 history.
- **Crypto handling:** Cap crypto allocation at 5% in optimization constraints (realistic for a new grad client). Crypto returns are extremely non-normal — this is exactly where GARCH and regime models add value.

---

## 3. Modeling Stack

### 3.1 Regime-Switching Model (Hamilton Markov-Switching)

**What it does:** Estimates a 2-state (bull/bear) Markov-switching model on equity returns. Each regime has its own mean and variance. Transition probabilities govern how likely the market is to stay in or switch between regimes.

**Implementation:**
- Use `statsmodels.tsa.regime_switching.markov_regression.MarkovRegression`
- Fit on IVV monthly excess returns (vs SHV)
- Extract: regime means (μ_bull, μ_bear), regime vols (σ_bull, σ_bear), transition matrix P
- Compute smoothed regime probabilities for each historical month

**How it feeds into the project:**
1. **Regime-conditional statistics:** Show that the covariance matrix is *different* in bull vs. bear markets (correlations spike in crises). This is why static MV optimization can fail.
2. **Regime-aware simulation:** In the parametric MC, draw returns from the regime-conditional distribution. Each simulated path follows a Markov chain: the regime at time t determines which (μ, σ) to draw from, and the transition matrix governs regime switches.
3. **Dashboard visualization:** A timeline showing regime probabilities overlaid on cumulative returns — immediately reveals that 2008–09, 2020 March, and 2022 were "bear regime" periods.

**Estimated effort:** ~80–100 lines in `regime_model.py`

### 3.2 GARCH(1,1) + DCC-GARCH

**What it does:** Models time-varying volatility (GARCH) and time-varying correlations (DCC) for each asset.

**Implementation:**
- Use `arch` library for univariate GARCH(1,1) on each asset
- Use `arch` or manual DCC estimation for dynamic conditional correlations
- Extract: conditional volatility series for each asset, dynamic correlation matrices

**How it feeds into the project:**
1. **GARCH-filtered simulation:** Instead of drawing from a static covariance matrix, simulate forward using the GARCH process. Each step updates conditional vol based on the previous return, producing realistic volatility clustering.
2. **Current regime assessment:** The most recent GARCH conditional vol tells you whether you're in a high-vol or low-vol environment *right now*. This can inform the initial allocation recommendation.
3. **Dashboard visualization:** Time series of conditional volatility for each asset, with the current level highlighted. Dynamic correlation heatmap that changes over time (animated or slider-controlled).

**Estimated effort:** ~100–120 lines in `garch_model.py`

### 3.3 Simulation Engine (Unified)

Three simulation modes, all producing the same output format (array of terminal wealth values + full path data):

| Mode | Method | When to Use |
|------|--------|-------------|
| **Block Bootstrap** | Resample 12-month historical blocks | Default. Non-parametric, preserves all dependencies. |
| **Parametric Normal** | Draw from estimated (μ, Σ) | Baseline comparison. Fast, but misses fat tails. |
| **Regime-Conditional** | Markov chain drives regime → draw from regime-specific (μ, Σ) | Shows impact of regime uncertainty on tail risk. |
| **GARCH-Filtered** | Simulate GARCH process forward, draw standardized residuals | Shows impact of volatility clustering. |

**Paths:** 50,000 for production runs (takes ~30 seconds with vectorized numpy). 5,000 for development/debugging.

**Output per path:** Monthly portfolio values (120 months), regime states (if applicable), contribution schedule applied.

### 3.4 Risk Metrics Module

| Metric | Definition | Dashboard Display |
|--------|-----------|-------------------|
| Sharpe Ratio | (E[r] − r_f) / σ | Bar chart across strategies |
| Sortino Ratio | (E[r] − r_f) / σ_downside | Better for asymmetric returns (crypto) |
| Max Drawdown | Largest peak-to-trough decline | Time series + distribution |
| Value-at-Risk (5%) | 5th percentile of return distribution | Single number per strategy |
| Conditional VaR (CVaR) | Average return below VaR | Captures tail severity |
| Calmar Ratio | Annualized return / Max drawdown | Drawdown-adjusted performance |
| Goal Attainment | P[real terminal wealth ≥ goal] | The headline number |

---

## 4. Interactive Dashboard Design

### 4.1 Tech Stack
- **Framework:** React 18 + Vite
- **Charts:** Recharts for standard charts, D3 for the efficient frontier (needs custom interaction), Plotly.js for 3D surface plots (optional)
- **Styling:** Tailwind CSS + custom design tokens
- **Data flow:** Backend exports JSON to `data/results/` → Frontend reads via FastAPI or static JSON
- **Deployment:** Can run locally (FastAPI + Vite dev server) or deploy to Vercel (frontend) + Railway (backend)

### 4.2 Pages / Views

**Page 1: Dashboard Overview**
- Hero metric cards: P(Goal), median terminal wealth, recommended allocation pie chart, current regime indicator
- Sparkline charts: 10-year wealth projection (median + bands), savings contribution timeline
- Quick summary of recommendation

**Page 2: Client Profile (Editable)**
- Sliders/inputs for: starting salary, growth rate, expenses, loan balance, goal amount, time horizon, risk tolerance
- Real-time recalculation of savings schedule
- This is what makes it a *tool*, not just a report

**Page 3: Asset Universe**
- Asset cards with key stats (return, vol, Sharpe, max drawdown)
- Interactive correlation heatmap — hover to see exact values
- Historical cumulative return chart (all assets overlaid, log scale)
- Toggle between full history and sub-periods

**Page 4: Efficient Frontier**
- Interactive scatter plot: σ vs E[r]
- Individual assets as labeled dots
- Efficient frontier curve (no short sales)
- Tangency portfolio highlighted with CAL line drawn through it
- Click any point on the frontier to see its weights
- Toggle: 3-asset / 5-asset / 12-asset universe
- Toggle: with/without crypto

**Page 5: Regime Analysis**
- Timeline: smoothed regime probabilities overlaid on IVV cumulative return
- Table: regime-conditional statistics (μ, σ, correlation matrix per regime)
- Regime transition matrix visualization
- Current regime indicator with confidence level

**Page 6: Volatility Dynamics (GARCH)**
- Time series: conditional volatility for each asset
- Dynamic correlation heatmap with time slider
- Current vol level vs historical percentile
- Vol-of-vol chart (second moment of GARCH process)

**Page 7: Simulation Results**
- Wealth fan chart: median + 5/25/75/95 percentile bands
- Terminal wealth histogram with goal line
- Toggle between simulation modes (bootstrap / parametric / regime / GARCH)
- Comparison view: overlay fan charts for different strategies
- Table: full strategy comparison (all metrics)

**Page 8: Risk Analysis**
- Drawdown chart (time series)
- VaR/CVaR comparison across strategies (bar chart)
- Stress test results table
- Stress scenario wealth paths (show the 3 scenarios as distinct colored paths)

**Page 9: Factor Analysis**
- CAPM regression results table with significance indicators
- FF5 factor loading bar chart
- Rolling beta chart (12-month rolling window)
- Alpha decomposition: "where does the portfolio's return come from?"

### 4.3 Design Direction

**Aesthetic:** Dark-mode financial terminal. Think Bloomberg Terminal meets modern data viz.  
- **Background:** Near-black (#0a0a0f) with subtle noise texture
- **Accent:** Electric cyan (#00d4ff) for primary metrics, warm amber (#ff9f43) for warnings/risk
- **Typography:** JetBrains Mono for numbers/data, a clean sans-serif (DM Sans or Satoshi) for labels
- **Cards:** Frosted glass effect (backdrop-blur) with subtle border glow
- **Charts:** Dark theme with cyan/amber/white palette. No grid lines — minimal, data-forward
- **Animations:** Smooth number counting on metric cards. Chart lines draw in on page load. Subtle parallax on scroll.

This should look like a tool someone at Citadel or Two Sigma would use internally, not a cookie-cutter dashboard.

---

## 5. AI Agent Execution Plan

### Philosophy
Each phase produces a **working, testable artifact**. The agent should never write more than ~200 lines without running tests. Every phase ends with a verification step.

### Phase 1: Project Skeleton & Data Pipeline
**Agent Instructions:**
```
1. Create the full directory structure as specified in Section 1.
2. Create requirements.txt:
   numpy, pandas, scipy, matplotlib, yfinance, pandas_datareader,
   statsmodels, arch, scikit-learn, fastapi, uvicorn
3. Create config.py with:
   - ASSET_TICKERS dict (all 12 assets with metadata)
   - CLIENT_PROFILE dict (salary, growth, tax, expenses, loan, goal, horizon)
   - SIMULATION_CONFIG (n_paths=50000, block_size=12, inflation=0.025)
   - DATE_RANGE (start='2005-01-01', end='2025-12-31')
4. Create data/fetcher.py:
   - fetch_returns(tickers, start, end) → DataFrame of monthly total returns
   - Handle missing data: forward-fill up to 3 months, then drop
   - Cache to data/cache/{ticker}.csv to avoid re-downloading
   - Special handling for crypto tickers (BTC-USD, ETH-USD)
5. Create data/crypto_fetcher.py:
   - Same interface but handles crypto-specific issues (24/7 trading, monthly resampling)
6. Create client/cashflows.py:
   - generate_savings_schedule(config) → DataFrame with year-by-year savings
7. VERIFY: Run fetcher, print shape and date range for each asset. Run cashflows, print table.
```

**Deliverable:** All data downloads successfully. Savings table matches the original report.

---

### Phase 2: Portfolio Statistics & Efficient Frontier
**Agent Instructions:**
```
1. Create models/portfolio_stats.py:
   - compute_stats(returns_df, rf_ticker='SHV') → dict of ann. return, vol, Sharpe per asset
   - compute_covariance(returns_df) → annualized covariance matrix
   - compute_correlation(returns_df) → correlation matrix
   - max_drawdown(cumulative_returns_series) → float

2. Create models/efficient_frontier.py:
   - tangency_portfolio(mu, cov, rf, bounds=None) → weights, sharpe, ret, vol
   - efficient_frontier(mu, cov, rf, n_points=100, bounds=None) → list of (vol, ret, weights)
   - Use scipy.optimize.minimize with SLSQP
   - Support arbitrary subsets of the asset universe (3, 5, 12 assets)
   - For 12-asset optimization, add constraint: crypto allocation ≤ 5%

3. VERIFY:
   - Print stats table. Compare IVV Sharpe to original report (~0.80).
   - Print tangency weights for 3-asset, 5-asset, 12-asset universes.
   - Sanity check: tangency Sharpe should increase as universe expands.
```

**Deliverable:** Stats tables, tangency portfolios for 3 universe sizes.

---

### Phase 3: Regime-Switching Model
**Agent Instructions:**
```
1. Create models/regime_model.py:
   - fit_regime_model(equity_returns, n_regimes=2) → fitted model object
   - Extract: regime_means, regime_vols, transition_matrix, smoothed_probabilities
   - get_current_regime(model) → (regime_id, probability)
   - regime_conditional_stats(all_returns, regime_probs, threshold=0.8)
     → compute mean vector and covariance matrix for each regime
     (use only months where regime probability > threshold)

2. Fit on IVV excess returns (vs SHV), full sample 2005–2025.

3. VERIFY:
   - Print regime means and vols. Bear regime should have negative mean, ~2x vol.
   - Print transition matrix. Diagonal should be >0.9 (regimes are persistent).
   - Plot smoothed probabilities — 2008-09, March 2020, early 2022 should show bear.
   - Print regime-conditional correlation matrix for IVV/AGG — should show
     correlation spike in bear regime.
```

**Deliverable:** Fitted regime model, regime probabilities, regime-conditional statistics.

---

### Phase 4: GARCH Model
**Agent Instructions:**
```
1. Create models/garch_model.py:
   - fit_garch(returns_series, p=1, q=1) → arch model result
   - conditional_volatility(model_result) → Series of conditional vol
   - forecast_vol(model_result, horizon=12) → array of forecasted monthly vols
   - fit_all_assets(returns_df) → dict of {ticker: model_result}

2. For DCC (Dynamic Conditional Correlation):
   - Standardize each asset's returns by its GARCH conditional vol
   - Estimate DCC parameters on standardized residuals
   - Output: time-varying correlation matrix series
   - If DCC estimation is too complex, use rolling 36-month correlation as fallback

3. VERIFY:
   - Print current conditional vol for each asset vs historical average.
   - BTC/ETH should have highest conditional vol.
   - Plot conditional vol for IVV — should spike in 2008, 2020, 2022.
```

**Deliverable:** GARCH conditional vol series for all assets, DCC correlation matrices.

---

### Phase 5: Simulation Engine
**Agent Instructions:**
```
1. Create simulation/bootstrap.py:
   - block_bootstrap_mc(returns_df, weights, contributions, n_paths, block_size=12,
                         inflation=0.025, horizon_years=10, rebalance='annual')
   - Returns: paths array (n_paths × 120 months), terminal_wealth array
   - Must handle: monthly contributions (spread annual savings across 12 months),
     rebalancing at specified frequency, inflation deflation

2. Create simulation/parametric.py:
   - parametric_mc(mu, cov, weights, contributions, n_paths, ...)
   - Same interface but draws from multivariate normal
   - regime_mc(regime_model, regime_cov_matrices, weights, contributions, n_paths, ...)
   - Simulates Markov chain → draws from regime-conditional distribution
   - garch_mc(garch_models, weights, contributions, n_paths, ...)
   - Simulates GARCH process forward for each asset, applies correlation structure

3. Create simulation/engine.py:
   - run_simulation(mode='bootstrap'|'parametric'|'regime'|'garch', **kwargs)
   - Unified interface that dispatches to the right engine
   - Returns standardized SimulationResult object with:
     paths, terminal_wealth, monthly_contributions, weights_used, metadata

4. Create simulation/stress.py:
   - inject_crash(paths, year, severity=-0.35) → modified paths
   - inject_job_loss(contributions, year, duration_months=12) → modified contributions
   - inject_inflation(terminal_wealth, actual_inflation) → re-deflated wealth

5. VERIFY:
   - Run bootstrap with 1000 paths, print terminal wealth quantiles.
   - Run parametric, compare quantiles — should be similar but with thinner tails.
   - Run regime MC — should show fatter left tail (bear regime produces crashes).
   - Run GARCH MC — should show volatility clustering in paths.
   - Verify: 50,000 paths completes in < 60 seconds.
```

**Deliverable:** All four simulation modes working. Comparison table of terminal wealth quantiles across modes.

---

### Phase 6: Analysis & Strategy Comparison
**Agent Instructions:**
```
1. Create analysis/risk_metrics.py:
   - compute_all_metrics(paths, terminal_wealth, goal, rf_rate)
   - Returns dict: sharpe, sortino, max_drawdown_median, max_drawdown_5pct,
     var_5, cvar_5, calmar, p_goal, mean, median, p5, p25, p75, p95

2. Create analysis/compare_strategies.py:
   - Define strategy list:
     a. All Cash (100% SHV)
     b. All Equity (100% IVV)
     c. 60/40 IVV/AGG
     d. Tangency 3-asset (IVV/AGG/SHV)
     e. Tangency 5-asset (+ QUAL/USMV)
     f. Tangency 12-asset (full universe)
     g. Tangency 12-asset + glide path
     h. Equal-weight 12-asset
     i. Risk parity (weight inversely proportional to vol)
   - Run each through all 4 simulation modes
   - Produce comparison DataFrame: strategies × metrics × simulation_modes

3. Create analysis/sensitivity.py:
   - Sweep estimation windows: 2005-2025, 2010-2025, 2015-2025, 2005-2015
   - Sweep crypto cap: 0%, 2%, 5%, 10%
   - Sweep rebalancing frequency: none, quarterly, annual
   - For each sweep, re-run tangency optimization + bootstrap simulation

4. Create analysis/rebalancing.py:
   - Run bootstrap sim with: no rebalance, quarterly, semi-annual, annual
   - Compare terminal wealth distributions

5. VERIFY:
   - Strategy comparison table should show tangency 12-asset dominates on Sharpe.
   - Risk parity should have lowest drawdown but lower P(Goal).
   - Crypto inclusion should widen the distribution (fatter tails).
```

**Deliverable:** Full strategy comparison table, sensitivity sweep results, rebalancing analysis.

---

### Phase 7: FastAPI Backend
**Agent Instructions:**
```
1. Create api/server.py:
   - GET /api/client-profile → savings schedule
   - GET /api/asset-stats → return stats, correlations
   - GET /api/efficient-frontier?universe=3|5|12 → frontier points + tangency
   - GET /api/regime → regime probabilities, regime stats
   - GET /api/garch → conditional vol series, current vol
   - GET /api/simulation?mode=bootstrap&strategy=tangency_12 → paths, terminal dist
   - GET /api/comparison → full strategy comparison table
   - GET /api/risk?strategy=tangency_12 → risk metrics, drawdown
   - GET /api/factor → CAPM alpha, FF5 loadings
   - GET /api/sensitivity?param=window → sensitivity results
   - POST /api/recalculate → accept modified client profile, re-run everything

2. Create run_all.py:
   - Master pipeline: fetch → stats → regime → garch → simulate → analyze → export
   - Export all results as JSON to data/results/
   - Also start FastAPI server

3. VERIFY:
   - Start server, hit each endpoint with curl, verify JSON structure.
   - /api/simulation should return within 5 seconds (pre-computed).
```

**Deliverable:** Working API serving all computed results.

---

### Phase 8: Frontend — Scaffolding & Core Pages
**Agent Instructions:**
```
1. Initialize React project with Vite:
   npm create vite@latest frontend -- --template react
   cd frontend && npm install recharts d3 tailwindcss @headlessui/react lucide-react

2. Set up design system:
   - Dark theme tokens in theme/tokens.js
   - Color palette: bg #0a0a0f, surface #141419, border #1e1e2a,
     cyan #00d4ff, amber #ff9f43, green #00c853, red #ff4444, text #e0e0e8
   - Typography: JetBrains Mono (numbers), DM Sans (labels)
   - Card component with frosted glass effect
   - Metric card component (value, label, delta, sparkline)

3. Build Layout:
   - Sidebar nav with page icons
   - Top bar with project name + current regime indicator
   - Content area with smooth page transitions

4. Build Dashboard page (Page 1):
   - Hero metrics: P(Goal), median wealth, Sharpe, current regime
   - Savings trajectory sparkline
   - Recommended allocation donut chart
   - Quick recommendation text

5. Build Asset Universe page (Page 3):
   - Asset cards grid
   - Correlation heatmap (Recharts or D3)
   - Cumulative return chart (all assets, log scale, toggleable)

6. VERIFY: Pages render with mock data. No API calls yet — use hardcoded JSON.
```

**Deliverable:** Working dashboard shell with 2 pages, dark theme, professional design.

---

### Phase 9: Frontend — Interactive Charts
**Agent Instructions:**
```
1. Build Efficient Frontier page (Page 4):
   - D3 scatter plot with efficient frontier curve
   - Click frontier point → show weights in side panel
   - Toggle universe size (3/5/12 assets)
   - Tangency portfolio highlighted, CAL line drawn
   - Smooth transitions when toggling universe

2. Build Simulation page (Page 7):
   - Wealth fan chart: Recharts AreaChart with percentile bands
   - Toggle simulation mode (bootstrap/parametric/regime/GARCH)
   - Terminal wealth histogram
   - Goal line overlay
   - Strategy selector dropdown

3. Build Regime page (Page 5):
   - Timeline chart: regime probability (area chart) + cumulative return (line overlay)
   - Regime stats cards (bull vs bear)
   - Transition matrix heatmap

4. Build Risk page (Page 8):
   - Drawdown time series chart
   - VaR/CVaR comparison bar chart
   - Stress test results table with conditional formatting

5. VERIFY: All charts render with real API data. Interactions work (toggles, hover, click).
```

**Deliverable:** All chart pages functional with real data.

---

### Phase 10: Frontend — Polish & Advanced Features
**Agent Instructions:**
```
1. Build Client Profile page (Page 2):
   - Editable inputs: salary, growth, expenses, goal, horizon
   - On change → POST to /api/recalculate → refresh all downstream data
   - Show savings schedule table that updates in real time

2. Build Factor Analysis page (Page 9):
   - CAPM regression table with significance stars
   - FF5 loading bar chart
   - Rolling beta line chart (selectable asset)

3. Build GARCH page (Page 6):
   - Conditional vol time series (all assets, selectable)
   - Time-slider for dynamic correlation heatmap
   - Current vol vs historical percentile gauge

4. Build Strategy Comparison page (enhanced Page 7):
   - Full comparison table with sortable columns
   - Radar chart: Sharpe, Sortino, P(Goal), Calmar, -MaxDD per strategy
   - Fan chart overlay (select 2–4 strategies to compare)

5. Polish:
   - Loading states with skeleton screens
   - Error boundaries
   - Responsive design (works on iPad at minimum)
   - Chart export (download as PNG)
   - Number animations on metric cards

6. VERIFY: Full end-to-end test. Change client profile → see all pages update.
```

**Deliverable:** Complete, polished dashboard.

---

## 6. Iterative Improvement Cycles

After the initial 10 phases, the agent should iterate:

### Cycle 1: Accuracy Audit
```
- Cross-validate all statistics against the original class report
- Verify regime model output against known crisis dates
- Check that 12-asset tangency Sharpe > 5-asset > 3-asset
- Ensure all simulation modes produce consistent median wealth (within 5%)
- Profile simulation runtime — must complete in < 60s for 50k paths
```

### Cycle 2: Visual Polish
```
- Audit every chart for: axis labels, units, color consistency, responsive sizing
- Add micro-interactions: hover tooltips with precise values on all charts
- Ensure dark theme has sufficient contrast (WCAG AA)
- Add chart titles and subtitles explaining what the viewer should notice
- Screenshot every page, review for visual coherence
```

### Cycle 3: Robustness
```
- Handle edge cases: what if crypto data is unavailable? Graceful fallback.
- What if user sets goal to $500k? Simulation should still run, just show low P(Goal).
- What if user sets horizon to 1 year? Short horizon should show high cash allocation.
- Add input validation on client profile page
- Add error messages for API failures
```

### Cycle 4: Documentation & README
```
- Write comprehensive README.md:
  - Project description
  - Screenshots of dashboard
  - Setup instructions (Python venv + npm install + run)
  - Architecture overview
  - Methodology description (regime model, GARCH, simulation modes)
  - Data sources
  - Limitations and caveats
- Add docstrings to all Python functions
- Add inline comments for non-obvious modeling choices
```

---

## 7. What "Done" Looks Like

The finished product should:

1. **Run end-to-end with one command:** `python run_all.py && cd frontend && npm run dev`
2. **Produce 9 dashboard pages** with interactive charts and real data
3. **Support 4 simulation modes** (bootstrap, parametric, regime, GARCH) with 50k paths
4. **Optimize across 12 assets** including international, REITs, gold, and crypto
5. **Let the user edit client parameters** and see results update
6. **Look like a professional financial research tool**, not a student project
7. **Have a clean GitHub repo** with good README, clear structure, and documentation
8. **Be a portfolio piece** that demonstrates: asset pricing theory, portfolio optimization, time-series econometrics (regime switching, GARCH), Monte Carlo simulation, full-stack development, and data visualization

---

## 8. Risk Register (What Could Go Wrong)

| Risk | Mitigation |
|------|-----------|
| GARCH estimation fails to converge for some assets | Use try/except, fall back to historical vol. Crypto GARCH may need different starting params. |
| Regime model identifies >2 regimes | Fix at 2 regimes. 3-regime models are fragile with monthly data. |
| 12-asset MV optimizer hits corner solutions | Add minimum weight constraints (e.g., ≥2% for each included asset) or use regularization. |
| Crypto data too short for reliable statistics | Present crypto results with explicit "limited history" caveat. Show with/without crypto toggle. |
| Frontend becomes sluggish with 50k paths | Don't send raw paths to frontend. Backend computes percentiles, sends only summary stats + a downsampled 500-path array for the fan chart. |
| FastAPI + React setup is complex | For simpler deployment, can export all results as static JSON and have React read files directly. API only needed for the recalculate feature. |
| DCC-GARCH estimation is unreliable for 12 assets | Fall back to rolling 36-month correlation. DCC is most useful for 3–5 assets. |
| Total project scope is very large | Phases are designed to be independently valuable. The agent can stop after Phase 7 (backend complete) and still have a strong project. Frontend is additive. |
