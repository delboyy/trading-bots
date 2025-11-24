#!/usr/bin/env python3
"""
LIVE TRADING BOT: BTC 5m Fib Zigzag Scalper
Strategy: Fibonacci Retracement on Zigzag Swings
Parameters: Timeframe=5m, Zigzag Deviation=2%
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/btc_5m_fib_zigzag.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BTC_5M_FIB_ZIGZAG')

# Create logs directory
os.makedirs('logs', exist_ok=True)

class BTCFibZigzagBot:
    """Live trading bot for BTC 5m Fib Zigzag strategy"""

    def __init__(self):
        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters
        self.symbol = 'BTCUSD'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.zigzag_dev = 0.02 # 2% deviation
        self.fib_level = 0.618
        
        # Risk management
        self.max_position_size = 0.05 # 5% per trade
        self.risk_reward = 2.0
        self.max_drawdown_limit = 0.10

        # State tracking
        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.account_value_start = 0.0

        logger.info(f"Initialized BTC 5m Fib Zigzag Bot - Dev={self.zigzag_dev}")

    def detect_swings_zigzag(self, df: pd.DataFrame, deviation_pct: float = 0.02) -> Tuple[list, list]:
        """ZigZag implementation"""
        highs = []
        lows = []
        
        if df.empty: return highs, lows
        
        h_series = df['high'].values
        l_series = df['low'].values
        
        tmp_high = h_series[0]
        tmp_low = l_series[0]
        tmp_high_idx = 0
        tmp_low_idx = 0
        trend = 0 
        
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
                    tmp_high = curr_high
                    tmp_high_idx = i
                elif curr_low <= tmp_high * (1 - deviation_pct):
                    highs.append({'idx': tmp_high_idx, 'price': tmp_high})
                    trend = -1
                    tmp_low = curr_low
                    tmp_low_idx = i
            elif trend == 1:
                if curr_high > tmp_high:
                    tmp_high = curr_high
                    tmp_high_idx = i
                elif curr_low <= tmp_high * (1 - deviation_pct):
                    highs.append({'idx': tmp_high_idx, 'price': tmp_high})
                    trend = -1
                    tmp_low = curr_low
                    tmp_low_idx = i
            elif trend == -1:
                if curr_low < tmp_low:
                    tmp_low = curr_low
                    tmp_low_idx = i
                elif curr_high >= tmp_low * (1 + deviation_pct):
                    lows.append({'idx': tmp_low_idx, 'price': tmp_low})
                    trend = 1
                    tmp_high = curr_high
                    tmp_high_idx = i
                    
        return highs, lows

    def generate_signals(self, df: pd.DataFrame) -> Dict:
        """Generate signals based on Zigzag + Fib Retracement"""
        if len(df) < 50: return {}
        
        df['ema'] = df['close'].ewm(span=50, adjust=False).mean()
        current_close = df['close'].iloc[-1]
        current_ema = df['ema'].iloc[-1]
        
        highs, lows = self.detect_swings_zigzag(df, self.zigzag_dev)
        if not highs or not lows: return {}
        
        last_high = highs[-1]
        last_low = lows[-1]
        
        signal = {}
        
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
            
            data = [{'timestamp': b.timestamp, 'open': b.open, 'high': b.high, 'low': b.low, 'close': b.close} for b in bars]
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
                qty = round(qty, 6) # BTC precision
                
                side = 'buy' if signal['type'] == 'LONG' else 'sell'
                self.place_order(side, qty, signal['sl'], signal['tp'])
                
        except Exception as e:
            logger.error(f"Error in strategy: {e}")

    def run_live(self):
        logger.info("Starting BTC 5m Fib Zigzag Bot...")
        schedule.every(1).minutes.do(self.run_strategy)
        while True:
            try:
                schedule.run_pending()
                time.sleep(10)
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    BTCFibZigzagBot().run_live()
