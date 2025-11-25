#!/usr/bin/env python3
"""
MSFT 5m RSI Winner Bot - WINNER STRATEGY
Return: 4.00%, Win Rate: 53.7%, Trades: 54, Max DD: 4.50%

RSI-based scalping strategy that was a validated winner.
Uses default RSI parameters with volume confirmation.
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
        logging.FileHandler('logs/msft_rsi_winner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MSFT_RSI_WINNER')

class MSFTRSIWinnerBot:
    """
    RSI Winner Bot for MSFT
    Optimized 5-minute timeframe with winner parameters
    """

    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "msft_5m_winner"

        # Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        # Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Trading parameters (WINNER PARAMETERS)
        self.symbol = 'MSFT'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.strategy_type = 'rsi_scalping'

        # Winner RSI parameters (default settings that produced 4.00% return)
        self.rsi_period = 14  # Default RSI period
        self.rsi_oversold = 30  # Default oversold level
        self.rsi_overbought = 70  # Default overbought level

        # Bollinger Bands for filtering
        self.bb_period = 20
        self.bb_std = 2.0

        # Risk management
        self.stop_loss_pct = 0.005  # 0.5%
        self.take_profit_pct = 0.01  # 1.0%
        self.max_hold_time = 12  # bars (1 hour)
        self.max_daily_drawdown = 0.045  # 4.5% (matches winner DD)

        # Volume requirements (winner settings)
        self.min_volume_ratio = 1.2

        # Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.daily_pnl = 0
        self.daily_start_pnl = 0

        # Signal tracking
        self.last_signal_time = None

        logger.info("🚀 MSFT RSI Winner Bot initialized")
        logger.info(f"Strategy: {self.strategy_type}")
        logger.info(f"Symbol: {self.symbol}, Timeframe: 5m")
        logger.info(f"Winner Parameters: RSI({self.rsi_period}, {self.rsi_oversold}, {self.rsi_overbought})")
        logger.info(f"Expected Performance: 4.00% return, 53.7% win rate, 4.50% max DD")

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std: float = 2.0):
        """Calculate Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std_dev = prices.rolling(period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return upper, sma, lower

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

            # Add technical indicators (winner parameters)
            bars['rsi'] = self.calculate_rsi(bars['Close'], self.rsi_period)
            bars['bb_upper'], bars['bb_middle'], bars['bb_lower'] = self.calculate_bollinger_bands(
                bars['Close'], self.bb_period, self.bb_std
            )
            bars['volume_sma'] = bars['Volume'].rolling(20).mean()
            bars['volume_ratio'] = bars['Volume'] / bars['volume_sma']

            logger.info(f"Fetched {len(bars)} bars of historical data")
            return bars

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    def generate_signal(self, df: pd.DataFrame) -> int:
        """Generate trading signal using winner RSI logic"""
        if len(df) < 50:
            return 0

        current_time = df.index[-1]

        # Avoid overtrading - minimum 10 minutes between signals
        if self.last_signal_time and (current_time - self.last_signal_time).total_seconds() < 600:
            return 0

        # Get current values
        current_close = df['Close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        current_volume_ratio = df['volume_ratio'].iloc[-1]
        bb_upper = df['bb_upper'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]

        # Volume confirmation required (winner setting)
        if current_volume_ratio < self.min_volume_ratio:
            return 0

        # RSI signals with Bollinger Band filtering (WINNER LOGIC)
        signal = 0

        # LONG SIGNAL: RSI oversold + near lower BB (winner parameters)
        if (current_rsi < self.rsi_oversold and  # RSI < 30 (oversold)
            current_close < bb_lower * 1.01):  # Within 1% of lower BB
            signal = 1

        # SHORT SIGNAL: RSI overbought + near upper BB (winner parameters)
        elif (current_rsi > self.rsi_overbought and  # RSI > 70 (overbought)
              current_close > bb_upper * 0.99):  # Within 1% of upper BB
            signal = -1

        if signal != 0:
            self.last_signal_time = current_time
            direction = "LONG (RSI OVERSOLD)" if signal == 1 else "SHORT (RSI OVERBOUGHT)"
            logger.info(f"Winner RSI Signal: {direction} at {current_time}")
            logger.info(f"RSI: {current_rsi:.1f}, Close: ${current_close:.2f}, Volume Ratio: {current_volume_ratio:.2f}")

        return signal

    def execute_trade(self, signal: int, quantity: float) -> bool:
        """Execute trade on Alpaca"""
        try:
            side = 'buy' if signal == 1 else 'sell'

            # Calculate stop loss and take profit
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

    def run(self):
        """Main trading loop"""
        logger.info("Starting MSFT RSI Winner Bot...")

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
    bot = MSFTRSIWinnerBot()
    bot.run()
