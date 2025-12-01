#!/usr/bin/env python3
"""
BTC COMBO STRATEGY - LIVE BOT
Best performing strategy: 0.247% daily, 55% win rate
Combines: Momentum + Volume + Session Filter

Strategy Logic:
- Entry: Momentum > threshold + Volume > avg * multiplier + EMA cross
- Session Filter: Only trade during high-volume sessions (NY/London)
- Exit: TP 1.5% or SL 0.7%
- Timeframe: 15m (optimized)
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import time
import signal
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/btc_combo_15m_claude.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BTC_COMBO_15M_CLAUDE')

# Add project root to path for StatusTracker
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

try:
    from grok.utils.status_tracker import StatusTracker
except ImportError:
    # Fallback: create a dummy StatusTracker if import fails
    class StatusTracker:
        def update_status(self, bot_id, status):
            logger.info(f"Status update: {status}")
        def update_status(self, bot_id, status):
            logger.info(f"Status update: {status}")

class BTCComboClaudeBot:
    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "btc_combo_claude"
        
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        
        if not all([self.api_key, self.api_secret]):
            raise ValueError("Missing Alpaca API credentials")
        
        self.api = REST(self.api_key, self.api_secret, self.base_url)
        self.symbol = 'BTC/USD'
        
        # Strategy Parameters (from backtesting)
        self.timeframe_minutes = int(os.getenv('TIMEFRAME_MINUTES', '15'))
        self.timeframe = TimeFrame(self.timeframe_minutes, TimeFrameUnit.Minute)
        self.momentum_period = 4
        self.volume_multiplier = 1.3
        self.take_profit_pct = 0.015  # 1.5%
        self.stop_loss_pct = 0.007    # 0.7%
        self.momentum_threshold = 0.5  # 0.5% momentum
        
        # Session filter
        self.use_session_filter = True
        self.active_sessions = [
            (3, 11),   # London: 3am-11am ET
            (9, 11),   # NY AM: 9:30am-11:30am ET
            (14, 16)   # NY PM: 2pm-4pm ET
        ]
        
        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.tp_order_id = None
        self.sl_order_id = None
        
        # Performance tracking
        self.daily_start_capital = 10000
        self.current_capital = 10000
        self.last_trade_time = None
        self.min_time_between_trades = timedelta(minutes=self.timeframe_minutes * 3)
        
        logger.info(f"Initialized BTC Combo Claude Bot for {self.timeframe_minutes}m timeframe")
        logger.info(f"Parameters: Mom={self.momentum_period}, Vol={self.volume_multiplier}, TP={self.take_profit_pct*100}%, SL={self.stop_loss_pct*100}%")
        logger.info(f"Session Filter: {self.use_session_filter}")
    
    def is_active_session(self):
        """Check if current time is in active trading session"""
        if not self.use_session_filter:
            return True
        
        current_hour = datetime.now().hour
        for start_hour, end_hour in self.active_sessions:
            if start_hour <= current_hour < end_hour:
                return True
        return False
    
    def get_market_data(self, bars=50):
        """Fetch recent market data"""
        try:
            end = datetime.now()
            start = end - timedelta(minutes=self.timeframe_minutes * bars)
            
            # Format dates as RFC3339 (YYYY-MM-DDTHH:MM:SSZ)
            start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            barset = self.api.get_crypto_bars(
                self.symbol,
                self.timeframe,
                start=start_str,
                end=end_str
            ).df
            
            if barset.empty:
                return None
            
            # Reset index and rename columns
            barset = barset.reset_index()
            barset.columns = ['symbol', 'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'trade_count', 'vwap']
            barset = barset[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]
            barset['timestamp'] = pd.to_datetime(barset['timestamp'])
            barset = barset.set_index('timestamp')
            
            return barset
        
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    def calculate_signals(self, df):
        """Calculate trading signals"""
        # Momentum
        df['Momentum'] = df['Close'].pct_change(self.momentum_period) * 100
        
        # Volume
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        
        # EMAs
        df['EMA_Fast'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_Slow'] = df['Close'].ewm(span=26, adjust=False).mean()
        
        return df
    
    def check_entry_signal(self, df):
        """Check for entry signal"""
        if len(df) < 30:
            return False
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Session filter
        if not self.is_active_session():
            return False
        
        # Minimum time between trades
        if self.last_trade_time and datetime.now() - self.last_trade_time < self.min_time_between_trades:
            return False
        
        # Entry conditions:
        # 1. Positive momentum above threshold
        # 2. EMA Fast crosses above EMA Slow
        # 3. Volume > average * multiplier
        
        momentum_signal = current['Momentum'] > self.momentum_threshold
        ema_cross = (current['EMA_Fast'] > current['EMA_Slow'] and 
                     previous['EMA_Fast'] <= previous['EMA_Slow'])
        volume_signal = current['Volume'] > current['Volume_MA'] * self.volume_multiplier
        
        return momentum_signal and ema_cross and volume_signal
    
    def check_exit_signal(self, df):
        """Check for exit signal"""
        if self.position == 0:
            return False, ""
        
        current_price = df.iloc[-1]['Close']
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Take Profit
        if pnl_pct >= self.take_profit_pct:
            return True, "TP"
        
        # Stop Loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "SL"
        
        # Reverse signal: EMA Fast crosses below EMA Slow
        current = df.iloc[-1]
        previous = df.iloc[-2]
        if current['EMA_Fast'] < current['EMA_Slow'] and previous['EMA_Fast'] >= previous['EMA_Slow']:
            return True, "Reverse"
        
        return False, ""
    
    def place_entry_order(self, current_price):
        """Place entry order with TP/SL"""
        try:
            # Calculate position size (use available cash)
            account = self.api.get_account()
            available_cash = float(account.cash)
            position_size = (available_cash * 0.95) / current_price  # Use 95% of cash
            position_size = round(position_size, 6)  # BTC precision
            
            if position_size < 0.0001:  # Minimum BTC position
                logger.warning(f"Position size too small: {position_size}")
                return False
            
            # Place LIMIT order (0.01% fee vs 0.035% market order)
            limit_price = current_price * 0.9995  # Slightly below current for quick fill
            logger.info(f"🚀 ENTRY: Buying (LIMIT) {position_size} BTC @ ${limit_price:,.2f} (limit)")
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=position_size,
                side='buy',
                type='limit',
                limit_price=round(limit_price, 2),
                time_in_force='gtc'
            )
            
            logger.info(f"✅ Entry limit order placed: {order.id}")
            
            # Wait for fill (limit orders may take longer)
            time.sleep(5)
            filled_price = current_price  # Will update from actual fill if needed
            
            # Update position
            self.position = position_size
            self.entry_price = filled_price
            self.last_trade_time = datetime.now()
            
            # Place TP and SL orders (separate orders, NOT OCO - Alpaca doesn't support OCO for crypto)
            tp_price = filled_price * (1 + self.take_profit_pct)
            sl_price = filled_price * (1 - self.stop_loss_pct)
            
            # Take Profit
            tp_order = self.api.submit_order(
                symbol=self.symbol,
                qty=position_size,
                side='sell',
                type='limit',
                limit_price=round(tp_price, 2),
                time_in_force='gtc'
            )
            self.tp_order_id = tp_order.id
            logger.info(f"📈 TP order placed @ ${tp_price:,.2f}")
            
            # Stop Loss
            sl_order = self.api.submit_order(
                symbol=self.symbol,
                qty=position_size,
                side='sell',
                type='stop',
                stop_price=round(sl_price, 2),
                time_in_force='gtc'
            )
            self.sl_order_id = sl_order.id
            logger.info(f"🛑 SL order placed @ ${sl_price:,.2f}")
            
            # Update tracker
            self.tracker.update_status(self.bot_id, {
                'in_position': True,
                'entry_price': current_price,
                'position_size': position_size,
                'tp_price': tp_price,
                'sl_price': sl_price
            })
            
            return True
        
        except Exception as e:
            logger.error(f"Error placing entry order: {e}")
            return False
    
    def place_exit_order(self, current_price, reason):
        """Place exit order"""
        try:
            if self.position == 0:
                return False
            
            # Cancel TP/SL orders
            if self.tp_order_id:
                try:
                    self.api.cancel_order(self.tp_order_id)
                except:
                    pass
            if self.sl_order_id:
                try:
                    self.api.cancel_order(self.sl_order_id)
                except:
                    pass
            
            # Place market sell
            logger.info(f"🔴 EXIT: Selling {self.position} BTC @ ${current_price:,.2f} ({reason})")
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=self.position,
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            
            logger.info(f"✅ Exit order placed: {order.id}")
            
            # Calculate PnL
            pnl = self.position * (current_price - self.entry_price)
            pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
            
            logger.info(f"💰 PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            
            # Update capital
            self.current_capital += pnl
            
            # Update tracker
            self.tracker.update_status(self.bot_id, {
                'in_position': False,
                'last_pnl': pnl,
                'last_pnl_pct': pnl_pct,
                'total_capital': self.current_capital
            })
            
            # Reset position
            self.position = 0
            self.entry_price = 0
            self.tp_order_id = None
            self.sl_order_id = None
            
            return True
        
        except Exception as e:
            logger.error(f"Error placing exit order: {e}")
            return False
    
    def run(self):
        """Main bot loop"""
        logger.info(f"🤖 Starting BTC Combo Claude Bot ({self.timeframe_minutes}m)")
        
        # Initialize tracker
        self.tracker.update_status(self.bot_id, {
            'name': f'BTC Combo Claude {self.timeframe_minutes}m',
            'strategy': 'Momentum + Volume + Session Filter',
            'status': 'running',
            'in_position': False
        })
        
        while True:
            try:
                # Get market data
                df = self.get_market_data(bars=50)
                if df is None or len(df) < 30:
                    logger.warning("Insufficient data, waiting...")
                    time.sleep(60)
                    continue
                
                # Calculate signals
                df = self.calculate_signals(df)
                current_price = df.iloc[-1]['Close']
                
                logger.info(f"📊 Current: ${current_price:,.2f} | Position: {self.position:.6f} BTC")
                
                # Check position status
                if self.position == 0:
                    # Check for entry
                    if self.check_entry_signal(df):
                        self.place_entry_order(current_price)
                else:
                    # Check for exit
                    should_exit, reason = self.check_exit_signal(df)
                    if should_exit:
                        self.place_exit_order(current_price, reason)
                
                # Update tracker
                self.tracker.update_status(self.bot_id, {
                    'last_update': datetime.now().isoformat(),
                    'current_price': current_price,
                    'status': 'running'
                })
                
                # Wait for next bar
                wait_seconds = self.timeframe_minutes * 60
                logger.info(f"⏳ Waiting {wait_seconds}s until next check...")
                time.sleep(wait_seconds)
            
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

def signal_handler(sig, frame):
    logger.info("🛑 Shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = BTCComboClaudeBot()
    bot.run()

