#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE STRATEGY VALIDATION - MASTER DOCUMENTATION STRATEGIES

This script validates ALL strategies from the STRATEGY_MASTER_DOCUMENTATION.md
over 2-year periods (2023-2025) to ensure they perform as documented.

Strategies to validate:
1. Time-Based Scalping Strategies (TSLA, QQQ)
2. RSI Scalping Strategies (GOOGL, MSFT, BAC)
3. Volume Breakout Strategies (AMD, MSFT)
4. Candlestick Scalping Strategies (GLD, DIA, MSFT, SPY)
5. Fibonacci Momentum Strategies (GLD)
6. Session Momentum Strategies (GLD)
7. ATR Range Scalping Strategies (GLD)
8. Crypto Strategies (BTC VWAP, BTC Combo, BTC Triple MA, ETH)

Data Sources:
- IBKR data for stocks (local files)
- Binance data for crypto (processed parquet files)

Validation Period: 2 years (2023-2025 where available)
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared_utils.indicators import *
from shared_utils.data_loader import *
from shared_utils.logger import setup_logger

# Setup logging
logger = setup_logger("comprehensive_validation")

# ===============================
# DATA LOADING FUNCTIONS
# ===============================

def load_stock_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load stock data from local IBKR CSV files"""
    file_path = f"/Users/a1/Projects/Trading/trading-bots/data/{symbol}_{timeframe}_2y.csv"

    if not os.path.exists(file_path):
        logger.warning(f"Data file not found: {file_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df.set_index('date', inplace=True)

        # Filter to 2023-2025 data
        df = df[df.index >= '2023-01-01']
        df = df[df.index <= '2025-12-31']

        # Rename columns to standard format
        df.columns = [col.capitalize() for col in df.columns]

        logger.info(f"Loaded {len(df)} bars for {symbol} {timeframe}")
        return df

    except Exception as e:
        logger.error(f"Error loading {symbol} {timeframe}: {e}")
        return pd.DataFrame()

def load_crypto_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load crypto data from processed parquet files"""
    base_path = f"/Users/a1/Projects/Trading/trading-bots/data/processed/binance_{symbol}_{timeframe}_combined.parquet"

    if not os.path.exists(base_path):
        logger.warning(f"Crypto data file not found: {base_path}")
        return pd.DataFrame()

    try:
        df = pd.read_parquet(base_path)

        # Filter to 2023-2025 data
        start_date = pd.Timestamp('2023-01-01').tz_localize(df.index.tz)
        end_date = pd.Timestamp('2025-12-31').tz_localize(df.index.tz)
        df = df[df.index >= start_date]
        df = df[df.index <= end_date]

        # Ensure proper column names
        rename_dict = {}
        for col in df.columns:
            if col.lower() == 'open':
                rename_dict[col] = 'Open'
            elif col.lower() == 'high':
                rename_dict[col] = 'High'
            elif col.lower() == 'low':
                rename_dict[col] = 'Low'
            elif col.lower() == 'close':
                rename_dict[col] = 'Close'
            elif col.lower() == 'volume':
                rename_dict[col] = 'Volume'

        if rename_dict:
            df = df.rename(columns=rename_dict)

        logger.info(f"Loaded {len(df)} bars for {symbol} {timeframe}")
        return df

    except Exception as e:
        logger.error(f"Error loading crypto {symbol} {timeframe}: {e}")
        return pd.DataFrame()

# ===============================
# STRATEGY CLASSES
# ===============================

class BaseStrategy:
    """Base class for all trading strategies"""

    def __init__(self, name: str, symbol: str, timeframe: str):
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.trades = []
        self.position = 0
        self.entry_price = 0
        self.entry_time = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate required indicators for the strategy"""
        return df

    def check_entry_conditions(self, df: pd.DataFrame, i: int) -> Optional[str]:
        """Check if entry conditions are met. Return 'buy' or 'sell' or None"""
        return None

    def check_exit_conditions(self, df: pd.DataFrame, i: int) -> bool:
        """Check if exit conditions are met"""
        return False

    def run_backtest(self, df: pd.DataFrame) -> Dict:
        """Run backtest on historical data"""
        if df.empty:
            return {'error': 'No data available'}

        df = self.calculate_indicators(df)
        df = df.dropna()  # Remove rows with NaN indicators

        for i in range(len(df)):
            current_price = df['Close'].iloc[i]
            current_time = df.index[i]

            # Check for entry
            if self.position == 0:
                signal = self.check_entry_conditions(df, i)
                if signal == 'buy':
                    self.enter_position(current_price, current_time, 'long')
                elif signal == 'sell':
                    self.enter_position(current_price, current_time, 'short')

            # Check for exit
            elif self.position != 0:
                if self.check_exit_conditions(df, i):
                    self.exit_position(current_price, current_time)

        # Close any remaining position at the end
        if self.position != 0:
            final_price = df['Close'].iloc[-1]
            final_time = df.index[-1]
            self.exit_position(final_price, final_time)

        return self.calculate_performance_metrics()

    def enter_position(self, price: float, timestamp, direction: str):
        """Enter a position"""
        self.position = 1 if direction == 'long' else -1
        self.entry_price = price
        self.entry_time = timestamp

    def exit_position(self, price: float, timestamp):
        """Exit the current position"""
        if self.position == 0:
            return

        pnl = (price - self.entry_price) * self.position
        hold_time = (timestamp - self.entry_time).total_seconds() / 3600  # hours

        self.trades.append({
            'entry_time': self.entry_time,
            'exit_time': timestamp,
            'entry_price': self.entry_price,
            'exit_price': price,
            'pnl': pnl,
            'hold_time': hold_time,
            'direction': 'long' if self.position == 1 else 'short'
        })

        self.position = 0
        self.entry_price = 0
        self.entry_time = None

    def calculate_performance_metrics(self) -> Dict:
        """Calculate performance metrics from trades"""
        if not self.trades:
            return {
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'avg_trade_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': []
            }

        trades_df = pd.DataFrame(self.trades)
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()

        # Basic metrics
        total_return = trades_df['pnl'].sum()
        win_rate = (trades_df['pnl'] > 0).mean()
        total_trades = len(trades_df)
        avg_trade_return = trades_df['pnl'].mean()

        # Max drawdown calculation
        cumulative = trades_df['cumulative_pnl']
        peak = cumulative.expanding().max()
        drawdown = cumulative - peak
        max_drawdown = drawdown.min()

        # Sharpe ratio (assuming daily returns, simplified)
        if len(trades_df) > 1:
            daily_returns = trades_df.set_index('exit_time')['pnl'].resample('D').sum().fillna(0)
            if daily_returns.std() > 0:
                sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(365)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_trade_return': avg_trade_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'trades': self.trades
        }

class TimeBasedScalpingStrategy(BaseStrategy):
    """Time-Based Scalping Strategy from Master Doc"""

    def __init__(self, symbol: str, timeframe: str, momentum_period: int = 7,
                 volume_multiplier: float = 1.2, take_profit_pct: float = 0.015,
                 stop_loss_pct: float = 0.005, max_hold_bars: int = 12):
        super().__init__("Time-Based Scalping", symbol, timeframe)
        self.momentum_period = momentum_period
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_bars = max_hold_bars
        self.bars_held = 0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Add momentum score
        df['momentum_score'] = df['Close'] - df['Close'].shift(self.momentum_period)
        # Add volume average
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        return df

    def check_entry_conditions(self, df: pd.DataFrame, i: int) -> Optional[str]:
        if i < self.momentum_period:
            return None

        # Check if in active trading hours (9:30 AM - 4:00 PM ET)
        current_time = df.index[i].time()
        if not (time(9, 30) <= current_time <= time(16, 0)):
            return None

        momentum_score = df['momentum_score'].iloc[i]
        current_volume = df['Volume'].iloc[i]
        avg_volume = df['avg_volume'].iloc[i]

        # Entry conditions
        momentum_threshold = df['Close'].iloc[i] * 0.002  # 0.2% momentum
        volume_threshold = avg_volume * self.volume_multiplier

        if abs(momentum_score) > momentum_threshold and current_volume > volume_threshold:
            return 'buy' if momentum_score > 0 else 'sell'

        return None

    def check_exit_conditions(self, df: pd.DataFrame, i: int) -> bool:
        if self.position == 0:
            return False

        current_price = df['Close'].iloc[i]
        entry_price = self.entry_price

        # Profit target
        if self.position == 1:  # Long position
            if current_price >= entry_price * (1 + self.take_profit_pct):
                return True
            if current_price <= entry_price * (1 - self.stop_loss_pct):
                return True
        else:  # Short position
            if current_price <= entry_price * (1 - self.take_profit_pct):
                return True
            if current_price >= entry_price * (1 + self.stop_loss_pct):
                return True

        # Max hold time
        self.bars_held += 1
        if self.bars_held >= self.max_hold_bars:
            return True

        return False

    def enter_position(self, price: float, timestamp, direction: str):
        super().enter_position(price, timestamp, direction)
        self.bars_held = 0

class RSIScalpingStrategy(BaseStrategy):
    """RSI Scalping Strategy from Master Doc"""

    def __init__(self, symbol: str, timeframe: str, rsi_period: int = 7,
                 rsi_oversold: int = 25, rsi_overbought: int = 75,
                 volume_multiplier: float = 1.2, take_profit_pct: float = 0.012,
                 stop_loss_pct: float = 0.006, max_hold_bars: int = 8):
        super().__init__("RSI Scalping", symbol, timeframe)
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_bars = max_hold_bars
        self.bars_held = 0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume average
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        return df

    def check_entry_conditions(self, df: pd.DataFrame, i: int) -> Optional[str]:
        if i < 2 or pd.isna(df['rsi'].iloc[i]) or pd.isna(df['rsi'].iloc[i-1]):
            return None

        current_rsi = df['rsi'].iloc[i]
        previous_rsi = df['rsi'].iloc[i-1]
        current_volume = df['Volume'].iloc[i]
        avg_volume = df['avg_volume'].iloc[i]

        if current_volume < avg_volume * self.volume_multiplier:
            return None

        # Bullish signal: RSI crosses above oversold
        if previous_rsi <= self.rsi_oversold and current_rsi > self.rsi_oversold:
            return 'buy'

        # Bearish signal: RSI crosses below overbought
        if previous_rsi >= self.rsi_overbought and current_rsi < self.rsi_overbought:
            return 'sell'

        return None

    def check_exit_conditions(self, df: pd.DataFrame, i: int) -> bool:
        if self.position == 0:
            return False

        current_price = df['Close'].iloc[i]
        entry_price = self.entry_price

        # Profit target
        profit_target = self.take_profit_pct
        stop_loss = self.stop_loss_pct

        if self.position == 1:  # Long position
            if current_price >= entry_price * (1 + profit_target):
                return True
            if current_price <= entry_price * (1 - stop_loss):
                return True
        else:  # Short position
            if current_price <= entry_price * (1 - profit_target):
                return True
            if current_price >= entry_price * (1 + stop_loss):
                return True

        # Max hold time
        self.bars_held += 1
        if self.bars_held >= self.max_hold_bars:
            return True

        return False

    def enter_position(self, price: float, timestamp, direction: str):
        super().enter_position(price, timestamp, direction)
        self.bars_held = 0

class VolumeBreakoutStrategy(BaseStrategy):
    """Volume Breakout Strategy from Master Doc"""

    def __init__(self, symbol: str, timeframe: str, volume_multiplier: float = 1.8,
                 breakout_threshold: float = 0.005, take_profit_pct: float = 0.02,
                 stop_loss_pct: float = 0.01, min_volume_period: int = 20):
        super().__init__("Volume Breakout", symbol, timeframe)
        self.volume_multiplier = volume_multiplier
        self.breakout_threshold = breakout_threshold
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.min_volume_period = min_volume_period

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Calculate average volume
        df['avg_volume'] = df['Volume'].rolling(self.min_volume_period).mean()
        return df

    def check_entry_conditions(self, df: pd.DataFrame, i: int) -> Optional[str]:
        if i < self.min_volume_period:
            return None

        current_price = df['Close'].iloc[i]
        current_volume = df['Volume'].iloc[i]
        avg_volume = df['avg_volume'].iloc[i]

        # Volume spike condition
        volume_spike = current_volume > (avg_volume * self.volume_multiplier)

        if not volume_spike:
            return None

        # Price breakout conditions
        if i >= 10:  # Need some history for breakout detection
            recent_high = df['High'].tail(10).max()
            recent_low = df['Low'].tail(10).min()

            # Bullish breakout
            if current_price > recent_high * (1 + self.breakout_threshold):
                return 'buy'

            # Bearish breakdown
            if current_price < recent_low * (1 - self.breakout_threshold):
                return 'sell'

        return None

    def check_exit_conditions(self, df: pd.DataFrame, i: int) -> bool:
        if self.position == 0:
            return False

        current_price = df['Close'].iloc[i]
        entry_price = self.entry_price

        # Profit target and stop loss
        if self.position == 1:  # Long position
            if current_price >= entry_price * (1 + self.take_profit_pct):
                return True
            if current_price <= entry_price * (1 - self.stop_loss_pct):
                return True
        else:  # Short position
            if current_price <= entry_price * (1 - self.take_profit_pct):
                return True
            if current_price >= entry_price * (1 + self.stop_loss_pct):
                return True

        return False

class CandlestickScalpingStrategy(BaseStrategy):
    """Candlestick Scalping Strategy from Master Doc"""

    def __init__(self, symbol: str, timeframe: str, volume_multiplier: float = 1.4,
                 take_profit_pct: float = 0.015, stop_loss_pct: float = 0.007,
                 max_hold_bars: int = 6):
        super().__init__("Candlestick Scalping", symbol, timeframe)
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_bars = max_hold_bars
        self.bars_held = 0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Volume average for confirmation
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        return df

    def detect_candlestick_patterns(self, df: pd.DataFrame, i: int) -> Optional[str]:
        """Detect basic candlestick patterns"""
        if i < 5:  # Need some history
            return None

        # Current candle
        current = df.iloc[i]
        prev1 = df.iloc[i-1]

        open_price = current['Open']
        high_price = current['High']
        low_price = current['Low']
        close_price = current['Close']

        body_size = abs(close_price - open_price)
        total_range = high_price - low_price

        if total_range == 0:
            return None

        body_ratio = body_size / total_range
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price

        # Volume confirmation
        current_volume = current['Volume']
        avg_volume = df['avg_volume'].iloc[i]
        volume_confirmed = current_volume > avg_volume * self.volume_multiplier

        if not volume_confirmed:
            return None

        # Hammer pattern (small body, long lower wick)
        if (body_ratio < 0.3 and lower_shadow > body_size * 2 and
            upper_shadow < body_size and close_price > open_price):
            return 'hammer'  # Bullish reversal

        # Shooting star (small body, long upper wick)
        if (body_ratio < 0.3 and upper_shadow > body_size * 2 and
            lower_shadow < body_size and close_price < open_price):
            return 'shooting_star'  # Bearish reversal

        # Engulfing patterns
        prev_body_high = max(prev1['Open'], prev1['Close'])
        prev_body_low = min(prev1['Open'], prev1['Close'])

        # Bullish engulfing
        if (close_price > open_price and prev1['Close'] < prev1['Open'] and
            close_price >= prev_body_high and open_price <= prev_body_low):
            return 'bullish_engulfing'

        # Bearish engulfing
        if (close_price < open_price and prev1['Close'] > prev1['Open'] and
            open_price >= prev_body_high and close_price <= prev_body_low):
            return 'bearish_engulfing'

        return None

    def check_entry_conditions(self, df: pd.DataFrame, i: int) -> Optional[str]:
        pattern = self.detect_candlestick_patterns(df, i)

        if pattern == 'hammer':
            return 'buy'
        elif pattern == 'shooting_star':
            return 'sell'
        elif pattern == 'bullish_engulfing':
            return 'buy'
        elif pattern == 'bearish_engulfing':
            return 'sell'

        return None

    def check_exit_conditions(self, df: pd.DataFrame, i: int) -> bool:
        if self.position == 0:
            return False

        current_price = df['Close'].iloc[i]
        entry_price = self.entry_price

        # Profit target and stop loss
        if self.position == 1:  # Long position
            if current_price >= entry_price * (1 + self.take_profit_pct):
                return True
            if current_price <= entry_price * (1 - self.stop_loss_pct):
                return True
        else:  # Short position
            if current_price <= entry_price * (1 - self.take_profit_pct):
                return True
            if current_price >= entry_price * (1 + self.stop_loss_pct):
                return True

        # Max hold time
        self.bars_held += 1
        if self.bars_held >= self.max_hold_bars:
            return True

        return False

    def enter_position(self, price: float, timestamp, direction: str):
        super().enter_position(price, timestamp, direction)
        self.bars_held = 0

class FibonacciMomentumStrategy(BaseStrategy):
    """Fibonacci Momentum Strategy from Master Doc"""

    def __init__(self, symbol: str, timeframe: str, fib_levels: List[float] = [0.236, 0.382, 0.618, 0.786],
                 momentum_period: int = 6, volume_multiplier: float = 1.5,
                 take_profit_pct: float = 0.016, stop_loss_pct: float = 0.009,
                 max_hold_time: int = 12):
        super().__init__("Fibonacci Momentum", symbol, timeframe)
        self.fib_levels = fib_levels
        self.momentum_period = momentum_period
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_time = max_hold_time
        self.bars_held = 0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Calculate Fibonacci retracement levels
        recent_high = df['High'].rolling(50).max()
        recent_low = df['Low'].rolling(50).min()

        for level in self.fib_levels:
            df[f'fib_{level}'] = recent_low + (recent_high - recent_low) * level

        # Momentum
        df['momentum'] = df['Close'] - df['Close'].shift(self.momentum_period)

        # Volume average
        df['avg_volume'] = df['Volume'].rolling(20).mean()

        return df

    def check_entry_conditions(self, df: pd.DataFrame, i: int) -> Optional[str]:
        if i < self.momentum_period:
            return None

        current_price = df['Close'].iloc[i]
        momentum = df['momentum'].iloc[i]
        current_volume = df['Volume'].iloc[i]
        avg_volume = df['avg_volume'].iloc[i]

        # Volume confirmation
        if current_volume < avg_volume * self.volume_multiplier:
            return None

        # Check Fibonacci levels
        for level in self.fib_levels:
            fib_price = df[f'fib_{level}'].iloc[i]
            price_distance = abs(current_price - fib_price) / current_price

            # Near Fibonacci level (within 0.3% tolerance)
            if price_distance < 0.003:
                # Long signal: price below Fib with bullish momentum
                if current_price < fib_price and momentum > 0.002:
                    return 'buy'
                # Short signal: price above Fib with bearish momentum
                elif current_price > fib_price and momentum < -0.002:
                    return 'sell'

        return None

    def check_exit_conditions(self, df: pd.DataFrame, i: int) -> bool:
        if self.position == 0:
            return False

        current_price = df['Close'].iloc[i]
        entry_price = self.entry_price

        # Profit target
        if self.position == 1:  # Long position
            if current_price >= entry_price * (1 + self.take_profit_pct):
                return True
            if current_price <= entry_price * (1 - self.stop_loss_pct):
                return True
        else:  # Short position
            if current_price <= entry_price * (1 - self.take_profit_pct):
                return True
            if current_price >= entry_price * (1 + self.stop_loss_pct):
                return True

        # Max hold time
        self.bars_held += 1
        if self.bars_held >= self.max_hold_time:
            return True

        return False

    def enter_position(self, price: float, timestamp, direction: str):
        super().enter_position(price, timestamp, direction)
        self.bars_held = 0

# ===============================
# MAIN VALIDATION FUNCTION
# ===============================

def validate_all_strategies():
    """Validate all strategies from the master documentation"""

    results = {}

    # ===============================
    # TIME-BASED SCALPING STRATEGIES
    # ===============================

    logger.info("🔍 Validating Time-Based Scalping Strategies...")

    # TSLA Time-Based 15m (MOMENTUM_PERIOD: 7) - BEST PERFORMER
    strategy = TimeBasedScalpingStrategy("TSLA", "15mins", momentum_period=7)
    df = load_stock_data("TSLA", "15mins")
    results['TSLA_TimeBased_15m_Mom7'] = strategy.run_backtest(df)

    # TSLA Time-Based 15m (DEFAULT)
    strategy = TimeBasedScalpingStrategy("TSLA", "15mins", momentum_period=10)
    results['TSLA_TimeBased_15m_Default'] = strategy.run_backtest(df)

    # TSLA Time-Based 15m (VOLUME 1.3x)
    strategy = TimeBasedScalpingStrategy("TSLA", "15mins", momentum_period=10, volume_multiplier=1.3)
    results['TSLA_TimeBased_15m_Vol1_3x'] = strategy.run_backtest(df)

    # ===============================
    # RSI SCALPING STRATEGIES
    # ===============================

    logger.info("🔍 Validating RSI Scalping Strategies...")

    # GOOGL RSI 15m (AGGRESSIVE) - TOP RSI PERFORMER
    strategy = RSIScalpingStrategy("GOOGL", "15mins", rsi_period=7, rsi_oversold=25, rsi_overbought=75)
    df = load_stock_data("GOOGL", "15mins")
    results['GOOGL_RSI_15m_Aggressive'] = strategy.run_backtest(df)

    # BAC RSI 15m (AGGRESSIVE) - UNDERPERFORMING
    strategy = RSIScalpingStrategy("BAC", "15mins", rsi_period=7, rsi_oversold=25, rsi_overbought=75)
    df = load_stock_data("BAC", "15mins")
    results['BAC_RSI_15m_Aggressive'] = strategy.run_backtest(df)

    # ===============================
    # VOLUME BREAKOUT STRATEGIES
    # ===============================

    logger.info("🔍 Validating Volume Breakout Strategies...")

    # AMD Volume Breakout 5m (1.8x VOLUME)
    strategy = VolumeBreakoutStrategy("AMD", "5mins", volume_multiplier=1.8)
    df = load_stock_data("AMD", "5mins")
    results['AMD_VolumeBreakout_5m_1_8x'] = strategy.run_backtest(df)

    # AMD Volume Breakout 5m (2.0x VOLUME)
    strategy = VolumeBreakoutStrategy("AMD", "5mins", volume_multiplier=2.0)
    results['AMD_VolumeBreakout_5m_2_0x'] = strategy.run_backtest(df)

    # MSFT Volume Breakout 15m
    strategy = VolumeBreakoutStrategy("MSFT", "15mins", volume_multiplier=1.5)
    df = load_stock_data("MSFT", "15mins")
    results['MSFT_VolumeBreakout_15m'] = strategy.run_backtest(df)

    # ===============================
    # CANDLESTICK SCALPING STRATEGIES
    # ===============================

    logger.info("🔍 Validating Candlestick Strategies...")

    # GLD Candlestick 5m (VOLUME 1.4x) - BEST CANDLESTICK
    strategy = CandlestickScalpingStrategy("GLD", "5mins", volume_multiplier=1.4)
    df = load_stock_data("GLD", "5mins")
    results['GLD_Candlestick_5m_Vol1_4x'] = strategy.run_backtest(df)

    # DIA Candlestick 5m (DEFAULT)
    strategy = CandlestickScalpingStrategy("DIA", "5mins", volume_multiplier=1.2)
    df = load_stock_data("DIA", "5mins")
    results['DIA_Candlestick_5m_Default'] = strategy.run_backtest(df)

    # MSFT Candlestick 15m
    strategy = CandlestickScalpingStrategy("MSFT", "15mins", volume_multiplier=1.2)
    df = load_stock_data("MSFT", "15mins")
    results['MSFT_Candlestick_15m'] = strategy.run_backtest(df)

    # SPY Candlestick 5m
    strategy = CandlestickScalpingStrategy("SPY", "5mins", volume_multiplier=1.2)
    df = load_stock_data("SPY", "5mins")
    results['SPY_Candlestick_5m'] = strategy.run_backtest(df)

    # ===============================
    # FIBONACCI MOMENTUM STRATEGIES
    # ===============================

    logger.info("🔍 Validating Fibonacci Momentum Strategies...")

    # GLD Fibonacci Momentum 5m - TOP GLD PERFORMER
    strategy = FibonacciMomentumStrategy("GLD", "5mins")
    df = load_stock_data("GLD", "5mins")
    results['GLD_Fibonacci_Momentum_5m'] = strategy.run_backtest(df)

    # ===============================
    # SESSION MOMENTUM STRATEGIES
    # ===============================

    logger.info("🔍 Validating Session Momentum Strategies...")

    # GLD Session Momentum 5m - HIGH PERFORMANCE
    # Note: Need to implement SessionMomentumStrategy class

    # ===============================
    # ATR RANGE SCALPING STRATEGIES
    # ===============================

    logger.info("🔍 Validating ATR Range Strategies...")

    # GLD ATR Range Scalping 5m - SOLID PERFORMANCE
    # Note: Need to implement ATRRangeStrategy class

    # ===============================
    # CRYPTO STRATEGIES
    # ===============================

    logger.info("🔍 Validating Crypto Strategies...")

    # BTC VWAP Range (Aggressive) 5m - BEST BTC STRATEGY
    # ETH Volatility Breakout 1h - 0.248% daily return

    return results

def print_results_summary(results: Dict):
    """Print a summary of validation results"""

    print("\n" + "="*80)
    print("🎯 COMPREHENSIVE STRATEGY VALIDATION RESULTS")
    print("="*80)

    print(f"\nValidated {len(results)} strategies over 2-year period (2023-2025)")
    print("\n📊 PERFORMANCE SUMMARY:")
    print("<15")
    print("-" * 85)

    valid_strategies = 0
    for strategy_name, metrics in results.items():
        if 'error' in metrics:
            print("<15")
            continue

        valid_strategies += 1
        total_return = metrics['total_return']
        win_rate = metrics['win_rate'] * 100
        total_trades = metrics['total_trades']
        max_dd = metrics['max_drawdown']
        sharpe = metrics['sharpe_ratio']

        # Color coding based on performance
        if total_return > 50:
            perf_indicator = "🟢 EXCELLENT"
        elif total_return > 20:
            perf_indicator = "🟡 GOOD"
        elif total_return > 0:
            perf_indicator = "🟠 OK"
        else:
            perf_indicator = "🔴 POOR"

        print("<15")

    print(f"\n✅ Successfully validated {valid_strategies} out of {len(results)} strategies")
    print("\n📋 DETAILED RESULTS:")

    for strategy_name, metrics in results.items():
        if 'error' in metrics:
            print(f"\n❌ {strategy_name}: {metrics['error']}")
            continue

        print(f"\n🎯 {strategy_name}")
        print(f"   Total Return: {metrics['total_return']:.2f}")
        print(f"   Win Rate: {metrics['win_rate']*100:.1f}%")
        print(f"   Total Trades: {metrics['total_trades']}")
        print(f"   Avg Trade Return: {metrics['avg_trade_return']:.4f}")
        print(f"   Max Drawdown: {metrics['max_drawdown']:.2f}")
        print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")

def main():
    """Main validation function"""
    logger.info("🚀 Starting comprehensive strategy validation...")

    # Validate all strategies
    results = validate_all_strategies()

    # Print summary
    print_results_summary(results)

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/Users/a1/Projects/Trading/trading-bots/validation_results_{timestamp}.json"

    import json
    with open(results_file, 'w') as f:
        # Convert numpy types to native Python types for JSON serialization
        json_results = {}
        for k, v in results.items():
            json_results[k] = {}
            for k2, v2 in v.items():
                if isinstance(v2, np.float64):
                    json_results[k][k2] = float(v2)
                elif isinstance(v2, np.int64):
                    json_results[k][k2] = int(v2)
                else:
                    json_results[k][k2] = v2
        json.dump(json_results, f, indent=2, default=str)

    logger.info(f"📁 Detailed results saved to: {results_file}")
    print(f"\n📁 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    main()
