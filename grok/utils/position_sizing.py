"""
Position Sizing Utility
All bots import this to get consistent position sizing
"""

import os
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).resolve().parents[1] / 'config'
sys.path.insert(0, str(config_path))

try:
    from position_sizing import (
        GLOBAL_RISK_PCT,
        MAX_POSITION_PCT,
        BOT_RISK_OVERRIDES,
        MAX_DAILY_LOSS_PCT,
        POSITION_SIZING_METHOD
    )
except ImportError:
    # Fallback defaults if config file doesn't exist
    GLOBAL_RISK_PCT = 0.02
    MAX_POSITION_PCT = 0.10
    BOT_RISK_OVERRIDES = {}
    MAX_DAILY_LOSS_PCT = 0.05
    POSITION_SIZING_METHOD = 'simple'


def calculate_position_size(bot_id, account_equity, entry_price, stop_loss_price=None):
    """
    Calculate position size for a trade
    
    Args:
        bot_id: Bot identifier (e.g., 'eth_1h')
        account_equity: Total account equity
        entry_price: Entry price for the trade
        stop_loss_price: Stop loss price (optional, for risk-based sizing)
    
    Returns:
        float: Position size (number of shares/units)
    """
    # Get risk percentage for this bot
    risk_pct = BOT_RISK_OVERRIDES.get(bot_id, GLOBAL_RISK_PCT)
    
    if POSITION_SIZING_METHOD == 'risk_based' and stop_loss_price is not None:
        # Risk-based sizing (accounts for stop loss distance)
        risk_amount = account_equity * risk_pct
        price_risk = abs(entry_price - stop_loss_price)
        
        if price_risk == 0:
            # Fallback to simple method if no stop loss distance
            position_size = (account_equity * risk_pct) / entry_price
        else:
            position_size = risk_amount / price_risk
    else:
        # Simple sizing (fixed percentage of equity)
        risk_amount = account_equity * risk_pct
        position_size = risk_amount / entry_price
    
    # Apply maximum position size limit
    max_position_value = account_equity * MAX_POSITION_PCT
    max_position_size = max_position_value / entry_price
    
    # Use the smaller of the two
    final_size = min(position_size, max_position_size)
    
    return final_size


def get_risk_pct(bot_id):
    """Get risk percentage for a specific bot"""
    return BOT_RISK_OVERRIDES.get(bot_id, GLOBAL_RISK_PCT)


def get_max_position_pct():
    """Get maximum position percentage"""
    return MAX_POSITION_PCT


def get_max_daily_loss_pct():
    """Get maximum daily loss percentage"""
    return MAX_DAILY_LOSS_PCT
