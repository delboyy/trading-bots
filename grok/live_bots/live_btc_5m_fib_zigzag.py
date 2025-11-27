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
import signal
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
        logging.FileHandler('logs/btc_5m_fib_zigzag.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BTC_5M_FIB_ZIGZAG')

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Global stop flag
stop_flag = False

def signal_handler(signum, frame):
    """Handle stop signals gracefully"""
    global stop_flag
    stop_flag = True
    logger.info(f"Received signal {signum}, stopping bot gracefully...")
    # Give a moment for cleanup
    time.sleep(2)
    logger.info("Bot stopped successfully")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill command

class BTCFibZigzagBot:
    """Live trading bot for BTC 5m Fib Zigzag strategy"""

    def __init__(self):
        # Initialize Status Tracker
        self.tracker = StatusTracker()
        self.bot_id = "btc_5m_zigzag"
        
        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters
        self.symbol = 'BTC/USD'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.zigzag_dev = 0.02 # 2% deviation
        self.fib_level = 0.618
        
        # Risk management
        self.max_position_size = 0.10 # 10% per trade
        self.risk_reward = 2.0
        self.max_drawdown_limit = 0.15
        
        # Order tracking for separate SL/TP orders
        self.active_sl_order = None
        self.active_tp_order = None
        
        # State tracking
        self.position = 0
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
            bars = self.api.get_crypto_bars(self.symbol, self.timeframe, limit=limit)
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
        """
        Place market order with separate stop loss and take profit orders.
        Alpaca doesn't support bracket orders for crypto, so we place them separately.
        """
        try:
            # 1. Place market entry order
            entry_order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            logger.info(f"✅ Entry order placed: {side} {qty} @ Market")
            
            # Wait a moment for entry to fill
            import time
            time.sleep(2)
            
            # 2. Place Stop Loss order (opposite side)
            sl_side = 'sell' if side == 'buy' else 'buy'
            sl_order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=sl_side,
                type='stop',
                time_in_force='gtc',
                stop_price=round(sl, 2)
            )
            logger.info(f"🛡️ Stop Loss placed: {sl_side} @ ${sl:.2f}")
            
            # 3. Place Take Profit order (opposite side)
            tp_order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=sl_side,  # Same as SL side
                type='limit',
                time_in_force='gtc',
                limit_price=round(tp, 2)
            )
            logger.info(f"🎯 Take Profit placed: {sl_side} @ ${tp:.2f}")
            
            # Store order IDs for tracking
            self.active_sl_order = sl_order.id
            self.active_tp_order = tp_order.id
            
            logger.info(f"✅ Complete: Entry + SL + TP orders placed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error placing orders: {e}")
            # Try to cancel any partial orders
            try:
                self.cancel_all_orders()
            except:
                pass
            return False
    
    def cancel_all_orders(self):
        """Cancel all open orders for this symbol"""
        try:
            orders = self.api.list_orders(status='open', symbols=[self.symbol])
            for order in orders:
                self.api.cancel_order(order.id)
                logger.info(f"Cancelled order: {order.id}")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
    
    def check_and_cleanup_orders(self):
        """
        Check if TP or SL filled, and cancel the opposite order.
        This prevents orphaned orders from triggering unwanted trades.
        """
        try:
            # Check if we have active exit orders
            if not hasattr(self, 'active_sl_order') or not hasattr(self, 'active_tp_order'):
                return
            
            # Get current position
            pos = self.get_position()
            
            # If no position, one of the exit orders filled - cancel the other
            if not pos:
                self.cancel_all_orders()
                self.active_sl_order = None
                self.active_tp_order = None
                logger.info("✅ Position closed - exit orders cleaned up")
                
        except Exception as e:
            logger.error(f"Error in order cleanup: {e}")

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
                # Check and cleanup exit orders if needed
                self.check_and_cleanup_orders()
                return

            self.position = 0
            
            # Clean up any orphaned orders from previous trades
            if not pos:
                self.check_and_cleanup_orders()
            
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
        global stop_flag
        logger.info("Starting BTC 5m Fib Zigzag Bot...")
        schedule.every(1).minutes.do(self.run_strategy)

        while not stop_flag:
            try:
                schedule.run_pending()
                time.sleep(10)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(60)
        
        logger.info("Bot shutdown complete - cleaning up...")
        logger.info("BTC 5m Fib Zigzag Bot stopped")

if __name__ == "__main__":
    BTCFibZigzagBot().run_live()
