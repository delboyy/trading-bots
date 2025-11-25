"""
Advanced Scalping Strategy
Combines multiple indicators and candlestick patterns for high-frequency trading
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from shared_utils.indicators import (
    on_balance_volume, volume_price_trend, get_session_indicator,
    detect_doji, detect_hammer, detect_engulfing, detect_morning_star, detect_evening_star,
    keltner_channels, stochastic_oscillator
)


class AdvancedScalpingStrategy:
    """
    Advanced scalping strategy combining multiple technical indicators
    Optimized for 5-15-30 minute timeframes
    """

    def __init__(self, data: pd.DataFrame, **kwargs):
        self.data = data.copy()

        # Strategy parameters
        self.rsi_period = kwargs.get('rsi_period', 14)
        self.rsi_overbought = kwargs.get('rsi_overbought', 70)
        self.rsi_oversold = kwargs.get('rsi_oversold', 30)

        self.bb_period = kwargs.get('bb_period', 20)
        self.bb_std = kwargs.get('bb_std', 2.0)

        self.ema_fast = kwargs.get('ema_fast', 9)
        self.ema_slow = kwargs.get('ema_slow', 21)

        self.volume_threshold = kwargs.get('volume_threshold', 1.5)  # Volume above average

        # Risk management
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.005)  # 0.5%
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.01)  # 1.0%
        self.max_hold_time = kwargs.get('max_hold_time', 12)  # bars

        # Add all indicators
        self._add_indicators()

    def _add_indicators(self):
        """Add all technical indicators to the dataframe"""
        df = self.data

        # Basic price indicators
        df['ema_fast'] = df['Close'].ewm(span=self.ema_fast).mean()
        df['ema_slow'] = df['Close'].ewm(span=self.ema_slow).mean()

        # RSI calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(self.bb_period).mean()
        df['bb_std'] = df['Close'].rolling(self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (self.bb_std * df['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (self.bb_std * df['bb_std'])

        # Volume indicators
        df['obv'] = on_balance_volume(df)
        df['vpt'] = volume_price_trend(df)
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']

        # Session indicator
        df['session'] = get_session_indicator(df)

        # Candlestick patterns
        df['doji'] = detect_doji(df)
        df['hammer'], df['shooting_star'] = detect_hammer(df)
        df['bullish_engulfing'], df['bearish_engulfing'] = detect_engulfing(df)
        df['morning_star'] = detect_morning_star(df)
        df['evening_star'] = detect_evening_star(df)

        # Advanced indicators
        df['stoch_k'], df['stoch_d'] = stochastic_oscillator(df)
        df['keltner_upper'], df['keltner_middle'], df['keltner_lower'] = keltner_channels(df)

        # Trend strength
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['ema_slow']

        # Momentum
        df['momentum'] = df['Close'] - df['Close'].shift(5)
        df['momentum_sma'] = df['momentum'].rolling(5).mean()

        self.data = df

    def _get_scalping_signals(self) -> pd.Series:
        """
        Generate scalping signals using multiple confirmation factors
        """
        df = self.data
        signals = pd.Series(0, index=df.index)

        # Base conditions
        ema_trend_up = df['ema_fast'] > df['ema_slow']
        ema_trend_down = df['ema_fast'] < df['ema_slow']

        rsi_oversold = df['rsi'] < self.rsi_oversold
        rsi_overbought = df['rsi'] > self.rsi_overbought

        high_volume = df['volume_ratio'] > self.volume_threshold

        # Price near Bollinger Band edges
        near_lower_bb = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) < 0.1
        near_upper_bb = (df['bb_upper'] - df['Close']) / (df['bb_upper'] - df['bb_lower']) < 0.1

        # Stochastic conditions
        stoch_oversold = df['stoch_k'] < 20
        stoch_overbought = df['stoch_k'] > 80

        # Candlestick confirmation
        bullish_patterns = (
            df['hammer'] |
            df['bullish_engulfing'] |
            df['morning_star'] |
            (df['doji'] & ema_trend_up)  # Doji in uptrend = bullish
        )

        bearish_patterns = (
            df['shooting_star'] |
            df['bearish_engulfing'] |
            df['evening_star'] |
            (df['doji'] & ema_trend_down)  # Doji in downtrend = bearish
        )

        # Session filtering (prefer NY session for scalping)
        ny_session = df['session'] == 3  # NY Day session

        # LONG SIGNALS (Multiple confirmations required)
        long_signal = (
            ema_trend_up &
            rsi_oversold &
            near_lower_bb &
            stoch_oversold &
            bullish_patterns &
            high_volume &
            ny_session
        )

        # SHORT SIGNALS (Multiple confirmations required)
        short_signal = (
            ema_trend_down &
            rsi_overbought &
            near_upper_bb &
            stoch_overbought &
            bearish_patterns &
            high_volume &
            ny_session
        )

        # Apply signals
        signals[long_signal] = 1
        signals[short_signal] = -1

        # Exit logic - close positions after max hold time or target/stop hit
        # This will be handled in the main strategy loop

        return signals

    def _calculate_dynamic_stops(self, entry_price: float, direction: int) -> Tuple[float, float]:
        """
        Calculate dynamic stop loss and take profit based on volatility
        """
        current_atr = self.data['bb_std'].iloc[-1]  # Use BB std as volatility proxy

        if direction == 1:  # Long
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            take_profit = entry_price * (1 + self.take_profit_pct)
        else:  # Short
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            take_profit = entry_price * (1 - self.take_profit_pct)

        return stop_loss, take_profit

    def generate_signals(self) -> pd.Series:
        """
        Main signal generation method
        """
        return self._get_scalping_signals()

    def get_current_analysis(self) -> Dict[str, Any]:
        """
        Get current market analysis for decision making
        """
        if len(self.data) < 50:  # Not enough data
            return {}

        latest = self.data.iloc[-1]

        return {
            'trend': 'bullish' if latest['ema_fast'] > latest['ema_slow'] else 'bearish',
            'rsi': latest['rsi'],
            'volume_ratio': latest['volume_ratio'],
            'bb_position': (latest['Close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower']),
            'stoch_k': latest['stoch_k'],
            'stoch_d': latest['stoch_d'],
            'session': latest['session'],
            'momentum': latest['momentum'],
            'doji': latest['doji'],
            'hammer': latest['hammer'],
            'shooting_star': latest['shooting_star'],
            'bullish_engulfing': latest['bullish_engulfing'],
            'bearish_engulfing': latest['bearish_engulfing']
        }


class OBVScalpingStrategy:
    """
    OBV-based scalping strategy
    Focuses on volume confirmation for price movements
    """

    def __init__(self, data: pd.DataFrame, **kwargs):
        self.data = data.copy()
        self.obv_period = kwargs.get('obv_period', 20)
        self.volume_threshold = kwargs.get('volume_threshold', 1.2)
        self._add_indicators()

    def _add_indicators(self):
        df = self.data
        df['obv'] = on_balance_volume(df)
        df['obv_sma'] = df['obv'].rolling(self.obv_period).mean()
        df['obv_signal'] = df['obv'] - df['obv_sma']
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        df['ema_fast'] = df['Close'].ewm(span=5).mean()
        df['ema_slow'] = df['Close'].ewm(span=13).mean()
        self.data = df

    def generate_signals(self) -> pd.Series:
        df = self.data
        signals = pd.Series(0, index=df.index)

        # OBV divergence signals
        obv_bullish = (df['obv_signal'] > 0) & (df['obv_signal'].shift(1) < 0)
        obv_bearish = (df['obv_signal'] < 0) & (df['obv_signal'].shift(1) > 0)

        # Volume confirmation
        high_volume = df['volume_ratio'] > self.volume_threshold

        # Trend confirmation
        trend_up = df['ema_fast'] > df['ema_slow']
        trend_down = df['ema_fast'] < df['ema_slow']

        # Generate signals
        signals[obv_bullish & high_volume & trend_up] = 1
        signals[obv_bearish & high_volume & trend_down] = -1

        return signals


class CandlestickScalpingStrategy:
    """
    Pure candlestick pattern-based scalping
    Focuses on pattern recognition with volume confirmation
    """

    def __init__(self, data: pd.DataFrame, **kwargs):
        self.data = data.copy()
        self.volume_threshold = kwargs.get('volume_threshold', 1.3)
        self._add_indicators()

    def _add_indicators(self):
        df = self.data

        # Candlestick patterns
        df['doji'] = detect_doji(df)
        df['hammer'], df['shooting_star'] = detect_hammer(df)
        df['bullish_engulfing'], df['bearish_engulfing'] = detect_engulfing(df)
        df['morning_star'] = detect_morning_star(df)
        df['evening_star'] = detect_evening_star(df)

        # Volume confirmation
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']

        # Trend context
        df['ema_9'] = df['Close'].ewm(span=9).mean()
        df['ema_21'] = df['Close'].ewm(span=21).mean()

        self.data = df

    def generate_signals(self) -> pd.Series:
        df = self.data
        signals = pd.Series(0, index=df.index)

        # High volume condition
        high_volume = df['volume_ratio'] > self.volume_threshold

        # Trend context
        uptrend = df['ema_9'] > df['ema_21']
        downtrend = df['ema_9'] < df['ema_21']

        # Bullish signals
        bullish_signal = (
            high_volume & (
                df['hammer'] |
                df['bullish_engulfing'] |
                df['morning_star'] |
                (df['doji'] & uptrend)
            )
        )

        # Bearish signals
        bearish_signal = (
            high_volume & (
                df['shooting_star'] |
                df['bearish_engulfing'] |
                df['evening_star'] |
                (df['doji'] & downtrend)
            )
        )

        signals[bullish_signal] = 1
        signals[bearish_signal] = -1

        return signals
