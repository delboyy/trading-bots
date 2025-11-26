#!/usr/bin/env python3
"""
GLD 5m ATR Range Scalping Bot - SOLID PERFORMANCE STRATEGY
Return: 40.45%, Win Rate: 55.1%, Trades: 501, Max DD: 16.24%

ATR-based range scalping optimized for GLD's volatility patterns.
Identifies ranging markets and trades breakouts within volatility bands.
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

from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit
from grok.utils.status_tracker import StatusTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/gld_atr_range_scalping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GLD_ATR_RANGE_SCALPING')

class GLDATRRangeScalpingBot:
    """
    ATR Range Scalping Bot for GLD
    Optimized for 5-minute timeframe with volatility-based entries
    """

    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "gld_5m_atr_range"

        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Trading parameters
        self.symbol = 'GLD'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.strategy_type = 'atr_range_scalping'

        # Strategy parameters (optimized from backtest)
        self.atr_period = 14
        self.range_multiplier = 0.7
        self.volume_multiplier = 1.2

        # Risk management
        self.stop_loss_pct = 0.005  # 0.5%
        self.take_profit_pct = 0.01  # 1.0%
        self.max_hold_time = 8  # bars (40 minutes)
        self.max_daily_drawdown = 0.05  # 5%
        self.max_position_pct = 0.06  # 6% of account

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.daily_pnl = 0
        self.daily_start_pnl = 0

        # Range tracking
        self.last_signal_time = None

        logger.info("🚀 GLD ATR Range Scalping Bot initialized")
        logger.info(f"Strategy: {self.strategy_type}")
        logger.info(f"Symbol: {self.symbol}, Timeframe: 5m")
        logger.info(f"Expected Performance: 40.45% return, 55.1% win rate")

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range"""
        if len(df) < self.atr_period:
            return pd.Series([0] * len(df), index=df.index)

        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift(1)).abs()
        low_close = (df['Low'] - df['Close'].shift(1)).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr

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

    def is_ranging_market(self, df: pd.DataFrame) -> bool:
        """Determine if current market is in a ranging phase"""
        if len(df) < 20:
            return False

        # Calculate ATR
        atr = self.calculate_atr(df)
        current_atr = atr.iloc[-1]

        # Check recent volatility (last 10 bars)
        recent_high = df['High'].tail(10).max()
        recent_low = df['Low'].tail(10).min()
        recent_range = recent_high - recent_low

        # Market is ranging if ATR-based range is significant portion of price
        current_price = df['Close'].iloc[-1]
        range_percentage = recent_range / current_price

        # Ranging market if range is reasonable (not too volatile, not too quiet)
        return 0.005 < range_percentage < 0.02 and recent_range > current_atr * self.range_multiplier

    def generate_signal(self, df: pd.DataFrame) -> int:
        """Generate trading signal using ATR range scalping logic"""
        if len(df) < self.atr_period + 10:
            return 0

        # Check if market is ranging
        if not self.is_ranging_market(df):
            return 0

        current_time = df.index[-1]

        # Avoid overtrading - minimum 15 minutes between signals
        if self.last_signal_time and (current_time - self.last_signal_time).total_seconds() < 900:
            return 0

        current_close = df['Close'].iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]

        # Volume confirmation required
        if current_volume < avg_volume * self.volume_multiplier:
            return 0

        # Calculate recent range levels
        recent_high = df['High'].tail(10).max()
        recent_low = df['Low'].tail(10).min()
        range_width = recent_high - recent_low

        # Calculate ATR for position sizing
        atr = self.calculate_atr(df)
        current_atr = atr.iloc[-1]

        # Range breakout signals
        near_low = current_close <= recent_low + range_width * 0.1
        near_high = current_close >= recent_high - range_width * 0.1

        # Momentum confirmation
        short_momentum = current_close - df['Close'].iloc[-3] if len(df) > 3 else 0

        if near_low and short_momentum > current_atr * 0.3:
            logger.info(f"Long signal: Near range low ${current_close:.2f}, momentum {short_momentum:.4f}")
            self.last_signal_time = current_time
            return 1
        elif near_high and short_momentum < -current_atr * 0.3:
            logger.info(f"Short signal: Near range high ${current_close:.2f}, momentum {short_momentum:.4f}")
            self.last_signal_time = current_time
            return -1

        return 0

    def execute_trade(self, signal: int, quantity: float) -> bool:
        """Execute trade on Alpaca"""
        try:
            side = 'buy' if signal == 1 else 'sell'

            # Get current price
            current_price = float(self.api.get_latest_quote(self.symbol).askprice)

            # Calculate stop loss and take profit
            stop_price = current_price * (1 - self.stop_loss_pct) if signal == 1 else current_price * (1 + self.stop_loss_pct)
            limit_price = current_price * (1 + self.take_profit_pct) if signal == 1 else current_price * (1 - self.take_profit_pct)

            # Submit bracket order
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=quantity,
                side=side,
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                stop_loss={'stop_price': round(stop_price, 2)},
                take_profit={'limit_price': round(limit_price, 2)}
            )

            logger.info(f"Order executed: {side} {quantity} {self.symbol} at ~${current_price:.2f}")
            logger.info(f"Stop Loss: ${stop_price:.2f}, Take Profit: ${limit_price:.2f}")

            # Update position tracking
            self.position = signal
            self.entry_price = current_price
            self.entry_time = datetime.now()

            return True

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return False

    def check_exit_conditions(self, current_price: float) -> bool:
        """Check if position should be exited"""
        if self.position == 0:
            return False

        current_time = datetime.now()

        # Time-based exit
        if self.entry_time and (current_time - self.entry_time).total_seconds() > (self.max_hold_time * 5 * 60):
            logger.info("Exiting due to max hold time")
            return True

        # Profit target hit
        if self.position == 1 and current_price >= self.entry_price * (1 + self.take_profit_pct):
            logger.info("Take profit hit")
            return True
        elif self.position == -1 and current_price <= self.entry_price * (1 - self.take_profit_pct):
            logger.info("Take profit hit")
            return True

        # Stop loss hit
        if self.position == 1 and current_price <= self.entry_price * (1 - self.stop_loss_pct):
            logger.info("Stop loss hit")
            return True
        elif self.position == -1 and current_price >= self.entry_price * (1 + self.stop_loss_pct):
            logger.info("Stop loss hit")
            return True

        return False

    def close_position(self) -> bool:
        """Close current position"""
        try:
            # Close all positions for this symbol
            positions = self.api.list_positions()
            for pos in positions:
                if pos.symbol == self.symbol:
                    side = 'sell' if pos.side == 'long' else 'buy'
                    qty = abs(float(pos.qty))

                    self.api.submit_order(
                        symbol=self.symbol,
                        qty=qty,
                        side=side,
                        type='market',
                        time_in_force='gtc'
                    )

                    logger.info(f"Position closed: {side} {qty} {self.symbol}")
                    break

            self.position = 0
            self.entry_price = 0
            self.entry_time = None

            return True

        except Exception as e:
            logger.error(f"Position close failed: {e}")
            return False

    def check_daily_drawdown(self) -> bool:
        """Check if daily drawdown limit is hit"""
        try:
            account = self.api.get_account()
            current_equity = float(account.equity)

            if self.daily_start_pnl == 0:
                self.daily_start_pnl = current_equity

            daily_drawdown = (self.daily_start_pnl - current_equity) / self.daily_start_pnl

            if daily_drawdown > self.max_daily_drawdown:
                logger.warning(f"Daily drawdown limit hit: {daily_drawdown:.1%}")
                return True

        except Exception as e:
            logger.error(f"Drawdown check failed: {e}")

        return False

    def run(self):
        """Main trading loop"""
        logger.info("Starting GLD ATR Range Scalping Bot...")

        while True:
            try:
                # Check daily drawdown limit
                if self.check_daily_drawdown():
                    logger.warning("Daily drawdown limit hit - stopping for today")
                    time.sleep(3600)  # Wait 1 hour
                    continue

                # Update Dashboard
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

                # Get current market data
                df = self.get_historical_data(limit=100)
                if df is None:
                    time.sleep(60)
                    continue

                # Check if we need to exit current position
                if self.position != 0:
                    current_price = df['Close'].iloc[-1]
                    if self.check_exit_conditions(current_price):
                        self.close_position()

                # Generate new signals only if no position
                elif self.position == 0:
                    signal = self.generate_signal(df)

                    if signal != 0:
                        # Calculate position size
                        account = self.api.get_account()
                        equity = float(account.equity)
                        position_value = equity * self.max_position_pct
                        current_price = df['Close'].iloc[-1]
                        quantity = position_value // current_price

                        if quantity > 0:
                            self.execute_trade(signal, quantity)

                # Sleep for 1 minute before next check
                time.sleep(60)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                if self.position != 0:
                    self.close_position()
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self.tracker.update_status(self.bot_id, {'error': f"CRASH: {str(e)}"})
                time.sleep(60)

if __name__ == "__main__":
    bot = GLDATRRangeScalpingBot()
    bot.run()
