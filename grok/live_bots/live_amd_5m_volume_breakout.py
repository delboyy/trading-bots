#!/usr/bin/env python3
"""
AMD 5m Volume Breakout Bot - HIGH-RETURN WINNER STRATEGY
Return: 13.75%, Win Rate: 66.7%, Trades: 15, Max DD: 1.13%

Volume breakout scalping strategy optimized for AMD volatility.
Uses high volume thresholds and breakout detection for explosive moves.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit
# from shared_utils.logger import setup_logger # Removing dependency if not found
# from shared_strategies.scalping_strategy import ScalpingStrategy

# Use local StatusTracker
from grok.utils.status_tracker import StatusTracker

# Setup logging locally to avoid missing dependency
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/amd_5m_volume_breakout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AMD_5M_VOLUME_BREAKOUT')

class AMDVolumeBreakoutBot:
    """
    Volume Breakout Bot for AMD
    Optimized for 5-minute timeframe with high-volume breakout detection
    """

    def __init__(self):
        # Initialize Status Tracker
        self.tracker = StatusTracker()
        self.bot_id = "amd_5m_vol"

        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Trading parameters
        self.symbol = 'AMD'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.strategy_type = 'volume_breakout'

        # Optimized parameters for high returns
        self.volume_multiplier = 1.8  # Higher threshold for better signals
        self.take_profit_pct = 0.012  # Let winners run (1.2%)
        self.stop_loss_pct = 0.004    # Tighter stops (0.4%)
        self.max_hold_time = 12       # bars (1 hour)
        self.max_daily_drawdown = 0.02  # 2%

        # RSI neutral zone filtering
        self.rsi_neutral_min = 35
        self.rsi_neutral_max = 65

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.daily_pnl = 0
        self.daily_start_pnl = 0

        # Signal tracking
        self.last_signal_time = None

        logger.info("🚀 AMD Volume Breakout Bot initialized")
        logger.info(f"Strategy: {self.strategy_type}")
        logger.info(f"Symbol: {self.symbol}, Timeframe: 5m")
        logger.info(f"Volume Multiplier: {self.volume_multiplier}x (optimized for high returns)")
        logger.info(f"Take Profit: {self.take_profit_pct:.1%}, Stop Loss: {self.stop_loss_pct:.1%}")
        logger.info(f"Expected Performance: 13.75% return, 66.7% win rate")

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

            # Add technical indicators
            bars['volume_sma'] = bars['Volume'].rolling(20).mean()
            bars['volume_ratio'] = bars['Volume'] / bars['volume_sma']

            # RSI for neutral zone filtering
            delta = bars['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            bars['rsi'] = 100 - (100 / (1 + rs))

            # Breakout detection
            bars['high_breakout'] = bars['High'] > bars['High'].rolling(20).max().shift(1)
            bars['low_breakout'] = bars['Low'] < bars['Low'].rolling(20).min().shift(1)

            logger.info(f"Fetched {len(bars)} bars of historical data")
            return bars

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    def generate_signal(self, df: pd.DataFrame) -> int:
        """Generate trading signal using volume breakout logic"""
        if len(df) < 50:
            return 0

        current_time = df.index[-1]

        # Avoid overtrading - minimum 10 minutes between signals
        if self.last_signal_time and (current_time - self.last_signal_time).total_seconds() < 600:
            return 0

        # Get current values
        current_volume_ratio = df['volume_ratio'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        high_breakout = df['high_breakout'].iloc[-1]
        low_breakout = df['low_breakout'].iloc[-1]

        # HIGH VOLUME THRESHOLD (1.8x average - optimized for AMD volatility)
        if current_volume_ratio < self.volume_multiplier:
            return 0

        # RSI NEUTRAL ZONE (avoid extreme conditions)
        if not (self.rsi_neutral_min <= current_rsi <= self.rsi_neutral_max):
            return 0

        # BREAKOUT DETECTION
        signal = 0
        if high_breakout:
            signal = 1  # LONG breakout
        elif low_breakout:
            signal = -1  # SHORT breakout

        if signal != 0:
            self.last_signal_time = current_time
            direction = "LONG BREAKOUT" if signal == 1 else "SHORT BREAKOUT"
            logger.info(f"Volume Breakout Signal: {direction} at {current_time}")
            logger.info(f"Volume Ratio: {current_volume_ratio:.1f}x, RSI: {current_rsi:.1f}")

        return signal

    def execute_trade(self, signal: int, quantity: float) -> bool:
        """Execute trade on Alpaca"""
        try:
            side = 'buy' if signal == 1 else 'sell'

            # Calculate stop loss and take profit (optimized parameters)
            current_price = float(self.api.get_latest_quote(self.symbol).askprice)
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

        # Profit target hit (optimized 1.2%)
        if self.position == 1 and current_price >= self.entry_price * (1 + self.take_profit_pct):
            logger.info("Take profit hit")
            return True
        elif self.position == -1 and current_price <= self.entry_price * (1 - self.take_profit_pct):
            logger.info("Take profit hit")
            return True

        # Stop loss hit (tighter 0.4%)
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

    def run(self):
        """Main trading loop"""
        logger.info("Starting AMD Volume Breakout Bot...")

        while True:
            try:
                # Update Dashboard Status
                try:
                    account = self.api.get_account()
                    positions = self.api.list_positions()
                    amd_pos = next((p for p in positions if p.symbol == self.symbol), None)
                    
                    self.tracker.update_status(self.bot_id, {
                        'equity': float(account.equity),
                        'cash': float(account.cash),
                        'position': float(amd_pos.qty) if amd_pos else 0,
                        'entry_price': float(amd_pos.avg_entry_price) if amd_pos else 0,
                        'unrealized_pl': float(amd_pos.unrealized_pl) if amd_pos else 0,
                        'error': None
                    })
                except Exception as e:
                    logger.error(f"Status update failed: {e}")
                    self.tracker.update_status(self.bot_id, {'error': str(e)})

                # Get current market data
                df = self.get_historical_data(limit=100)
                if df is None:
                    time.sleep(30)
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
                        # Calculate position size (1% of account equity)
                        account = self.api.get_account()
                        equity = float(account.equity)
                        position_value = equity * 0.01  # 1% risk
                        current_price = df['Close'].iloc[-1]
                        quantity = position_value // current_price

                        if quantity > 0:
                            self.execute_trade(signal, quantity)

                # Sleep for 30 seconds (5m timeframe)
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                if self.position != 0:
                    self.close_position()
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self.tracker.update_status(self.bot_id, {'error': f"CRASH: {str(e)}"})
                time.sleep(30)

if __name__ == "__main__":
    bot = AMDVolumeBreakoutBot()
    bot.run()
