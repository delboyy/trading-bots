#!/usr/bin/env python3
"""
GOOGL 15m RSI Scalping Live Trading Bot
Based on validated 2-year IBKR performance: 41.30% return, 54.1% win rate
Strategy: RSI-based mean reversion with aggressive parameters
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit
# from shared_utils.data_loader import load_ohlcv_yfinance
# from shared_strategies.scalping_strategy import ScalpingStrategy

from grok.utils.status_tracker import StatusTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/live_googl_15m_rsi_scalping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GOOGLRSIScalpingBot:
    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "googl_15m_rsi"

        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Validate credentials
        if not self.api_key or not self.api_secret:
            raise ValueError("Alpaca API credentials not found in environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters
        self.symbol = 'GOOGL'
        self.timeframe = TimeFrame(15, TimeFrameUnit.Minute)

        # RSI strategy parameters (validated winners)
        self.strategy_params = {
            'rsi_period': 7,        # More sensitive than default 14
            'rsi_oversold': 25,     # More extreme than default 30
            'rsi_overbought': 75,   # More extreme than default 70
        }

        # Risk management
        self.max_position_size_pct = 0.01  # 1% of account equity
        self.stop_loss_pct = 0.005         # 0.5% stop loss
        self.take_profit_pct = 0.015       # 1.5% take profit
        self.max_daily_drawdown = 0.02     # 2% daily drawdown limit

        # Trading state
        self.position = None
        self.daily_pnl = 0.0
        self.daily_start_equity = 0.0
        self.is_running = False

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0

        logger.info(f"Initialized GOOGL RSI Scalping Bot with params: {self.strategy_params}")

    def get_historical_data(self, limit: int = 1000) -> pd.DataFrame:
        """Fetch historical data from Alpaca"""
        try:
            # Get bars from Alpaca
            bars = self.api.get_bars(
                self.symbol,
                self.timeframe,
                limit=limit,
                adjustment='raw'
            ).df

            if bars.empty:
                logger.warning(f"No bars received for {self.symbol}")
                return pd.DataFrame()

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

            logger.info(f"Fetched {len(bars)} bars for {self.symbol}")
            return bars

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    def calculate_position_size(self, entry_price: float) -> float:
        """Calculate position size based on risk management"""
        try:
            # Get account equity
            account = self.api.get_account()
            equity = float(account.equity)

            # Calculate max position value
            max_position_value = equity * self.max_position_size_pct

            # Calculate quantity based on stop loss
            stop_loss_price = entry_price * (1 - self.stop_loss_pct)
            risk_per_share = entry_price - stop_loss_price
            max_shares = max_position_value / risk_per_share

            # Round down to whole shares
            qty = int(max_shares)

            # Ensure minimum order size
            qty = max(qty, 1)

            logger.info(f"Calculated position size: {qty} shares at ${entry_price:.2f}")
            return qty

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def execute_trade(self, side: str, qty: float, entry_price: float) -> bool:
        """Execute market order with bracket protection"""
        try:
            stop_price = entry_price * (1 - self.stop_loss_pct) if side == 'buy' else entry_price * (1 + self.stop_loss_pct)
            limit_price = entry_price * (1 + self.take_profit_pct) if side == 'buy' else entry_price * (1 - self.take_profit_pct)

            # Submit bracket order
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                stop_loss={'stop_price': round(stop_price, 2)},
                take_profit={'limit_price': round(limit_price, 2)}
            )

            logger.info(f"Executed {side} order for {qty} {self.symbol} at ${entry_price:.2f}")
            logger.info(f"Stop Loss: ${stop_price:.2f}, Take Profit: ${limit_price:.2f}")

            # Update position tracking
            self.position = {
                'side': side,
                'qty': qty,
                'entry_price': entry_price,
                'stop_loss': stop_price,
                'take_profit': limit_price,
                'timestamp': datetime.now()
            }

            return True

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False

    def check_position_status(self):
        """Check if current position has been closed"""
        try:
            positions = self.api.list_positions()
            current_position = None

            for pos in positions:
                if pos.symbol == self.symbol:
                    current_position = pos
                    break

            if current_position:
                # Position still open
                return False
            else:
                # Position closed - check if it was a win/loss
                if self.position:
                    logger.info(f"Position closed for {self.symbol}")

                    # Reset position
                    self.position = None

                return True

        except Exception as e:
            logger.error(f"Error checking position status: {e}")
            return False

    def generate_signal(self, data: pd.DataFrame) -> str:
        """Generate trading signal using RSI strategy"""
        try:
            if len(data) < 50:  # Need enough data for RSI
                return 'hold'

            # Calculate RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.strategy_params['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.strategy_params['rsi_period']).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]

            # RSI Strategy Logic
            rsi_oversold = self.strategy_params['rsi_oversold']
            rsi_overbought = self.strategy_params['rsi_overbought']

            # Buy signal: RSI crosses above oversold level
            if prev_rsi <= rsi_oversold and current_rsi > rsi_oversold:
                return 'buy'

            # Sell signal: RSI crosses below overbought level
            elif prev_rsi >= rsi_overbought and current_rsi < rsi_overbought:
                return 'sell'

            return 'hold'

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return 'hold'

    def check_daily_drawdown(self) -> bool:
        """Check if daily drawdown limit exceeded"""
        try:
            account = self.api.get_account()
            current_equity = float(account.equity)

            if self.daily_start_equity == 0:
                self.daily_start_equity = current_equity

            daily_drawdown = (self.daily_start_equity - current_equity) / self.daily_start_equity

            if daily_drawdown >= self.max_daily_drawdown:
                logger.warning(f"Daily drawdown limit reached: {daily_drawdown:.2%}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking daily drawdown: {e}")
            return False

    def run_trading_loop(self):
        """Main trading loop"""
        logger.info("Starting GOOGL RSI Scalping trading loop")
        self.is_running = True

        while self.is_running:
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

                # Check if we should stop due to drawdown
                if self.check_daily_drawdown():
                    logger.warning("Daily drawdown limit reached - stopping trading")
                    break

                # Check position status
                position_closed = self.check_position_status()

                # Only look for new signals if no position is open
                if self.position is None:
                    # Get latest data
                    data = self.get_historical_data(limit=200)

                    if not data.empty:
                        # Generate signal
                        signal = self.generate_signal(data)

                        if signal in ['buy', 'sell']:
                            current_price = data['Close'].iloc[-1]
                            qty = self.calculate_position_size(current_price)

                            if qty > 0:
                                logger.info(f"Signal generated: {signal.upper()} at ${current_price:.2f}")
                                success = self.execute_trade(signal, qty, current_price)

                                if success:
                                    self.total_trades += 1
                            else:
                                logger.warning("Insufficient position size calculated")

                # Wait before next iteration (15-minute intervals)
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                self.tracker.update_status(self.bot_id, {'error': f"CRASH: {str(e)}"})
                time.sleep(30)

    def stop_trading(self):
        """Gracefully stop trading"""
        logger.info("Stopping GOOGL RSI Scalping bot")
        self.is_running = False

        # Close any open positions
        try:
            positions = self.api.list_positions()
            for pos in positions:
                if pos.symbol == self.symbol:
                    logger.info(f"Closing position: {pos.qty} {self.symbol}")
                    self.api.close_position(self.symbol)
        except Exception as e:
            logger.error(f"Error closing positions: {e}")

    def print_performance_summary(self):
        """Print performance summary"""
        try:
            account = self.api.get_account()
            current_equity = float(account.equity)

            logger.info("=" * 60)
            logger.info("GOOGL RSI SCALPING BOT PERFORMANCE SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Symbol: {self.symbol}")
            logger.info(f"Strategy: RSI Scalping (Period: {self.strategy_params['rsi_period']})")
            logger.info(f"Timeframe: 15 minutes")
            logger.info(f"Total Trades: {self.total_trades}")
            logger.info(f"Current Equity: ${current_equity:.2f}")
            logger.info(f"Daily P&L: ${self.daily_pnl:.2f}")
            logger.info(f"Daily P&L: ${self.daily_pnl:.2f}")

        except Exception as e:
            logger.error(f"Error printing performance summary: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    if 'bot' in globals():
        bot.stop_trading()
    sys.exit(0)


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create and run bot
        bot = GOOGLRSIScalpingBot()
        bot.print_performance_summary()

        # Start trading
        bot.run_trading_loop()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'bot' in globals():
            bot.print_performance_summary()
            bot.stop_trading()
