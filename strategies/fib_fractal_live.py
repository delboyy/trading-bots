"""
Breakout Strategy (Live Implementation)
---------------------------------------
Logic:
- Trend Filter: EMA 50 (Close > EMA = Long, Close < EMA = Short)
- Swing Detection: ZigZag (2% Deviation)
- Entry: Break of Swing High (Long) or Swing Low (Short)
- Stop Loss: Previous Swing Low (Long) or Swing High (Short)
- Take Profit: 2R (Reward = 2 * Risk)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

# --- Configuration ---
ZIGZAG_DEVIATION = 0.02  # 2%
EMA_PERIOD = 50
RISK_REWARD_RATIO = 2.0

def get_strategy_signal(df: pd.DataFrame) -> Dict:
    """
    Analyzes the dataframe to generate a trading signal based on Breakout Logic.
    
    Args:
        df: DataFrame with 'Open', 'High', 'Low', 'Close' columns.
        
    Returns:
        Dict containing signal details or None if no signal.
    """
    if df.empty or len(df) < EMA_PERIOD + 10:
        return {}

    # 1. Calculate Trend (EMA 50)
    df['EMA'] = df['Close'].ewm(span=EMA_PERIOD, adjust=False).mean()
    current_close = df['Close'].iloc[-1]
    current_ema = df['EMA'].iloc[-1]
    
    is_uptrend = current_close > current_ema
    is_downtrend = current_close < current_ema
    
    # 2. Detect Swings (ZigZag)
    highs, lows = detect_swings_zigzag(df, deviation_pct=ZIGZAG_DEVIATION)
    
    # Need at least one High and one Low to define a range
    if not highs or not lows:
        return {}
        
    last_high = highs[-1] # {'idx': ..., 'price': ...}
    last_low = lows[-1]   # {'idx': ..., 'price': ...}
    
    # 3. Check for Breakout
    signal = {}
    
    # LONG SIGNAL
    # If Uptrend AND Price breaks above Last Swing High
    if is_uptrend:
        # Check if we just broke the high (current close > high, previous close <= high)
        # Or simply if current price is above the level and we are not in a trade (handled by orchestrator)
        # Here we just report the setup levels.
        
        breakout_level = last_high['price']
        stop_loss = last_low['price']
        
        # Validate Risk
        risk = breakout_level - stop_loss
        if risk > 0:
            target = breakout_level + (risk * RISK_REWARD_RATIO)
            
            # Check if current price is triggering the breakout
            if current_close > breakout_level:
                signal = {
                    "type": "LONG",
                    "entry_price": breakout_level, # Or current_close if market order
                    "stop_loss": stop_loss,
                    "take_profit": target,
                    "setup_valid": True,
                    "reason": f"Breakout above Swing High {breakout_level:.2f}"
                }

    # SHORT SIGNAL
    # If Downtrend AND Price breaks below Last Swing Low
    elif is_downtrend:
        breakout_level = last_low['price']
        stop_loss = last_high['price']
        
        # Validate Risk
        risk = stop_loss - breakout_level
        if risk > 0:
            target = breakout_level - (risk * RISK_REWARD_RATIO)
            
            if current_close < breakout_level:
                signal = {
                    "type": "SHORT",
                    "entry_price": breakout_level,
                    "stop_loss": stop_loss,
                    "take_profit": target,
                    "setup_valid": True,
                    "reason": f"Breakout below Swing Low {breakout_level:.2f}"
                }
                
    return signal

def detect_swings_zigzag(df: pd.DataFrame, deviation_pct: float = 0.02) -> Tuple[list, list]:
    """
    Simplified ZigZag implementation for live usage.
    Returns list of Highs and Lows.
    """
    highs = []
    lows = []
    
    if df.empty:
        return highs, lows
        
    series = df['Close'].values # Use Close for simplicity in live, or High/Low for precision
    # Using High/Low is better for true swings
    h_series = df['High'].values
    l_series = df['Low'].values
    
    last_pivot_type = None # 'high' or 'low'
    last_pivot_price = series[0]
    last_pivot_idx = 0
    
    # Initial direction assumption
    # This is a simplified pass. For robust live zigzag, we need to track state.
    # For now, we re-calculate on the whole window.
    
    tmp_high = h_series[0]
    tmp_low = l_series[0]
    tmp_high_idx = 0
    tmp_low_idx = 0
    
    trend = 0 # 1 up, -1 down
    
    for i in range(1, len(df)):
        curr_high = h_series[i]
        curr_low = l_series[i]
        
        if trend == 0:
            if curr_high > tmp_high:
                tmp_high = curr_high
                tmp_high_idx = i
            if curr_low < tmp_low:
                tmp_low = curr_low
                tmp_low_idx = i
                
            if curr_high >= tmp_low * (1 + deviation_pct):
                lows.append({'idx': tmp_low_idx, 'price': tmp_low})
                trend = 1
                last_pivot_type = 'low'
                tmp_high = curr_high
                tmp_high_idx = i
            elif curr_low <= tmp_high * (1 - deviation_pct):
                highs.append({'idx': tmp_high_idx, 'price': tmp_high})
                trend = -1
                last_pivot_type = 'high'
                tmp_low = curr_low
                tmp_low_idx = i
                
        elif trend == 1: # Up
            if curr_high > tmp_high:
                tmp_high = curr_high
                tmp_high_idx = i
            elif curr_low <= tmp_high * (1 - deviation_pct):
                highs.append({'idx': tmp_high_idx, 'price': tmp_high})
                trend = -1
                last_pivot_type = 'high'
                tmp_low = curr_low
                tmp_low_idx = i
                
        elif trend == -1: # Down
            if curr_low < tmp_low:
                tmp_low = curr_low
                tmp_low_idx = i
            elif curr_high >= tmp_low * (1 + deviation_pct):
                lows.append({'idx': tmp_low_idx, 'price': tmp_low})
                trend = 1
                last_pivot_type = 'low'
                tmp_high = curr_high
                tmp_high_idx = i
                
    return highs, lows
