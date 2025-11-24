#!/usr/bin/env python3
"""
LIVE TRADING BOT: NVDA 1d Volatility Breakout
Strategy: ATR-based volatility breakout on Nvidia (Daily)
Parameters: ATR window=14, k=1.5
Paper Trading Account Required
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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
        logging.FileHandler('logs/nvda_1d_volatility_breakout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('NVDA_1D_VOLATILITY_BREAKOUT')

# Create logs directory
os.makedirs('logs', exist_ok=True)

class NVDADailyVolBreakoutBot:
    """Live trading bot for NVDA 1d Volatility Breakout strategy"""

    def __init__(self):
        # Initialize Status Tracker
        self.tracker = StatusTracker()
        self.bot_id = "nvda_1d_vb"
        
        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters
        self.symbol = 'NVDA'
        self.timeframe = TimeFrame.Day
        self.atr_window = 14
        self.k = 1.5
        
        # Risk management
        self.max_position_size = 0.05 
        self.max_drawdown_limit = 0.30 

        # State tracking
        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.account_value_start = 0.0

        logger.info(f"Initialized NVDA 1d Volatility Breakout Bot - ATR({self.atr_window}), k={self.k}")

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(self.atr_window).mean()

    def generate_signals(self, df: pd.DataFrame) -> int:
        if len(df) < self.atr_window + 1: return 0
        
        atr = self.calculate_atr(df)
        prev_close = df['close'].shift(1)
        upper_band = prev_close + (self.k * atr)
        lower_band = prev_close - (self.k * atr)
        
        current_close = df['close'].iloc[-1]
        prev_upper = upper_band.iloc[-2] if len(upper_band) > 1 else 0
        prev_lower = lower_band.iloc[-2] if len(lower_band) > 1 else 0
        
        if current_close > prev_upper: return 1
        elif current_close < prev_lower: return -1
        return 0

    def get_account_info(self) -> Dict[str, Any]:
        try:
            account = self.api.get_account()
            return {'equity': float(account.equity), 'cash': float(account.cash)}
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

    def get_position(self) -> Optional[Dict[str, Any]]:
        try:
            positions = self.api.list_positions()
            for pos in positions:
                if pos.symbol == self.symbol:
                    return {
                        'qty': float(pos.qty),
                        'entry': float(pos.avg_entry_price),
                        'current': float(pos.current_price),
                        'pl': float(pos.unrealized_pl)
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

    def get_historical_data(self, days: int = 100) -> pd.DataFrame:
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            bars = self.api.get_bars(self.symbol, self.timeframe, start=start_time.isoformat(), end=end_time.isoformat(), limit=100)
            if not bars: return pd.DataFrame()
            
            data = [{'timestamp': b.timestamp, 'open': b.open, 'high': b.high, 'low': b.low, 'close': b.close} for b in bars]
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            return df
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            return pd.DataFrame()

    def place_order(self, side: str, qty: float) -> bool:
        try:
            self.api.submit_order(symbol=self.symbol, qty=qty, side=side, type='market', time_in_force='gtc')
            logger.info(f"Placed {side} order for {qty} {self.symbol}")
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
            else:
                self.position = 0

            df = self.get_historical_data(100)
            if df.empty: return
            
            signal = self.generate_signals(df)
            
            if signal != 0 and self.position == 0:
                current_price = df['close'].iloc[-1]
                risk_amt = account['equity'] * self.max_position_size
                qty = risk_amt / current_price
                qty = int(qty)
                
                if qty > 0:
                    side = 'buy' if signal == 1 else 'sell'
                    if self.place_order(side, qty):
                        self.position = signal
            
            elif signal != 0 and self.position != signal:
                qty_to_close = abs(pos['qty'])
                close_side = 'sell' if self.position == 1 else 'buy'
                self.place_order(close_side, qty_to_close)
                
                current_price = df['close'].iloc[-1]
                risk_amt = account['equity'] * self.max_position_size
                qty = risk_amt / current_price
                qty = int(qty)
                
                if qty > 0:
                    side = 'buy' if signal == 1 else 'sell'
                    if self.place_order(side, qty):
                        self.position = signal

        except Exception as e:
            logger.error(f"Error in strategy: {e}")

    def run_live(self):
        logger.info("Starting NVDA 1d Volatility Breakout Bot...")
        schedule.every(1).hours.do(self.run_strategy)
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(300)

if __name__ == "__main__":
    NVDADailyVolBreakoutBot().run_live()
