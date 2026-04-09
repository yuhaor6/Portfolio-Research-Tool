ASSET_TICKERS = {
    "IVV": {"name": "iShares S&P 500", "category": "equity", "description": "U.S. large-cap equity / CAPM benchmark"},
    "QUAL": {"name": "iShares MSCI USA Quality", "category": "equity", "description": "Quality factor tilt", "inception": "2013-07-19"},
    "USMV": {"name": "iShares MSCI USA Min Vol", "category": "equity", "description": "Low-vol factor tilt", "inception": "2011-10-20"},
    "VEA": {"name": "Vanguard FTSE Developed Markets", "category": "equity", "description": "International developed equity"},
    "VWO": {"name": "Vanguard FTSE Emerging Markets", "category": "equity", "description": "Emerging market equity"},
    "AGG": {"name": "iShares Core U.S. Agg Bond", "category": "fixed_income", "description": "Investment-grade bonds"},
    "SHV": {"name": "iShares Short Treasury", "category": "fixed_income", "description": "Risk-free / cash proxy"},
    "TIP": {"name": "iShares TIPS Bond", "category": "fixed_income", "description": "Inflation-protected bonds"},
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

DATE_RANGE = {
    "start": "2005-01-01",
    "end":   "2025-12-31",
}

# For 12-asset optimization (all assets available from 2017)
DATE_RANGE_12 = {
    "start": "2017-01-01",
    "end":   "2025-12-31",
}

CLIENT_PROFILE = {
    "starting_salary": 95_000,
    "salary_growth_rate": 0.04,
    "tax_rate": 0.28,
    "annual_expenses": 55_000,
    "loan_balance": 40_000,
    "loan_rate": 0.055,
    "loan_min_payment": 500,
    "emergency_fund_target": 20_000,
    "goal_amount": 1_000_000,
    "investment_horizon_years": 10,
    "risk_tolerance": "moderate",
    "initial_investment": 10_000,
}

SIMULATION_CONFIG = {
    "n_paths": 50_000,
    "n_paths_dev": 5_000,
    "block_size": 12,
    "inflation": 0.025,
    "rebalance_freq": "annual",
    "horizon_years": 10,
}

FACTOR_TICKERS = {
    "MKT": "F-F_Research_Data_5_Factors_2x3",  # Ken French library via pandas_datareader
}

OPT_CONSTRAINTS = {
    "min_weight": 0.00,
    "max_weight": 1.00,
    "max_crypto": 0.05,
    "min_weight_included": 0.02,
}
