#!/usr/bin/env python3
"""
GOOGL 15m RSI Aggressive Scalping Bot - TOP VALIDATED STRATEGY
Return: 71.52%, Win Rate: 54.1%, Trades: 340, Max DD: -21.61%

Aggressive RSI-based mean reversion strategy for GOOGL.
Uses RSI(7) with oversold=25, overbought=75 levels.
Volume confirmation required for signal validity.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from grok.utils.position_sizing import calculate_position_size

from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit

try:
    from grok.utils.status_tracker import StatusTracker
except ImportError:
    # Fallback: create a dummy StatusTracker if import fails
    class StatusTracker:
        def update_status(self, bot_id, status):
            print(f"Status update: {status}")
        def update_bot_status(self, bot_id, status):
            print(f"Status update: {status}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/googl_rsi_scalping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GOOGL_RSI_SCALPING')

class GOOGLRSIScalpingBot:
    """
    RSI Aggressive Scalping Bot for GOOGL
    Optimized for 15-minute timeframe with aggressive RSI levels
    """

    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "googl_15m_rsi"

        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Trading parameters
        self.symbol = 'GOOGL'
        self.timeframe = TimeFrame(15, TimeFrameUnit.Minute)
        self.strategy_type = 'rsi_scalping_aggressive'

        # RSI parameters (from validated strategy)
        self.rsi_period = 7
        self.rsi_oversold = 25
        self.rsi_overbought = 75
        self.volume_multiplier = 1.2

        # Risk management
        self.stop_loss_pct = 0.006  # 0.6%
        self.take_profit_pct = 0.012  # 1.2%
        self.max_hold_time = 8  # bars (2 hours)
        self.max_daily_drawdown = 0.02  # 2%

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.daily_pnl = 0
        self.daily_start_pnl = 0

        # Signal tracking
        self.last_signal_time = None

        logger.info("🚀 GOOGL RSI Aggressive Scalping Bot initialized")
        logger.info(f"Strategy: {self.strategy_type}")
        logger.info(f"Symbol: {self.symbol}, Timeframe: 15m")
        logger.info(f"RSI Period: {self.rsi_period}, Oversold: {self.rsi_oversold}, Overbought: {self.rsi_overbought}")
        logger.info(f"Expected Performance: 71.52% return, 54.1% win rate")

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def get_historical_data(self, limit: int = 200) -> Optional[pd.DataFrame]:
        """Fetch historical data from Alpaca"""
        try:
            bars = self.api.get_bars(
                self.symbol,
                self.timeframe,
                limit=limit
            ).df

            if bars.empty:
                logger.warning("No historical data received")
                return None

            # Rename columns to match our format
            bars = bars.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })

            # Ensure datetime index
            bars.index = pd.to_datetime(bars.index)

            logger.info(f"Fetched {len(bars)} bars of historical data")
            return bars

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    def generate_signal(self, df: pd.DataFrame) -> int:
        """Generate trading signal using RSI aggressive logic"""
        if len(df) < self.rsi_period + 5:
            return 0

        # Calculate RSI
        rsi = self.calculate_rsi(df['Close'], self.rsi_period)

        if len(rsi) < 2:
            return 0

        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        # Volume confirmation
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]

        if current_volume < avg_volume * self.volume_multiplier:
            return 0

        # Bullish signal: RSI crosses above oversold
        if prev_rsi <= self.rsi_oversold and current_rsi > self.rsi_oversold:
            logger.info(f"RSI bullish signal: {current_rsi:.2f}")
            return 1  # Buy signal

        # Bearish signal: RSI crosses below overbought
        if prev_rsi >= self.rsi_overbought and current_rsi < self.rsi_overbought:
            logger.info(f"RSI bearish signal: {current_rsi:.2f}")
            return -1  # Sell signal

        return 0  # No signal

    def execute_trade(self, signal: int):
        """Execute trade based on signal"""
        try:
            # Check current position
            position_qty = self.get_current_position()

            if signal == 1:  # Buy signal
                if position_qty <= 0:  # No position or short position
                    if position_qty < 0:
                        # Close short position first
                        self.api.submit_order(
                            symbol=self.symbol,
                            qty=abs(position_qty),
                            side='buy',
                            type='limit',
                            limit_price=round(current_price * 1.0005, 2),  # 0.01% fee
                            time_in_force='gtc'
                        )
                        logger.info(f"Closed short position: {abs(position_qty)} shares")

                    # Calculate position size
                    qty = self.calculate_position_size()
                    if qty > 0:
                        # Submit buy order
                        order = self.api.submit_order(
                            symbol=self.symbol,
                            qty=qty,
                            side='buy',
                            type='limit',
                            limit_price=round(current_price * 1.0005, 2),  # 0.01% fee
                            time_in_force='gtc'
                        )
                        logger.info(f"BUY ORDER: {qty} shares of {self.symbol} at market")
                        self.tracker.update_bot_status(self.bot_id, f"BUY {qty} shares")

                        # Set stop loss and take profit
                        self.set_stop_loss_take_profit(order.id, qty, 'buy')

            elif signal == -1:  # Sell signal
                if position_qty >= 0:  # No position or long position
                    if position_qty > 0:
                        # Close long position first
                        self.api.submit_order(
                            symbol=self.symbol,
                            qty=position_qty,
                            side='sell',
                            type='limit',
                            limit_price=round(current_price * 1.0005, 2),  # 0.01% fee
                            time_in_force='gtc'
                        )
                        logger.info(f"Closed long position: {position_qty} shares")

                    # Calculate position size
                    qty = self.calculate_position_size()
                    if qty > 0:
                        # Submit sell order
                        order = self.api.submit_order(
                            symbol=self.symbol,
                            qty=qty,
                            side='sell',
                            type='limit',
                            limit_price=round(current_price * 1.0005, 2),  # 0.01% fee
                            time_in_force='gtc'
                        )
                        logger.info(f"SELL ORDER: {qty} shares of {self.symbol} at market")
                        self.tracker.update_bot_status(self.bot_id, f"SELL {qty} shares")

                        # Set stop loss and take profit
                        self.set_stop_loss_take_profit(order.id, qty, 'sell')

        except Exception as e:
            logger.error(f"Error executing trade: {e}")

    def set_stop_loss_take_profit(self, order_id: str, qty: int, side: str):
        """Set stop loss and take profit orders"""
        try:
            # Get current price
            current_price = self.api.get_latest_quote(self.symbol).askprice

            if side == 'buy':
                stop_loss_price = current_price * (1 - self.stop_loss_pct)
                take_profit_price = current_price * (1 + self.take_profit_pct)
            else:  # sell
                stop_loss_price = current_price * (1 + self.stop_loss_pct)
                take_profit_price = current_price * (1 - self.take_profit_pct)

            # Stop loss order
            sl_order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side='sell' if side == 'buy' else 'buy',
                type='stop',
                stop_price=stop_loss_price,
                time_in_force='gtc'
            )

            # Take profit order
            tp_order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side='sell' if side == 'buy' else 'buy',
                type='limit',
                limit_price=take_profit_price,
                time_in_force='gtc'
            )

            logger.info(f"Set SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}")

        except Exception as e:
            logger.error(f"Error setting stop loss/take profit: {e}")

    def calculate_position_size(self) -> int:
        """Calculate position size based on risk management"""
        try:
            account = self.api.get_account()
            equity = float(account.equity)
            current_price = float(self.api.get_latest_quote(self.symbol).askprice)
            
            position_size = calculate_position_size(
                bot_id=self.bot_id,
                account_equity=equity,
                entry_price=current_price
            )
            return int(position_size)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 1  # Default to 1 share

    def get_current_position(self) -> int:
        """Get current position quantity"""
        try:
            positions = self.api.list_positions()
            for position in positions:
                if position.symbol == self.symbol:
                    return int(position.qty)
            return 0
        except Exception as e:
            logger.error(f"Error getting current position: {e}")
            return 0

    def check_daily_drawdown(self) -> bool:
        """Check if daily drawdown limit reached"""
        try:
            account = self.api.get_account()
            current_equity = float(account.equity)
            daily_start_equity = self.daily_start_pnl

            if daily_start_equity == 0:
                self.daily_start_pnl = current_equity
                return False

            drawdown = (current_equity - daily_start_equity) / daily_start_equity
            return drawdown <= -self.max_daily_drawdown

        except Exception as e:
            logger.error(f"Error checking daily drawdown: {e}")
            return False

    def run(self):
        """Main bot loop"""
        logger.info("🎯 Starting GOOGL RSI Aggressive Scalping Bot")
        self.tracker.update_bot_status(self.bot_id, "STARTED")

        while True:
            try:
                # Update dashboard status
                try:
                    account = self.api.get_account()
                    positions = self.api.list_positions()
                    pos = next((p for p in positions if p.symbol == self.symbol), None)
                    
                    self.tracker.update_status(self.bot_id, {
                        'equity': float(account.equity),
                        'cash': float(account.cash),
                        'position': float(pos.qty) if pos else 0,
                        'entry_price': float(pos.avg_entry_price) if pos else 0,
                        'unrealized_pl': float(pos.unrealized_pl) if pos else 0,
                        'error': None
                    })
                except Exception as e:
                    logger.error(f"Status update failed: {e}")
                    self.tracker.update_status(self.bot_id, {'error': str(e)})

                # Check if market is open
                clock = self.api.get_clock()
                if not clock.is_open:
                    logger.info("Market is closed, sleeping...")
                    time.sleep(300)  # Sleep 5 minutes
                    continue

                # Check daily drawdown
                if self.check_daily_drawdown():
                    logger.warning("Daily drawdown limit reached, stopping for today")
                    self.tracker.update_bot_status(self.bot_id, "DAILY_DD_LIMIT")
                    time.sleep(3600)  # Sleep 1 hour
                    continue

                # Get historical data
                df = self.get_historical_data(100)
                if df is None or df.empty:
                    logger.warning("Could not fetch historical data")
                    time.sleep(60)
                    continue

                # Generate signal
                signal = self.generate_signal(df)

                # Execute trade if signal generated
                if signal != 0:
                    self.execute_trade(signal)
                    self.last_signal_time = datetime.now()

                # Update status
                position_qty = self.get_current_position()
                self.tracker.update_bot_status(self.bot_id, f"RUNNING - Position: {position_qty}")

                # Sleep before next iteration (15-minute intervals)
                time.sleep(900)  # 15 minutes

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.tracker.update_bot_status(self.bot_id, f"ERROR: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    bot = GOOGLRSIScalpingBot()
    bot.run()
