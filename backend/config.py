# config.py — Global parameters for PortfolioLab

# ---------------------------------------------------------------------------
# Asset universe: 12 assets across equities, fixed income, alternatives
# ---------------------------------------------------------------------------
ASSET_TICKERS = {
    # Core Equities
    "IVV": {"name": "iShares S&P 500", "category": "equity", "description": "U.S. large-cap equity / CAPM benchmark"},
    "QUAL": {"name": "iShares MSCI USA Quality", "category": "equity", "description": "Quality factor tilt", "inception": "2013-07-19"},
    "USMV": {"name": "iShares MSCI USA Min Vol", "category": "equity", "description": "Low-vol factor tilt", "inception": "2011-10-20"},
    "VEA": {"name": "Vanguard FTSE Developed Markets", "category": "equity", "description": "International developed equity"},
    "VWO": {"name": "Vanguard FTSE Emerging Markets", "category": "equity", "description": "Emerging market equity"},
    # Fixed Income
    "AGG": {"name": "iShares Core U.S. Agg Bond", "category": "fixed_income", "description": "Investment-grade bonds"},
    "SHV": {"name": "iShares Short Treasury", "category": "fixed_income", "description": "Risk-free / cash proxy"},
    "TIP": {"name": "iShares TIPS Bond", "category": "fixed_income", "description": "Inflation-protected bonds"},
    # Alternatives
    "VNQ": {"name": "Vanguard Real Estate", "category": "alternatives", "description": "U.S. REITs"},
    "GLD": {"name": "SPDR Gold Shares", "category": "alternatives", "description": "Gold / commodity"},
    "BTC-USD": {"name": "Bitcoin", "category": "crypto", "description": "Crypto large-cap", "inception": "2014-09-17"},
    "ETH-USD": {"name": "Ethereum", "category": "crypto", "description": "Crypto smart contract platform", "inception": "2017-11-09"},
}

# Tickers in each analysis universe
UNIVERSE_3 = ["IVV", "AGG", "SHV"]
UNIVERSE_5 = ["IVV", "QUAL", "USMV", "AGG", "SHV"]
UNIVERSE_12 = list(ASSET_TICKERS.keys())

# Full-history tickers (available 2005+)
FULL_HISTORY_TICKERS = ["IVV", "AGG", "SHV", "VEA", "VWO", "VNQ", "GLD", "TIP"]

# Risk-free proxy
RF_TICKER = "SHV"

# ---------------------------------------------------------------------------
# Date ranges
# ---------------------------------------------------------------------------
DATE_RANGE = {
    "start": "2005-01-01",
    "end":   "2025-12-31",
}

# For 12-asset optimization (all assets available from 2017)
DATE_RANGE_12 = {
    "start": "2017-01-01",
    "end":   "2025-12-31",
}

# ---------------------------------------------------------------------------
# Client profile (new-grad target user)
# ---------------------------------------------------------------------------
CLIENT_PROFILE = {
    "starting_salary":      95_000,   # Annual gross income
    "salary_growth_rate":   0.04,     # Annual real growth (promotion + COL)
    "tax_rate":             0.28,     # Effective combined federal + state
    "annual_expenses":      55_000,   # Living expenses, rent, etc.
    "loan_balance":         40_000,   # Student loan balance
    "loan_rate":            0.055,    # 5.5% student loan rate
    "loan_min_payment":     500,      # Minimum monthly payment
    "emergency_fund_target": 20_000,  # 6-month expenses
    "goal_amount":          1_000_000,# Terminal wealth target
    "investment_horizon_years": 10,   # Years until goal
    "risk_tolerance":       "moderate",  # conservative / moderate / aggressive
    "initial_investment":   10_000,   # Starting portfolio value
}

# ---------------------------------------------------------------------------
# Simulation configuration
# ---------------------------------------------------------------------------
SIMULATION_CONFIG = {
    "n_paths":          50_000,  # Production
    "n_paths_dev":       5_000,  # Development / debugging
    "block_size":           12,  # Months per bootstrap block
    "inflation":          0.025, # Annual CPI assumption
    "rebalance_freq":  "annual", # none / quarterly / semi-annual / annual
    "horizon_years":        10,  # Must match CLIENT_PROFILE investment_horizon_years
}

# ---------------------------------------------------------------------------
# Factor model
# ---------------------------------------------------------------------------
FACTOR_TICKERS = {
    "MKT": "F-F_Research_Data_5_Factors_2x3",  # Ken French library via pandas_datareader
}

# ---------------------------------------------------------------------------
# Optimization constraints
# ---------------------------------------------------------------------------
OPT_CONSTRAINTS = {
    "min_weight":   0.00,   # Allow zero (no short-selling)
    "max_weight":   1.00,
    "max_crypto":   0.05,   # Cap crypto at 5% of portfolio
    "min_weight_included": 0.02,  # If asset is included, min 2%
}
