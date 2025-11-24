#!/usr/bin/env python3
"""
LIVE TRADING BOT: TSLA 4h Fib Local Extrema Swing
Strategy: Fibonacci Retracement on Local Extrema Swings
Parameters: Timeframe=4h, Window=5
Paper Trading Account Required
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit
import schedule

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from grok.utils.status_tracker import StatusTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tsla_4h_fib_le.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TSLA_4H_FIB_LE')

# Create logs directory
os.makedirs('logs', exist_ok=True)

class TSLAFibLocalExtremaBot:
    """Live trading bot for TSLA 4h Fib Local Extrema strategy"""

    def __init__(self):
        # Initialize Status Tracker
        self.tracker = StatusTracker()
        self.bot_id = "tsla_4h_le"
        
        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters
        self.symbol = 'TSLA'
        self.timeframe = TimeFrame(4, TimeFrameUnit.Hour)
        self.le_window = 5
        self.fib_level = 0.618
        
        # Risk management
        self.max_position_size = 0.05 # 5% per trade
        self.risk_reward = 2.0
        self.max_drawdown_limit = 0.15

        # State tracking
        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.account_value_start = 0.0

        logger.info(f"Initialized TSLA 4h Fib Local Extrema Bot - Window={self.le_window}")

    def detect_swings_local_extrema(self, df: pd.DataFrame, window: int = 5) -> Tuple[list, list]:
        """Local Extrema implementation"""
        highs = []
        lows = []
        
        if df.empty or len(df) < window * 2: return highs, lows
        
        for i in range(window, len(df) - window):
            # Check High
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                highs.append({'idx': i, 'price': df['high'].iloc[i]})
            
            # Check Low
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                lows.append({'idx': i, 'price': df['low'].iloc[i]})
                
        return highs, lows

    def generate_signals(self, df: pd.DataFrame) -> Dict:
        """Generate signals based on Local Extrema + Fib Retracement"""
        if len(df) < 50: return {}
        
        df['ema'] = df['close'].ewm(span=50, adjust=False).mean()
        current_close = df['close'].iloc[-1]
        current_ema = df['ema'].iloc[-1]
        
        highs, lows = self.detect_swings_local_extrema(df, self.le_window)
        if not highs or not lows: return {}
        
        last_high = highs[-1]
        last_low = lows[-1]
        
        signal = {}
        
        # LONG: Uptrend + Break of High
        if current_close > current_ema:
            breakout_level = last_high['price']
            sl_price = last_low['price']
            
            if current_close > breakout_level:
                 signal = {
                    "type": "LONG",
                    "entry": current_close,
                    "sl": sl_price,
                    "tp": current_close + (current_close - sl_price) * self.risk_reward
                }
                
        # SHORT: Downtrend + Break of Low
        elif current_close < current_ema:
            breakout_level = last_low['price']
            sl_price = last_high['price']
            
            if current_close < breakout_level:
                signal = {
                    "type": "SHORT",
                    "entry": current_close,
                    "sl": sl_price,
                    "tp": current_close - (sl_price - current_close) * self.risk_reward
                }
                
        return signal

    def get_account_info(self) -> Dict[str, Any]:
        try:
            account = self.api.get_account()
            return {'equity': float(account.equity), 'cash': float(account.cash)}
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

    def get_position(self) -> Optional[Dict[str, Any]]:
        try:
            pos = self.api.get_position(self.symbol)
            return {
                'qty': float(pos.qty),
                'entry': float(pos.avg_entry_price),
                'current': float(pos.current_price),
                'pl': float(pos.unrealized_pl)
            }
        except:
            return None

    def get_historical_data(self, limit: int = 200) -> pd.DataFrame:
        try:
            bars = self.api.get_bars(self.symbol, self.timeframe, limit=limit)
            if not bars: return pd.DataFrame()
            
            data = [{'timestamp': b.t, 'open': b.o, 'high': b.h, 'low': b.l, 'close': b.c} for b in bars]
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            return df
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            return pd.DataFrame()

    def place_order(self, side: str, qty: float, sl: float, tp: float) -> bool:
        try:
            self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                stop_loss={'stop_price': sl},
                take_profit={'limit_price': tp}
            )
            logger.info(f"Placed {side} order {qty} @ Market. SL: {sl}, TP: {tp}")
            return True
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False

    def run_strategy(self):
        try:
            account = self.get_account_info()
            if not account: return
            
            pos = self.get_position()
            
            # Update Status Dashboard
            self.tracker.update_status(self.bot_id, {
                'equity': account['equity'],
                'cash': account['cash'],
                'position': pos['qty'] if pos else 0,
                'entry_price': pos['entry'] if pos else 0,
                'unrealized_pl': pos['pl'] if pos else 0
            })
            
            if pos:
                self.position = 1 if pos['qty'] > 0 else -1
                return

            self.position = 0
            df = self.get_historical_data()
            if df.empty: return
            
            signal = self.generate_signals(df)
            if signal:
                risk_amt = account['equity'] * self.max_position_size
                dist = abs(signal['entry'] - signal['sl'])
                if dist == 0: return
                qty = risk_amt / dist
                qty = int(qty) # TSLA shares must be int or fractional if enabled. Safe to use int.
                
                if qty > 0:
                    side = 'buy' if signal['type'] == 'LONG' else 'sell'
                    self.place_order(side, qty, signal['sl'], signal['tp'])
                
        except Exception as e:
            logger.error(f"Error in strategy: {e}")

    def run_live(self):
        logger.info("Starting TSLA 4h Fib Local Extrema Bot...")
        schedule.every(15).minutes.do(self.run_strategy) # Check every 15m
        while True:
            try:
                schedule.run_pending()
                time.sleep(10)
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    TSLAFibLocalExtremaBot().run_live()
