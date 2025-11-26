#!/usr/bin/env python3
"""
GLD Fibonacci Momentum Scalping Bot
Winner from GLD Strategy Lockdown - 57.43% return, 64% win rate
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

class GLDFibonacciMomentumBot:
    def __init__(self):
        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Initialize Alpaca API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters (from lockdown winner)
        self.symbol = 'GLD'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.fib_levels = [0.236, 0.382, 0.618, 0.786]
        self.momentum_period = 6
        self.volume_multiplier = 1.5
        self.take_profit_pct = 0.016
        self.stop_loss_pct = 0.009

        # Risk management
        self.max_position_size_pct = 0.10  # Max 10% of account per trade
        self.max_daily_drawdown_pct = 0.05  # Stop trading if daily DD > 5%
        self.daily_pnl = 0
        self.daily_start_equity = None

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None

        # Data storage
        self.price_data = pd.DataFrame()
        self.fib_levels_data = {}

        # Setup logging
        self.setup_logging()

        logger.info(f"🎯 GLD Fibonacci Momentum Bot initialized")
        logger.info(f"   Symbol: {self.symbol}")
        logger.info(f"   Parameters: fib_levels={self.fib_levels}, momentum_period={self.momentum_period}")
        logger.info(f"   Risk: max_pos={self.max_position_size_pct:.1%}, max_dd={self.max_daily_drawdown_pct:.1%}")

    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f'gld_fibonacci_momentum_{datetime.now().strftime("%Y%m%d")}.log'

        logger.remove()  # Remove default handler
        logger.add(log_file, rotation="1 day", retention="7 days", level="INFO")
        logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>")

    def get_account_info(self):
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'cash': float(account.cash)
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None

    def get_historical_data(self, limit: int = 200) -> pd.DataFrame:
        """Fetch historical data from Alpaca"""
        try:
            bars = self.api.get_bars(
                self.symbol,
                self.timeframe,
                limit=limit
            )

            data = [{
                'timestamp': bar.t,
                'open': float(bar.o),
                'high': float(bar.h),
                'low': float(bar.l),
                'close': float(bar.c),
                'volume': float(bar.v)
            } for bar in bars]

            df = pd.DataFrame(data).set_index('timestamp')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()

            logger.info(f"Fetched {len(df)} bars of {self.symbol} data")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return pd.DataFrame()

    def calculate_fib_levels(self, data):
        """Calculate Fibonacci retracement levels"""
        if len(data) < 50:
            return {}

        # Use recent high/low for fib levels
        recent_high = data['High'].rolling(50).max().iloc[-1]
        recent_low = data['Low'].rolling(50).min().iloc[-1]

        fib_levels = {}
        for level in self.fib_levels:
            fib_levels[level] = recent_low + (recent_high - recent_low) * level

        return fib_levels

    def check_momentum(self, data):
        """Calculate momentum"""
        if len(data) < self.momentum_period:
            return 0

        recent_prices = data['Close'].tail(self.momentum_period)
        momentum = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
        return momentum

    def check_volume_confirmation(self, data):
        """Check volume confirmation"""
        if len(data) < 20:
            return False

        avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
        current_volume = data['Volume'].iloc[-1]
        return current_volume > avg_volume * self.volume_multiplier

    def should_enter_long(self, data, fib_levels, momentum):
        """Check if we should enter long position"""
        current_price = data['Close'].iloc[-1]

        # Must have bullish momentum
        if momentum <= 0.002:
            return False

        # Check if price is near a Fibonacci level (below it)
        for level, fib_price in fib_levels.items():
            if abs(current_price - fib_price) / current_price < 0.003 and current_price < fib_price:
                return True

        return False

    def should_enter_short(self, data, fib_levels, momentum):
        """Check if we should enter short position"""
        current_price = data['Close'].iloc[-1]

        # Must have bearish momentum
        if momentum >= -0.002:
            return False

        # Check if price is near a Fibonacci level (above it)
        for level, fib_price in fib_levels.items():
            if abs(current_price - fib_price) / current_price < 0.003 and current_price > fib_price:
                return True

        return False

    def calculate_position_size(self, account_info):
        """Calculate position size based on risk management"""
        equity = account_info['equity']
        max_position_value = equity * self.max_position_size_pct

        current_price = self.price_data['Close'].iloc[-1]
        position_size = max_position_value / current_price

        # Ensure we don't exceed buying power
        max_buying_power_size = account_info['buying_power'] / current_price
        position_size = min(position_size, max_buying_power_size)

        return max(1, int(position_size))  # At least 1 share

    def enter_position(self, side: str, qty: int):
        """Enter a position"""
        try:
            # Submit market order
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )

            self.position = qty if side == 'buy' else -qty
            self.entry_price = self.price_data['Close'].iloc[-1]
            self.entry_time = datetime.now()

            logger.info(f"🎯 ENTERED {side.upper()} position: {qty} {self.symbol} @ ${self.entry_price:.2f}")

            return True

        except Exception as e:
            logger.error(f"Failed to enter {side} position: {e}")
            return False

    def exit_position(self):
        """Exit current position"""
        try:
            side = 'sell' if self.position > 0 else 'buy'
            qty = abs(self.position)

            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )

            exit_price = self.price_data['Close'].iloc[-1]
            pnl = (exit_price - self.entry_price) if self.position > 0 else (self.entry_price - exit_price)
            self.daily_pnl += pnl * abs(self.position)

            logger.info(f"💰 EXITED position: {qty} {self.symbol} @ ${exit_price:.2f}")
            logger.info(f"   PnL: ${pnl * abs(self.position):.2f} | Daily PnL: ${self.daily_pnl:.2f}")

            self.position = 0
            self.entry_price = 0
            self.entry_time = None

            return True

        except Exception as e:
            logger.error(f"Failed to exit position: {e}")
            return False

    def check_exit_conditions(self, data):
        """Check if we should exit current position"""
        if self.position == 0:
            return False

        current_price = data['Close'].iloc[-1]

        if self.position > 0:  # Long position
            # Take profit or stop loss
            take_profit_price = self.entry_price * (1 + self.take_profit_pct)
            stop_loss_price = self.entry_price * (1 - self.stop_loss_pct)

            if current_price >= take_profit_price:
                logger.info(f"🎯 TAKE PROFIT triggered: ${current_price:.2f} >= ${take_profit_price:.2f}")
                return True
            elif current_price <= stop_loss_price:
                logger.info(f"🛑 STOP LOSS triggered: ${current_price:.2f} <= ${stop_loss_price:.2f}")
                return True

        else:  # Short position
            # Take profit or stop loss
            take_profit_price = self.entry_price * (1 - self.take_profit_pct)
            stop_loss_price = self.entry_price * (1 + self.stop_loss_pct)

            if current_price <= take_profit_price:
                logger.info(f"🎯 TAKE PROFIT triggered: ${current_price:.2f} <= ${take_profit_price:.2f}")
                return True
            elif current_price >= stop_loss_price:
                logger.info(f"🛑 STOP LOSS triggered: ${current_price:.2f} >= ${stop_loss_price:.2f}")
                return True

        return False

    def check_daily_drawdown_limit(self, account_info):
        """Check if we've hit the daily drawdown limit"""
        if self.daily_start_equity is None:
            self.daily_start_equity = account_info['equity']
            return False

        current_equity = account_info['equity']
        daily_drawdown = (self.daily_start_equity - current_equity) / self.daily_start_equity

        if daily_drawdown > self.max_daily_drawdown_pct:
            logger.warning(f"🚨 DAILY DRAWDOWN LIMIT HIT: {daily_drawdown:.1%} > {self.max_daily_drawdown_pct:.1%}")
            logger.warning("   Stopping trading for today")
            return True

        return False

    def run_trading_cycle(self):
        """Main trading cycle"""
        try:
            # Get latest data
            self.price_data = self.get_historical_data(limit=200)
            if self.price_data.empty:
                logger.warning("No price data available")
                return

            # Get account info
            account_info = self.get_account_info()
            if not account_info:
                logger.warning("Could not get account info")
                return

            # Check daily drawdown limit
            if self.check_daily_drawdown_limit(account_info):
                return

            # Calculate indicators
            fib_levels = self.calculate_fib_levels(self.price_data)
            momentum = self.check_momentum(self.price_data)
            volume_ok = self.check_volume_confirmation(self.price_data)

            current_price = self.price_data['Close'].iloc[-1]

            logger.info(f"📊 {self.symbol}: ${current_price:.2f} | Momentum: {momentum:.4f} | Volume OK: {volume_ok}")

            # Check exit conditions first
            if self.position != 0:
                if self.check_exit_conditions(self.price_data):
                    self.exit_position()

            # Check entry conditions if no position
            elif volume_ok:
                if self.should_enter_long(self.price_data, fib_levels, momentum):
                    qty = self.calculate_position_size(account_info)
                    logger.info(f"🚀 LONG SIGNAL: Near Fib level with bullish momentum")
                    self.enter_position('buy', qty)

                elif self.should_enter_short(self.price_data, fib_levels, momentum):
                    qty = self.calculate_position_size(account_info)
                    logger.info(f"🚀 SHORT SIGNAL: Near Fib level with bearish momentum")
                    self.enter_position('sell', qty)

            # Log position status
            if self.position != 0:
                pnl = (current_price - self.entry_price) if self.position > 0 else (self.entry_price - current_price)
                logger.info(f"📈 Position: {'LONG' if self.position > 0 else 'SHORT'} {abs(self.position)} | PnL: ${pnl * abs(self.position):.2f}")
            else:
                logger.info("📈 No position")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    def run(self):
        """Main bot loop"""
        logger.info("🚀 Starting GLD Fibonacci Momentum Bot")
        logger.info("Strategy: Fibonacci retracement levels with momentum confirmation")
        logger.info("Performance (backtest): 57.43% return, 64% win rate, 136 trades")
        logger.info("=" * 60)

        # Test connection
        try:
            account = self.api.get_account()
            logger.info(f"✅ Connected to Alpaca | Equity: ${float(account.equity):.2f}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Alpaca: {e}")
            return

        # Main loop - run every 5 minutes during market hours
        while True:
            try:
                # Check if market is open (simplified - GLD trades nearly 24/7)
                now = datetime.now()
                if now.weekday() < 5:  # Monday to Friday
                    self.run_trading_cycle()
                else:
                    logger.info("📅 Market closed (weekend)")

                # Sleep for 5 minutes
                logger.info("⏰ Sleeping for 5 minutes...")
                time.sleep(300)

            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

        # Close any remaining position on shutdown
        if self.position != 0:
            logger.info("🔄 Closing remaining position on shutdown")
            self.exit_position()


if __name__ == "__main__":
    bot = GLDFibonacciMomentumBot()
    bot.run()
