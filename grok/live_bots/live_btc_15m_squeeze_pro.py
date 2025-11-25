#!/usr/bin/env python3
"""
LIVE TRADING BOT: BTC 15m Squeeze-Pro
Strategy: Bollinger Band Squeeze + Momentum
Parameters: Timeframe=15m, BB(20,2), KC(20,1.5)
Paper Trading Account Required
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import pandas_ta as ta
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
        logging.FileHandler('logs/btc_15m_squeeze_pro.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BTC_15M_SQUEEZE_PRO')

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Global stop flag
stop_flag = False

def signal_handler(signum, frame):
    """Handle stop signals gracefully"""
    global stop_flag
    stop_flag = True
    logger.info(f"Received signal {signum}, stopping bot gracefully...")
    time.sleep(2)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class BTCSqueezeProBot:
    """Live trading bot for BTC 15m Squeeze-Pro strategy"""

    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "btc_15m_squeeze"
        
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        self.symbol = 'BTCUSD'
        self.timeframe = TimeFrame(15, TimeFrameUnit.Minute)
        
        # Risk management
        self.max_position_size = 0.10 # 10% per trade
        self.max_drawdown_limit = 0.15
        
        self.position = 0
        self.account_value_start = 0.0

        logger.info(f"Initialized BTC 15m Squeeze-Pro Bot")

    def get_account_info(self) -> Dict[str, Any]:
        try:
            account = self.api.get_account()
            return {'equity': float(account.equity), 'cash': float(account.cash)}
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            self.tracker.update_status(self.bot_id, {'error': str(e)})
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
            
            data = [{'timestamp': b.t, 'open': b.o, 'high': b.h, 'low': b.l, 'close': b.c, 'volume': b.v} for b in bars]
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            return df
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            self.tracker.update_status(self.bot_id, {'error': str(e)})
            return pd.DataFrame()

    def generate_signals(self, df: pd.DataFrame) -> Dict:
        if len(df) < 50: return {}
        
        # Bollinger Bands (20, 2)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        # Rename dynamically
        cols = bb.columns.tolist()
        df.rename(columns={cols[0]: 'bb_lower', cols[1]: 'bb_middle', cols[2]: 'bb_upper', cols[3]: 'bb_width'}, inplace=True)
        
        current = df.iloc[-1]
        
        signal = {}
        
        # LONG: Close breaks above Upper BB
        if current['close'] > current['bb_upper']:
             signal = {
                "type": "LONG",
                "entry": current['close'],
                "sl": current['bb_middle'],
                "tp": current['close'] * 1.05
            }
            
        # SHORT: Close breaks below Lower BB
        elif current['close'] < current['bb_lower']:
            signal = {
                "type": "SHORT",
                "entry": current['close'],
                "sl": current['bb_middle'],
                "tp": current['close'] * 0.95
            }
            
        return signal

    def place_order(self, side: str, qty: float, sl: float, tp: float) -> bool:
        try:
            self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                stop_loss={'stop_price': round(sl, 2)},
                take_profit={'limit_price': round(tp, 2)}
            )
            logger.info(f"Placed {side} order {qty} @ Market. SL: {sl}, TP: {tp}")
            return True
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            self.tracker.update_status(self.bot_id, {'error': str(e)})
            return False

    def run_strategy(self):
        try:
            account = self.get_account_info()
            if not account: return
            
            pos = self.get_position()
            
            self.tracker.update_status(self.bot_id, {
                'equity': account['equity'],
                'cash': account['cash'],
                'position': pos['qty'] if pos else 0,
                'entry_price': pos['entry'] if pos else 0,
                'unrealized_pl': pos['pl'] if pos else 0,
                'error': None
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
                qty = risk_amt / signal['entry']
                qty = round(qty, 4) # BTC precision
                
                side = 'buy' if signal['type'] == 'LONG' else 'sell'
                self.place_order(side, qty, signal['sl'], signal['tp'])
                
        except Exception as e:
            logger.error(f"Error in strategy: {e}")
            self.tracker.update_status(self.bot_id, {'error': str(e)})

    def run_live(self):
        global stop_flag
        logger.info(f"Starting {self.bot_id}...")
        schedule.every(1).minutes.do(self.run_strategy)

        try:
            while not stop_flag:
                schedule.run_pending()
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            self.tracker.update_status(self.bot_id, {'error': f"CRASH: {str(e)}"})

if __name__ == "__main__":
    BTCSqueezeProBot().run_live()
