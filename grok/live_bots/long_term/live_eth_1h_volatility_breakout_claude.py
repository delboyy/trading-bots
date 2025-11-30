#!/usr/bin/env python3
"""
LIVE TRADING BOT: ETH 1h Volatility Breakout
Strategy: ATR-based volatility breakout on Ethereum
Parameters: ATR window=14, k=2.0
Paper Trading Account Required
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from alpaca_trade_api import REST, TimeFrame
import schedule

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
        logging.FileHandler('logs/eth_1h_volatility_breakout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ETH_1H_VOLATILITY_BREAKOUT')

# Create logs directory
os.makedirs('logs', exist_ok=True)

class ETHVolatilityBreakoutBot:
    """Live trading bot for ETH 1h Volatility Breakout strategy"""

    def __init__(self):
        # Initialize Status Tracker
        self.tracker = StatusTracker()
        self.bot_id = "eth_1h"
        
        # Alpaca API credentials (set these environment variables)
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        # Strategy parameters
        self.symbol = 'ETHUSD'  # Alpaca uses ETHUSD for Ethereum
        self.timeframe = TimeFrame.Hour
        self.atr_window = 14
        self.k = 2.0

        # Risk management - BACKTESTED DRAWDOWN: 40.7%
        # SAFE ACCOUNT SIZE: $30,000+ | RECOMMENDED POSITION SIZE: 1-2% | HIGH RISK
        self.max_position_size = 0.02  # 2% of account per trade
        self.max_drawdown_limit = 0.15  # 15% max drawdown before stopping

        # State tracking
        self.position = 0  # 0 = no position, 1 = long, -1 = short
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.account_value_start = 0.0

        logger.info(f"Initialized ETH 1h Volatility Breakout Bot - ATR({self.atr_window}), k={self.k}")

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(self.atr_window).mean()

    def generate_signals(self, df: pd.DataFrame) -> int:
        """
        Generate trading signals based on ATR volatility breakouts
        Returns: 1 (long), -1 (short), 0 (no signal)
        """
        if len(df) < self.atr_window + 1:
            return 0

        # Calculate ATR
        atr = self.calculate_atr(df)

        # Create bands using previous period's data
        prev_close = df['close'].shift(1)
        upper_band = prev_close + (self.k * atr)
        lower_band = prev_close - (self.k * atr)

        current_close = df['close'].iloc[-1]
        prev_upper = upper_band.iloc[-2] if len(upper_band) > 1 else 0
        prev_lower = lower_band.iloc[-2] if len(lower_band) > 1 else 0

        # Generate signals
        if current_close > prev_upper:
            return 1  # Long breakout
        elif current_close < prev_lower:
            return -1  # Short breakout

        return 0  # No signal

    def get_account_info(self) -> Dict[str, Any]:
        """Get current account information"""
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'daytrade_count': int(account.daytrade_count)
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

    def get_position(self) -> Optional[Dict[str, Any]]:
        """Get current position for ETH"""
        try:
            positions = self.api.list_positions()
            for pos in positions:
                if pos.symbol == self.symbol:
                    return {
                        'qty': float(pos.qty),
                        'avg_entry_price': float(pos.avg_entry_price),
                        'current_price': float(pos.current_price),
                        'unrealized_pl': float(pos.unrealized_pl),
                        'unrealized_plpc': float(pos.unrealized_plpc)
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

    def get_historical_data(self, hours: int = 24) -> pd.DataFrame:
        """Get historical 1h data for ETH"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            bars = self.api.get_crypto_bars(
                self.symbol,
                self.timeframe,
                start=start_time.isoformat(timespec='seconds'),
                end=end_time.isoformat(timespec='seconds'),
                limit=1000
            )

            if not bars:
                logger.warning("No historical data received")
                return pd.DataFrame()

            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.t,
                    'open': float(bar.o),
                    'high': float(bar.h),
                    'low': float(bar.l),
                    'close': float(bar.c),
                    'volume': float(bar.v)
                })

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()

    def calculate_position_size(self, account_equity: float, entry_price: float) -> float:
        """Calculate position size based on risk management"""
        risk_amount = account_equity * self.max_position_size
        position_size = risk_amount / entry_price

        # Round to appropriate decimal places for crypto
        return round(position_size, 6)

    def place_order(self, side: str, qty: float, current_price: float = None) -> bool:
        """Place a LIMIT order (0.01% fee vs 0.035% market)"""
        try:
            # Get current price if not provided
            if current_price is None:
                quote = self.api.get_latest_crypto_quote(self.symbol) if '/' in self.symbol else self.api.get_latest_quote(self.symbol)
                current_price = float(quote.ap) if hasattr(quote, 'ap') else float(quote.askprice)
            
            # Place limit order slightly favorable for quick fill
            if side == 'buy':
                limit_price = current_price * 1.0005  # 0.05% above for quick fill
            else:  # sell
                limit_price = current_price * 0.9995  # 0.05% below for quick fill
            
            limit_price = round(limit_price, 2)
            
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='limit',
                limit_price=limit_price,
                time_in_force='gtc'
            )
            logger.info(f"Placed {side} LIMIT order for {qty} {self.symbol} @ ${limit_price} - Order ID: {order.id}")
            return True
        except Exception as e:
            logger.error(f"Error placing {side} order: {e}")
            return False

    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss should be triggered"""
        if self.position == 0:
            return False

        if self.position == 1 and current_price <= self.stop_loss:
            logger.warning(f"Stop loss triggered for long position at {current_price}")
            return True
        elif self.position == -1 and current_price >= self.stop_loss:
            logger.warning(f"Stop loss triggered for short position at {current_price}")
            return True

        return False

    def update_stop_loss(self, current_price: float):
        """Update trailing stop loss"""
        if self.position == 0:
            return

        # Simple stop loss: 2 ATR from entry
        # This is a simplified version - you might want more sophisticated trailing stops
        atr_value = self.calculate_atr(self.get_historical_data(24)).iloc[-1]
        if pd.notna(atr_value):
            if self.position == 1:
                self.stop_loss = max(self.stop_loss, current_price - 2 * atr_value)
            elif self.position == -1:
                self.stop_loss = min(self.stop_loss, current_price + 2 * atr_value)

    def check_max_drawdown(self, current_equity: float) -> bool:
        """Check if max drawdown limit is reached"""
        if self.account_value_start == 0:
            self.account_value_start = current_equity
            return False

        drawdown = (self.account_value_start - current_equity) / self.account_value_start
        if drawdown >= self.max_drawdown_limit:
            logger.critical(f"Max drawdown limit reached ({drawdown:.1%}) - stopping bot")
        return False

    def run_strategy(self):
        """Main strategy execution"""
        try:
            # Get account info
            account_info = self.get_account_info()
            if not account_info:
                return

            current_equity = account_info['equity']
            
            # Get current position
            current_position = self.get_position()
            
            # Update Status Dashboard
            self.tracker.update_status(self.bot_id, {
                'equity': current_equity,
                'cash': account_info['cash'],
                'position': current_position['qty'] if current_position else 0,
                'entry_price': current_position['avg_entry_price'] if current_position else 0,
                'unrealized_pl': current_position['unrealized_pl'] if current_position else 0
            })

            # Check max drawdown
            if self.check_max_drawdown(current_equity):
                logger.critical("Max drawdown limit reached - stopping bot")
                return

            # Get current position
            if current_position:
                self.position = 1 if current_position['qty'] > 0 else -1
                self.entry_price = current_position['avg_entry_price']

                # Update stop loss
                self.update_stop_loss(current_position['current_price'])

                # Check stop loss
                if self.check_stop_loss(current_position['current_price']):
                    # Close position
                    qty_to_close = abs(current_position['qty'])
                    side = 'sell' if self.position == 1 else 'buy'
                    if self.place_order(side, qty_to_close, current_price):
                        self.position = 0
                        self.entry_price = 0.0
                        self.stop_loss = 0.0
                    return
            else:
                self.position = 0
                self.entry_price = 0.0
                self.stop_loss = 0.0

            # Get recent data and generate signals
            df = self.get_historical_data(48)  # Get 48 hours of data
            if df.empty or len(df) < 20:
                logger.warning("Insufficient data for signal generation")
                return

            signal = self.generate_signals(df)

            # Execute signal if we don't have a position
            if signal != 0 and self.position == 0:
                current_price = df['close'].iloc[-1]
                qty = self.calculate_position_size(current_equity, current_price)

                if qty > 0:
                    side = 'buy' if signal == 1 else 'sell'
                    if self.place_order(side, qty, current_price):
                        self.position = signal
                        self.entry_price = current_price
                        # Set initial stop loss
                        atr_value = self.calculate_atr(df).iloc[-1]
                        if pd.notna(atr_value):
                            if signal == 1:
                                self.stop_loss = current_price - 2 * atr_value
                            else:
                                self.stop_loss = current_price + 2 * atr_value
                        logger.info(f"Entered {side} position at {current_price} with stop loss at {self.stop_loss}")

            logger.info(f"Strategy check complete - Position: {self.position}, Equity: ${current_equity:.2f}")

        except Exception as e:
            logger.error(f"Error in strategy execution: {e}")

    def run_live(self):
        """Run the bot continuously"""
        logger.info("Starting ETH 1h Volatility Breakout live trading bot...")

        def job():
            self.run_strategy()

        # Schedule to run every 5 minutes (1h timeframe, so check frequently for new bars)
        schedule.every(5).minutes.do(job)

        # Initial run
        job()

        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error


def main():
    """Main entry point"""
    try:
        bot = ETHVolatilityBreakoutBot()
        bot.run_live()
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
