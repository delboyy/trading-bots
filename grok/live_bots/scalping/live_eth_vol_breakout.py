#!/usr/bin/env python3
"""
ETH 1H HIGH VOLATILITY BREAKOUT - LIVE BOT
Best backtest: 51.16% over 2 years, 0.07% daily, 36% win rate

Strategy Logic:
- Entry: Z-Score > 2.0 during high volatility (ATR > ATR_MA)
- Exit: Price crosses SMA OR TP/SL
- Timeframe: 1h
- Asset: ETH/USD (Alpaca crypto)
"""


import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import logging
import time
import signal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/eth_vol_breakout_error.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ETH_VOL_BREAKOUT')

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Add parent directory to path for StatusTracker
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from grok.utils.status_tracker import StatusTracker

class ETHVolBreakoutBot:
    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "eth_vol_breakout"
        
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        
        if not all([self.api_key, self.api_secret]):
            raise ValueError("Missing Alpaca API credentials")
        
        self.api = REST(self.api_key, self.api_secret, self.base_url)
        self.symbol = 'ETH/USD'
        
        # Strategy Parameters (from backtesting)
        self.timeframe_minutes = 60  # 1h
        self.timeframe = TimeFrame(self.timeframe_minutes, TimeFrameUnit.Minute)
        
        # Z-Score Parameters
        self.z_window = 20
        self.z_entry_threshold = 2.0
        
        # ATR Parameters
        self.atr_period = 14
        self.atr_ma_period = 50
        
        # Risk Management
        self.take_profit_pct = 0.03   # 3%
        self.stop_loss_pct = 0.01     # 1%
        
        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.tp_order_id = None
        self.sl_order_id = None
        
        # Performance tracking
        self.daily_start_capital = 10000
        self.current_capital = 10000
        self.last_trade_time = None
        self.min_time_between_trades = timedelta(hours=2)
        
        logger.info(f"Initialized ETH Vol Breakout Bot for 1h timeframe")
        logger.info(f"Parameters: Z={self.z_entry_threshold}, ATR={self.atr_period}, TP={self.take_profit_pct*100}%, SL={self.stop_loss_pct*100}%")
    
    def get_market_data(self, bars=100):
        """Fetch recent market data"""
        try:
            end = datetime.now()
            start = end - timedelta(hours=bars)
            
            barset = self.api.get_crypto_bars(
                self.symbol,
                self.timeframe,
                start=start.isoformat(),
                end=end.isoformat()
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
    
    def calculate_indicators(self, df):
        """Calculate Z-Score and ATR indicators"""
        # Z-Score
        df['SMA'] = df['Close'].rolling(self.z_window).mean()
        df['StdDev'] = df['Close'].rolling(self.z_window).std()
        df['ZScore'] = (df['Close'] - df['SMA']) / df['StdDev']
        
        # ATR for volatility regime detection
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(self.atr_period).mean()
        df['ATR_MA'] = df['ATR'].rolling(self.atr_ma_period).mean()
        
        # Volatility regime
        df['High_Vol'] = df['ATR'] > df['ATR_MA']
        
        return df
    
    def check_entry_signal(self, df):
        """Check for entry signal"""
        if len(df) < self.atr_ma_period + 10:
            return False, None
        
        current = df.iloc[-1]
        
        # Minimum time between trades
        if self.last_trade_time and datetime.now() - self.last_trade_time < self.min_time_between_trades:
            return False, None
        
        # Entry conditions:
        # 1. High volatility regime (ATR > ATR_MA)
        # 2. Z-Score breakout (> 2.0 for long, < -2.0 for short)
        
        if not current['High_Vol']:
            return False, None
        
        # Bullish breakout
        if current['ZScore'] > self.z_entry_threshold:
            return True, 'buy'
        
        # Bearish breakout
        elif current['ZScore'] < -self.z_entry_threshold:
            return True, 'sell'
        
        return False, None
    
    def check_exit_signal(self, df, position_side):
        """Check for exit signal"""
        if self.position == 0:
            return False, ""
        
        current = df.iloc[-1]
        current_price = current['Close']
        
        # Calculate PnL
        if position_side == 'long':
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Take Profit
        if pnl_pct >= self.take_profit_pct:
            return True, "TP"
        
        # Stop Loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "SL"
        
        # Trend reversal: Price crosses SMA
        if position_side == 'long' and current_price < current['SMA']:
            return True, "SMA_Cross"
        elif position_side == 'short' and current_price > current['SMA']:
            return True, "SMA_Cross"
        
        return False, ""
    
    def place_entry_order(self, current_price, side):
        """Place entry order with TP/SL"""
        try:
            # Calculate position size (use available cash)
            account = self.api.get_account()
            available_cash = float(account.cash)
            position_size = (available_cash * 0.95) / current_price  # Use 95% of cash
            position_size = round(position_size, 6)  # ETH precision
            
            if position_size < 0.001:  # Minimum ETH position
                logger.warning(f"Position size too small: {position_size}")
                return False
            
            # Place market order
            logger.info(f"🚀 ENTRY: {side.upper()} {position_size} ETH @ ${current_price:,.2f}")
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=position_size,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            
            logger.info(f"✅ Entry order placed: {order.id}")
            
            # Wait for fill
            time.sleep(2)
            
            # Update position
            self.position = position_size if side == 'buy' else -position_size
            self.entry_price = current_price
            self.last_trade_time = datetime.now()
            
            # Place TP and SL orders
            if side == 'buy':
                tp_price = current_price * (1 + self.take_profit_pct)
                sl_price = current_price * (1 - self.stop_loss_pct)
                exit_side = 'sell'
            else:
                tp_price = current_price * (1 - self.take_profit_pct)
                sl_price = current_price * (1 + self.stop_loss_pct)
                exit_side = 'buy'
            
            # Take Profit
            tp_order = self.api.submit_order(
                symbol=self.symbol,
                qty=abs(self.position),
                side=exit_side,
                type='limit',
                limit_price=round(tp_price, 2),
                time_in_force='gtc'
            )
            self.tp_order_id = tp_order.id
            logger.info(f"📈 TP order placed @ ${tp_price:,.2f}")
            
            # Stop Loss
            sl_order = self.api.submit_order(
                symbol=self.symbol,
                qty=abs(self.position),
                side=exit_side,
                type='stop',
                stop_price=round(sl_price, 2),
                time_in_force='gtc'
            )
            self.sl_order_id = sl_order.id
            logger.info(f"🛑 SL order placed @ ${sl_price:,.2f}")
            
            # Update tracker
            self.tracker.update_bot_status(self.bot_id, {
                'in_position': True,
                'position_side': side,
                'entry_price': current_price,
                'position_size': abs(self.position),
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
            
            # Determine side
            side = 'sell' if self.position > 0 else 'buy'
            
            # Place market exit
            logger.info(f"🔴 EXIT: {side.upper()} {abs(self.position)} ETH @ ${current_price:,.2f} ({reason})")
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=abs(self.position),
                side=side,
                type='market',
                time_in_force='gtc'
            )
            
            logger.info(f"✅ Exit order placed: {order.id}")
            
            # Calculate PnL
            if self.position > 0:
                pnl = self.position * (current_price - self.entry_price)
            else:
                pnl = abs(self.position) * (self.entry_price - current_price)
            
            pnl_pct = pnl / (abs(self.position) * self.entry_price) * 100
            
            logger.info(f"💰 PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            
            # Update capital
            self.current_capital += pnl
            
            # Update tracker
            self.tracker.update_bot_status(self.bot_id, {
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
        logger.info(f"🤖 Starting ETH Vol Breakout Bot (1h)")
        
        # Initialize tracker
        self.tracker.update_bot_status(self.bot_id, {
            'name': 'ETH Vol Breakout 1h',
            'strategy': 'Z-Score + ATR Volatility Breakout',
            'status': 'running',
            'in_position': False
        })
        
        position_side = None
        
        while True:
            try:
                # Get market data
                df = self.get_market_data(bars=100)
                if df is None or len(df) < self.atr_ma_period + 10:
                    logger.warning("Insufficient data, waiting...")
                    time.sleep(300)  # 5 minutes
                    continue
                
                # Calculate indicators
                df = self.calculate_indicators(df)
                current_price = df.iloc[-1]['Close']
                z_score = df.iloc[-1]['ZScore']
                is_high_vol = df.iloc[-1]['High_Vol']
                
                logger.info(f"📊 ETH: ${current_price:,.2f} | Z-Score: {z_score:.2f} | High Vol: {is_high_vol} | Position: {self.position:.6f}")
                
                # Check position status
                if self.position == 0:
                    # Check for entry
                    has_signal, side = self.check_entry_signal(df)
                    if has_signal:
                        if self.place_entry_order(current_price, side):
                            position_side = 'long' if side == 'buy' else 'short'
                else:
                    # Check for exit
                    should_exit, reason = self.check_exit_signal(df, position_side)
                    if should_exit:
                        self.place_exit_order(current_price, reason)
                        position_side = None
                
                # Update tracker
                self.tracker.update_bot_status(self.bot_id, {
                    'last_update': datetime.now().isoformat(),
                    'current_price': current_price,
                    'z_score': z_score,
                    'high_vol': bool(is_high_vol),
                    'status': 'running'
                })
                
                # Wait for next bar (1 hour)
                wait_seconds = 3600
                logger.info(f"⏳ Waiting {wait_seconds}s until next check...")
                time.sleep(wait_seconds)
            
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(300)

def signal_handler(sig, frame):
    logger.info("🛑 Shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = ETHVolBreakoutBot()
    bot.run()
