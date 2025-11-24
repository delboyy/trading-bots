#!/usr/bin/env python3
"""
LIVE TRADING BOT: NQ 4h Volatility Breakout
Strategy: ATR-based volatility breakout on Nasdaq Futures (4h timeframe)
Parameters: ATR window=14, k=1.5
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
from grok.utils.status_tracker import StatusTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nq_4h_volatility_breakout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('NQ_4H_VOLATILITY_BREAKOUT')

os.makedirs('logs', exist_ok=True)

class NQ4HVolatilityBreakoutBot:
    """Live trading bot for NQ 4h Volatility Breakout strategy"""

    def __init__(self):
        # Initialize Status Tracker
        self.tracker = StatusTracker()
        self.bot_id = "nq_4h"
        
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

        if not self.api_key or not self.api_secret:
            raise ValueError("Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables")

        self.api = REST(self.api_key, self.api_secret, self.base_url)

        self.symbol = 'NQ'  # Nasdaq futures
        self.timeframe = TimeFrame.Hour * 4
        self.atr_window = 14
        self.k = 1.5

        self.max_position_size = 0.02
        self.max_drawdown_limit = 0.18

        self.position = 0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.account_value_start = 0.0

        logger.info(f"Initialized NQ 4h Volatility Breakout Bot - ATR({self.atr_window}), k={self.k}")

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(self.atr_window).mean()

    def generate_signals(self, df: pd.DataFrame) -> int:
        if len(df) < self.atr_window + 1:
            return 0

        atr = self.calculate_atr(df)
        prev_close = df['close'].shift(1)
        upper_band = prev_close + (self.k * atr)
        lower_band = prev_close - (self.k * atr)

        current_close = df['close'].iloc[-1]
        prev_upper = upper_band.iloc[-2] if len(upper_band) > 1 else 0
        prev_lower = lower_band.iloc[-2] if len(lower_band) > 1 else 0

        if current_close > prev_upper:
            return 1
        elif current_close < prev_lower:
            return -1
        return 0

    def get_account_info(self) -> Dict[str, Any]:
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

    def get_historical_data(self, hours: int = 192) -> pd.DataFrame:
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            bars = self.api.get_bars(
                self.symbol,
                self.timeframe,
                start=start_time.isoformat(),
                end=end_time.isoformat(),
                limit=1000
            )

            if not bars:
                return pd.DataFrame()

            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.timestamp,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': float(bar.volume)
                })

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()

    def calculate_position_size(self, account_equity: float, entry_price: float) -> int:
        risk_amount = account_equity * self.max_position_size
        position_size = risk_amount / entry_price
        return int(position_size)

    def place_order(self, side: str, qty: int) -> bool:
        try:
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            logger.info(f"Placed {side} order for {qty} {self.symbol} - Order ID: {order.id}")
            return True
        except Exception as e:
            logger.error(f"Error placing {side} order: {e}")
            return False

    def check_stop_loss(self, current_price: float) -> bool:
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
        if self.position == 0:
            return

        atr_value = self.calculate_atr(self.get_historical_data(192)).iloc[-1]
        if pd.notna(atr_value):
            if self.position == 1:
                self.stop_loss = max(self.stop_loss, current_price - 2 * atr_value)
            elif self.position == -1:
                self.stop_loss = min(self.stop_loss, current_price + 2 * atr_value)

    def check_max_drawdown(self, current_equity: float) -> bool:
        if self.account_value_start == 0:
            self.account_value_start = current_equity
            return False

        drawdown = (self.account_value_start - current_equity) / self.account_value_start
        if drawdown >= self.max_drawdown_limit:
            logger.critical(f"Max drawdown limit ({self.max_drawdown_limit:.1%}) reached. Current drawdown: {drawdown:.1%}")
            return True
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

            if current_position:
                self.position = 1 if current_position['qty'] > 0 else -1
                self.entry_price = current_position['avg_entry_price']
                self.update_stop_loss(current_position['current_price'])

                if self.check_stop_loss(current_position['current_price']):
                    qty_to_close = abs(int(current_position['qty']))
                    side = 'sell' if self.position == 1 else 'buy'
                    if self.place_order(side, qty_to_close):
                        self.position = 0
                        self.entry_price = 0.0
                        self.stop_loss = 0.0
                    return
            else:
                self.position = 0
                self.entry_price = 0.0
                self.stop_loss = 0.0

            df = self.get_historical_data(240)
            if df.empty or len(df) < 20:
                return

            signal = self.generate_signals(df)

            if signal != 0 and self.position == 0:
                current_price = df['close'].iloc[-1]
                qty = self.calculate_position_size(current_equity, current_price)

                if qty > 0:
                    side = 'buy' if signal == 1 else 'sell'
                    if self.place_order(side, qty):
                        self.position = signal
                        self.entry_price = current_price
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
        logger.info("Starting NQ 4h Volatility Breakout live trading bot...")

        def job():
            self.run_strategy()

        schedule.every(15).minutes.do(job)
        job()

        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(300)


def main():
    try:
        bot = NQ4HVolatilityBreakoutBot()
        bot.run_live()
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
