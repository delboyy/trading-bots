# Position Sizing Configuration
# All bots read from this file - change values here to adjust risk for all bots

# Global risk settings (applies to all bots unless overridden)
GLOBAL_RISK_PCT = 0.02          # 2% of equity per trade
MAX_POSITION_PCT = 0.10         # Maximum 10% of equity in one position

# Individual bot overrides (optional - leave empty to use global settings)
BOT_RISK_OVERRIDES = {
    # Example: 'eth_1h': 0.03,  # 3% risk for ETH 1h bot
    # Example: 'btc_combo': 0.015,  # 1.5% risk for BTC combo
}

# Maximum daily loss limit (as percentage of equity)
MAX_DAILY_LOSS_PCT = 0.05       # Stop trading if lose 5% in one day

# Volatility adjustment
USE_VOLATILITY_ADJUSTMENT = False  # Set to True to reduce size in high volatility

# Position sizing method
# 'simple': Use fixed percentage of equity
# 'risk_based': Calculate based on stop loss distance (recommended)
POSITION_SIZING_METHOD = 'simple'
