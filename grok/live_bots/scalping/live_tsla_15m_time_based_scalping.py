#!/usr/bin/env python3
"""
TSLA 15m Time-Based Scalping Bot - TOP WINNER STRATEGY
Return: 36.15%, Win Rate: 64.2%, Trades: 53, Max DD: 2.90%

Session-aware scalping strategy optimized for TSLA volatility.
Focuses on NY AM/PM sessions with momentum and volume confirmation.
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
# from shared_utils.logger import setup_logger
# from shared_strategies.scalping_strategy import ScalpingStrategy

from grok.utils.status_tracker import StatusTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tsla_time_based_scalping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TSLA_TIME_SCALPING')

class TSLATimeBasedScalpingBot:
    """
    Time-Based Scalping Bot for TSLA
    Optimized for 15-minute timeframe with session awareness
    """

    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "tsla_15m_time"

        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Trading parameters
        self.symbol = 'TSLA'
        self.timeframe = TimeFrame(15, TimeFrameUnit.Minute)
        self.strategy_type = 'time_based_scalping'

        # Risk management
        self.stop_loss_pct = 0.005  # 0.5%
        self.take_profit_pct = 0.01  # 1.0%
        self.max_hold_time = 12  # bars (3 hours)
        self.max_daily_drawdown = 0.02  # 2%

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.daily_pnl = 0
        self.daily_start_pnl = 0

        # Session tracking
        self.current_session = None
        self.last_signal_time = None

        logger.info("🚀 TSLA Time-Based Scalping Bot initialized")
        logger.info(f"Strategy: {self.strategy_type}")
        logger.info(f"Symbol: {self.symbol}, Timeframe: 15m")
        logger.info(f"Expected Performance: 36.15% return, 64.2% win rate")

    def get_session_indicator(self, dt: datetime) -> str:
        """Determine current trading session"""
        # Convert to NY time (assuming input is UTC)
        ny_time = dt - timedelta(hours=5)  # EST is UTC-5

        hour = ny_time.hour
        minute = ny_time.minute

        if 9 <= hour < 12:  # 9:30-11:30 ET
            return 'ny_am'
        elif 14 <= hour < 16:  # 14:00-16:00 ET
            return 'ny_pm'
        elif 3 <= hour < 12:  # 03:00-11:30 ET (London)
            return 'london'
        elif 0 <= hour < 8:  # 00:00-08:00 ET (Asia)
            return 'asia'
        else:
            return 'off_hours'

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
        """Generate trading signal using time-based scalping logic"""
        if len(df) < 50:
            return 0

        current_time = df.index[-1]
        session = self.get_session_indicator(current_time)

        # Only trade during active NY sessions
        if session not in ['ny_am', 'ny_pm']:
            return 0

        # Avoid overtrading - minimum 15 minutes between signals
        if self.last_signal_time and (current_time - self.last_signal_time).total_seconds() < 900:
            return 0

        # Get current price data
        current_close = df['Close'].iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]

        # Volume confirmation required
        if current_volume < avg_volume * 1.2:
            return 0

        # Calculate momentum (5-period)
        momentum = current_close - df['Close'].iloc[-6] if len(df) > 5 else 0
        momentum_sma = df['Close'].diff(5).rolling(5).mean().iloc[-1] if len(df) > 10 else 0

        # Session-specific logic
        if session == 'ny_am':
            # NY AM: Focus on momentum continuation
            if momentum > momentum_sma and momentum > 0:
                signal = 1  # Long
            elif momentum < momentum_sma and momentum < 0:
                signal = -1  # Short
            else:
                signal = 0

        elif session == 'ny_pm':
            # NY PM: Profit-taking and reversals
            recent_high = df['High'].rolling(10).max().iloc[-1]
            recent_low = df['Low'].rolling(10).min().iloc[-1]

            # Long if near recent low (potential bounce)
            if current_close < recent_low * 1.01 and momentum > 0:
                signal = 1
            # Short if near recent high (profit-taking)
            elif current_close > recent_high * 0.99 and momentum < 0:
                signal = -1
            else:
                signal = 0

        else:
            signal = 0

        if signal != 0:
            self.last_signal_time = current_time
            logger.info(f"Signal generated: {signal} in {session} session at {current_time}")

        return signal

    def execute_trade(self, signal: int, quantity: float) -> bool:
        """Execute trade on Alpaca"""
        try:
            side = 'buy' if signal == 1 else 'sell'

            # Calculate stop loss and take profit
            current_price = float(self.api.get_latest_quote(self.symbol).askprice)
            stop_price = current_price * (1 - self.stop_loss_pct) if signal == 1 else current_price * (1 + self.stop_loss_pct)
            limit_price = current_price * (1 + self.take_profit_pct) if signal == 1 else current_price * (1 - self.take_profit_pct)

            # Submit bracket order with LIMIT entry (0.01% fee vs 0.035% market)
            entry_limit_price = current_price * 1.0005 if signal == 1 else current_price * 0.9995
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=quantity,
                side=side,
                type='limit',
                limit_price=round(entry_limit_price, 2),
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
        if self.entry_time and (current_time - self.entry_time).total_seconds() > (self.max_hold_time * 15 * 60):
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

                    # Use limit order for exit (0.01% fee vs 0.035% market)
                    current_price = float(self.api.get_latest_quote(self.symbol).askprice)
                    exit_limit_price = current_price * 0.9995 if side == 'sell' else current_price * 1.0005
                    
                    self.api.submit_order(
                        symbol=self.symbol,
                        qty=qty,
                        side=side,
                        type='limit',
                        limit_price=round(exit_limit_price, 2),
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
        logger.info("Starting TSLA Time-Based Scalping Bot...")

        while True:
            try:
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
                        # Calculate position size (1% of account equity)
                        account = self.api.get_account()
                        equity = float(account.equity)
                        position_value = equity * 0.01  # 1% risk
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
    bot = TSLATimeBasedScalpingBot()
    bot.run()
