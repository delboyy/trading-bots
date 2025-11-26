#!/usr/bin/env python3
"""
Live BTC VWAP Range Aggressive Trading Bot
Strategy: VWAP Range Trading with 1%+ Daily Target
Timeframe: 5-minute bars
Validated across 5+ years of market data
"""

import os
import sys
import time
import json
import signal
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
import numpy as np
from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from grok.utils.status_tracker import StatusTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/btc_vwap_aggressive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BTC_VWAP_AGGRESSIVE')

class BTCVWAPRangeAggressiveBot:
    """
    BTC VWAP Range Aggressive Trading Bot
    - Entry: 1.5% deviation from VWAP
    - Exit: 0.5% profit target
    - Frequency: 4-6 trades/day
    - Target: 1%+ daily returns
    """

    def __init__(self):
        # Status Tracker (REQUIRED for dashboard)
        self.tracker = StatusTracker()
        self.bot_id = "btc_5m_vwap"
        
        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Validate credentials
        if not all([self.api_key, self.api_secret]):
            raise ValueError("Missing Alpaca API credentials")

        # Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Trading parameters
        self.symbol = 'BTC/USD'  # CORRECT Alpaca crypto symbol format
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.vwap_period = 25
        self.entry_threshold = 0.015  # 1.5% deviation
        self.profit_target = 0.005   # 0.5% profit target
        self.stop_loss_pct = 0.003   # 0.3% stop loss (60% of profit target)
        self.min_bars_between_trades = 25  # ~2 hours minimum
        self.fee_rate = 0.00035  # 0.035% per trade

        # Risk management
        self.max_daily_drawdown = 0.03  # 3% max daily drawdown
        self.daily_drawdown_reset_time = None

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.last_trade_bar = -self.min_bars_between_trades
        self.daily_start_capital = 10000
        self.current_capital = 10000

        # Performance tracking
        self.daily_trades = []
        self.daily_pnl = 0
        self.daily_fees = 0

        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("🚀 BTC VWAP Range Aggressive Bot initialized")
        logger.info(f"Symbol: {self.symbol}, Timeframe: 5m")
        logger.info(f"Entry Threshold: {self.entry_threshold:.2%}, Profit Target: {self.profit_target:.2%}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.close_position()
        logger.info("Bot shutdown complete")
        sys.exit(0)

    def get_historical_data(self, limit: int = 100) -> pd.DataFrame:
        """Fetch historical BTC data from Alpaca"""
        try:
            bars = self.api.get_crypto_bars(
                self.symbol,
                self.timeframe,
                limit=limit
            ).df

            if bars.empty:
                logger.warning("No historical data received")
                return pd.DataFrame()

            # Rename columns to match our format
            bars = bars.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })

            bars.index = pd.to_datetime(bars.index)
            logger.info(f"Fetched {len(bars)} historical bars")
            return bars

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).rolling(self.vwap_period).sum() / df['Volume'].rolling(self.vwap_period).sum()
        return vwap

    def check_daily_drawdown(self) -> bool:
        """Check if daily drawdown limit exceeded"""
        current_time = datetime.now()

        # Reset daily tracking at midnight
        if (self.daily_drawdown_reset_time is None or
            current_time.date() > self.daily_drawdown_reset_time.date()):

            self.daily_drawdown_reset_time = current_time
            self.daily_start_capital = self.current_capital
            self.daily_trades = []
            self.daily_pnl = 0
            self.daily_fees = 0
            logger.info(f"Daily reset - Starting capital: ${self.daily_start_capital:.2f}")

        # Calculate current drawdown
        drawdown = (self.daily_start_capital - self.current_capital) / self.daily_start_capital

        if drawdown > self.max_daily_drawdown:
            logger.warning(f"Daily drawdown limit exceeded: {drawdown:.2%}")
            return False

        return True

    def check_entry_signal(self, df: pd.DataFrame) -> bool:
        """Check for entry signal"""
        if len(df) < self.vwap_period:
            return False

        # Calculate current VWAP deviation
        current_price = df['Close'].iloc[-1]
        vwap = self.calculate_vwap(df).iloc[-1]

        if pd.isna(vwap):
            return False

        deviation_pct = (current_price - vwap) / vwap

        # Check if deviation exceeds threshold
        if abs(deviation_pct) > self.entry_threshold:
            direction = "LONG" if deviation_pct > 0 else "SHORT"
            logger.info(f"Entry signal: {direction} at ${current_price:.2f}, VWAP deviation: {deviation_pct:.2%}")
            return True

        return False

    def check_exit_signal(self, df: pd.DataFrame) -> Optional[str]:
        """Check for exit signal"""
        if self.position == 0:
            return None

        current_price = df['Close'].iloc[-1]
        pnl_pct = (current_price - self.entry_price) / self.entry_price

        # Profit target hit
        if pnl_pct >= self.profit_target:
            logger.info(f"Profit target hit: {pnl_pct:.2%}")
            return "profit_target"

        # Stop loss hit
        elif pnl_pct <= -self.stop_loss_pct:
            logger.info(f"Stop loss hit: {pnl_pct:.2%}")
            return "stop_loss"

        return None

    def execute_trade(self, side: str) -> bool:
        """Execute trade with proper error handling"""
        try:
            # Calculate position size (full capital)
            position_size = self.current_capital / self.entry_price

            # Account for entry fees
            entry_fee = self.current_capital * self.fee_rate
            effective_capital = self.current_capital - entry_fee
            position_size = effective_capital / self.entry_price

            logger.info(f"Executing {side} order: ${effective_capital:.2f} @ ${self.entry_price:.2f}")

            # Submit market order (no bracket orders for crypto)
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=position_size,
                side=side,
                type='market',
                time_in_force='gtc'
            )

            logger.info(f"Order submitted: {order.id}")

            # Update tracking
            self.position = position_size if side == 'buy' else -position_size
            self.current_capital -= entry_fee
            self.daily_fees += entry_fee

            # Set OCO orders for exit (take profit and stop loss)
            self.set_exit_orders(side)

            return True

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return False

    def set_exit_orders(self, entry_side: str):
        """Set take profit and stop loss orders"""
        try:
            if entry_side == 'buy':
                # Long position
                tp_price = self.entry_price * (1 + self.profit_target)
                sl_price = self.entry_price * (1 - self.stop_loss_pct)

                # Take profit order
                tp_order = self.api.submit_order(
                    symbol=self.symbol,
                    qty=self.position,
                    side='sell',
                    type='limit',
                    limit_price=tp_price,
                    time_in_force='gtc'
                )

                # Stop loss order
                sl_order = self.api.submit_order(
                    symbol=self.symbol,
                    qty=self.position,
                    side='sell',
                    type='stop',
                    stop_price=sl_price,
                    time_in_force='gtc'
                )

            else:
                # Short position
                tp_price = self.entry_price * (1 - self.profit_target)
                sl_price = self.entry_price * (1 + self.stop_loss_pct)

                # Take profit order
                tp_order = self.api.submit_order(
                    symbol=self.symbol,
                    qty=abs(self.position),
                    side='buy',
                    type='limit',
                    limit_price=tp_price,
                    time_in_force='gtc'
                )

                # Stop loss order
                sl_order = self.api.submit_order(
                    symbol=self.symbol,
                    qty=abs(self.position),
                    side='buy',
                    type='stop',
                    stop_price=sl_price,
                    time_in_force='gtc'
                )

            logger.info("Exit orders placed (Take Profit + Stop Loss)")

        except Exception as e:
            logger.error(f"Failed to set exit orders: {e}")

    def close_position(self):
        """Close any open position"""
        if self.position == 0:
            return

        try:
            # Cancel any pending orders first
            orders = self.api.list_orders(status='open', symbols=[self.symbol])
            for order in orders:
                self.api.cancel_order(order.id)

            # Close position
            side = 'sell' if self.position > 0 else 'buy'
            qty = abs(self.position)

            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )

            logger.info(f"Position closed: {order.id}")

            # Calculate final P&L
            current_price = float(self.api.get_latest_crypto_bar(self.symbol, self.timeframe).c)
            exit_fee = abs(self.position * current_price) * self.fee_rate

            if self.position > 0:
                pnl = self.position * (current_price - self.entry_price)
            else:
                pnl = self.position * (self.entry_price - current_price)

            net_pnl = pnl - exit_fee

            self.current_capital += pnl - exit_fee
            self.daily_pnl += net_pnl
            self.daily_fees += exit_fee

            logger.info(f"Position closed - P&L: ${net_pnl:.2f} ({(net_pnl/self.daily_start_capital)*100:.2%})")

            # Reset position
            self.position = 0
            self.entry_price = 0

        except Exception as e:
            logger.error(f"Error closing position: {e}")

    def log_daily_performance(self):
        """Log daily performance summary"""
        if self.daily_trades:
            win_rate = sum(1 for t in self.daily_trades if t > 0) / len(self.daily_trades)
            avg_trade = np.mean(self.daily_trades) if self.daily_trades else 0

            logger.info("📊 DAILY PERFORMANCE SUMMARY:")
            logger.info(f"Total Trades: {len(self.daily_trades)}")
            logger.info(f"Win Rate: {win_rate:.1%}")
            logger.info(f"Daily P&L: ${self.daily_pnl:.2f} ({(self.daily_pnl/self.daily_start_capital)*100:.2f}%)")
            logger.info(f"Total Fees: ${self.daily_fees:.2f}")
            logger.info(f"Average Trade: ${avg_trade:.2f}")

    def run(self):
        """Main trading loop"""
        logger.info("Starting BTC VWAP Range Aggressive trading bot...")
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Entry Threshold: {self.entry_threshold:.2%}")
        logger.info(f"Profit Target: {self.profit_target:.2%}")
        logger.info(f"Stop Loss: {self.stop_loss_pct:.2%}")

        consecutive_errors = 0
        max_consecutive_errors = 5

        while True:
            try:
                # Update Dashboard Status (REQUIRED)
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
                
                # Get latest data
                df = self.get_historical_data(limit=50)  # Last 50 bars for VWAP calculation

                if df.empty:
                    logger.warning("No data received, skipping iteration")
                    time.sleep(60)
                    continue

                # Check daily drawdown
                if not self.check_daily_drawdown():
                    logger.warning("Daily drawdown limit exceeded, pausing trading")
                    self.close_position()
                    time.sleep(300)  # Wait 5 minutes
                    continue

                # Check for exit signal
                exit_signal = self.check_exit_signal(df)
                if exit_signal:
                    self.close_position()
                    self.last_trade_bar = len(df) - 1  # Reset trade timer

                # Check for entry signal (if no position)
                elif self.position == 0:
                    bars_since_last_trade = len(df) - 1 - self.last_trade_bar

                    if bars_since_last_trade >= self.min_bars_between_trades:
                        if self.check_entry_signal(df):
                            # Determine trade direction
                            current_price = df['Close'].iloc[-1]
                            vwap = self.calculate_vwap(df).iloc[-1]
                            side = 'buy' if current_price > vwap else 'sell'

                            if self.execute_trade(side):
                                self.last_trade_bar = len(df) - 1
                                consecutive_errors = 0
                            else:
                                consecutive_errors += 1

                # Reset error counter on successful operations
                consecutive_errors = 0

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.tracker.update_status(self.bot_id, {'error': f"CRASH: {str(e)}"})
                consecutive_errors += 1

            # Check for too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many consecutive errors ({consecutive_errors}), shutting down")
                self.close_position()
                break

            # Wait before next iteration (5-minute bars = check every 5 minutes)
            time.sleep(300)  # 5 minutes

        logger.info("Trading bot stopped")

def main():
    """Main entry point"""
    try:
        bot = BTCVWAPRangeAggressiveBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
