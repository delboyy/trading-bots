"""
Comprehensive Scalping Strategy Framework
Supports 7 different scalping strategies with multiple parameter combinations
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from shared_utils.indicators import (
    on_balance_volume, volume_price_trend, get_session_indicator,
    detect_doji, detect_hammer, detect_engulfing, detect_morning_star, detect_evening_star,
    keltner_channels, stochastic_oscillator
)


class ScalpingStrategy:
    """
    Comprehensive scalping strategy framework supporting 7 different strategies:
    1. Advanced Scalping (multi-indicator)
    2. OBV Scalping (volume-based)
    3. Candlestick Scalping (pattern-based)
    4. Momentum Scalping (momentum-based)
    5. RSI Scalping (oscillator-based)
    6. Volume Breakout (breakout-based)
    7. Time-Based Scalping (session-aware)
    """

    def __init__(self, data: pd.DataFrame, strategy_type: str = 'advanced_scalping', **kwargs):
        self.data = data.copy()
        self.strategy_type = strategy_type

        # Common parameters
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.005)  # 0.5%
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.01)  # 1.0%
        self.max_hold_time = kwargs.get('max_hold_time', 12)  # bars
        self.min_volume_ratio = kwargs.get('min_volume_ratio', 1.2)

        # Strategy-specific parameters
        self.params = self._get_strategy_params(**kwargs)

        # Add indicators
        self._add_indicators()

    def _get_strategy_params(self, **kwargs) -> Dict[str, Any]:
        """Get parameters for the specific strategy type"""
        base_params = {
            'rsi_period': kwargs.get('rsi_period', 14),
            'rsi_overbought': kwargs.get('rsi_overbought', 70),
            'rsi_oversold': kwargs.get('rsi_oversold', 30),
            'bb_period': kwargs.get('bb_period', 20),
            'bb_std': kwargs.get('bb_std', 2.0),
            'ema_fast': kwargs.get('ema_fast', 9),
            'ema_slow': kwargs.get('ema_slow', 21),
            'volume_multiplier': kwargs.get('volume_multiplier', 1.5),
            'momentum_period': kwargs.get('momentum_period', 10),
            'obv_period': kwargs.get('obv_period', 21),
            'stoch_period': kwargs.get('stoch_period', 14),
            'keltner_period': kwargs.get('keltner_period', 20),
        }

        return base_params

    def _add_indicators(self):
        """Add all technical indicators to the dataframe"""
        df = self.data

        # Basic price indicators
        df['returns'] = df['Close'].pct_change()
        df['ema_fast'] = df['Close'].ewm(span=self.params['ema_fast']).mean()
        df['ema_slow'] = df['Close'].ewm(span=self.params['ema_slow']).mean()

        # RSI calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.params['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(self.params['bb_period']).mean()
        df['bb_std'] = df['Close'].rolling(self.params['bb_period']).std()
        df['bb_upper'] = df['bb_middle'] + (self.params['bb_std'] * df['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (self.params['bb_std'] * df['bb_std'])

        # Volume indicators
        df['obv'] = on_balance_volume(df)
        df['vpt'] = volume_price_trend(df)
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']

        # OBV trend and signals
        df['obv_sma'] = df['obv'].rolling(self.params['obv_period']).mean()
        df['obv_trend'] = np.where(df['obv'] > df['obv_sma'], 1, -1)

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

        # Momentum
        df['momentum'] = df['Close'] - df['Close'].shift(self.params['momentum_period'])
        df['momentum_sma'] = df['momentum'].rolling(5).mean()

        # Trend strength
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['ema_slow']

        # Volume breakout detection
        df['high_breakout'] = df['High'] > df['High'].rolling(20).max().shift(1)
        df['low_breakout'] = df['Low'] < df['Low'].rolling(20).min().shift(1)

        self.data = df

    def _get_signals(self) -> pd.Series:
        """Generate signals based on strategy type"""
        if self.strategy_type == 'advanced_scalping':
            return self._advanced_scalping_signals()
        elif self.strategy_type == 'obv_scalping':
            return self._obv_scalping_signals()
        elif self.strategy_type == 'candlestick_scalping':
            return self._candlestick_scalping_signals()
        elif self.strategy_type == 'momentum_scalping':
            return self._momentum_scalping_signals()
        elif self.strategy_type == 'rsi_scalping':
            return self._rsi_scalping_signals()
        elif self.strategy_type == 'volume_breakout':
            return self._volume_breakout_signals()
        elif self.strategy_type == 'time_based_scalping':
            return self._time_based_scalping_signals()
        else:
            raise ValueError(f"Unknown strategy type: {self.strategy_type}")

    def _advanced_scalping_signals(self) -> pd.Series:
        """Advanced scalping with multiple confirmations"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # Base conditions
        ema_trend_up = df['ema_fast'] > df['ema_slow']
        ema_trend_down = df['ema_fast'] < df['ema_slow']
        rsi_oversold = df['rsi'] < self.params['rsi_oversold']
        rsi_overbought = df['rsi'] > self.params['rsi_overbought']
        high_volume = df['volume_ratio'] > self.params['volume_multiplier']

        # Price near BB edges
        near_lower_bb = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) < 0.1
        near_upper_bb = (df['bb_upper'] - df['Close']) / (df['bb_upper'] - df['bb_lower']) < 0.1

        # Stochastic conditions
        stoch_oversold = df['stoch_k'] < 20
        stoch_overbought = df['stoch_k'] > 80

        # Candlestick patterns
        bullish_patterns = (df['hammer'] | df['bullish_engulfing'] | df['morning_star'] |
                          (df['doji'] & ema_trend_up))
        bearish_patterns = (df['shooting_star'] | df['bearish_engulfing'] | df['evening_star'] |
                           (df['doji'] & ema_trend_down))

        # Session filter
        ny_session = df['session'].isin([2, 3])  # NY AM/PM

        # LONG SIGNALS
        long_signal = (ema_trend_up & rsi_oversold & near_lower_bb & stoch_oversold &
                      bullish_patterns & high_volume & ny_session)
        signals[long_signal] = 1

        # SHORT SIGNALS
        short_signal = (ema_trend_down & rsi_overbought & near_upper_bb & stoch_overbought &
                       bearish_patterns & high_volume & ny_session)
        signals[short_signal] = -1

        return signals

    def _obv_scalping_signals(self) -> pd.Series:
        """OBV-based scalping signals"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # OBV trend and divergence
        obv_bullish = (df['obv'] > df['obv_sma']) & (df['obv_trend'] == 1)
        obv_bearish = (df['obv'] < df['obv_sma']) & (df['obv_trend'] == -1)

        # Price confirmation
        price_up = df['Close'] > df['Close'].shift(1)
        price_down = df['Close'] < df['Close'].shift(1)

        # Volume confirmation
        high_volume = df['volume_ratio'] > self.params['volume_multiplier']

        # RSI filter
        rsi_oversold = df['rsi'] < self.params['rsi_oversold']
        rsi_overbought = df['rsi'] > self.params['rsi_overbought']

        # LONG: OBV bullish + price up + volume + oversold RSI
        long_signal = obv_bullish & price_up & high_volume & rsi_oversold
        signals[long_signal] = 1

        # SHORT: OBV bearish + price down + volume + overbought RSI
        short_signal = obv_bearish & price_down & high_volume & rsi_overbought
        signals[short_signal] = -1

        return signals

    def _candlestick_scalping_signals(self) -> pd.Series:
        """Candlestick pattern-based scalping"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # Volume confirmation required
        high_volume = df['volume_ratio'] > self.params['volume_multiplier']

        # Trend confirmation
        ema_trend_up = df['ema_fast'] > df['ema_slow']
        ema_trend_down = df['ema_fast'] < df['ema_slow']

        # LONG SIGNALS
        long_patterns = (df['hammer'] | df['bullish_engulfing'] | df['morning_star'])
        long_signal = long_patterns & ema_trend_up & high_volume
        signals[long_signal] = 1

        # SHORT SIGNALS
        short_patterns = (df['shooting_star'] | df['bearish_engulfing'] | df['evening_star'])
        short_signal = short_patterns & ema_trend_down & high_volume
        signals[short_signal] = -1

        return signals

    def _momentum_scalping_signals(self) -> pd.Series:
        """Momentum-based scalping"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # Momentum signals
        momentum_positive = df['momentum'] > df['momentum_sma']
        momentum_negative = df['momentum'] < df['momentum_sma']

        # Volume and RSI confirmation
        high_volume = df['volume_ratio'] > self.params['volume_multiplier']
        rsi_oversold = df['rsi'] < self.params['rsi_oversold']
        rsi_overbought = df['rsi'] > self.params['rsi_overbought']

        # LONG: Positive momentum + volume + oversold
        long_signal = momentum_positive & high_volume & rsi_oversold
        signals[long_signal] = 1

        # SHORT: Negative momentum + volume + overbought
        short_signal = momentum_negative & high_volume & rsi_overbought
        signals[short_signal] = -1

        return signals

    def _rsi_scalping_signals(self) -> pd.Series:
        """RSI-based scalping"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # RSI extremes
        rsi_oversold = df['rsi'] < self.params['rsi_oversold']
        rsi_overbought = df['rsi'] > self.params['rsi_overbought']

        # Volume confirmation
        high_volume = df['volume_ratio'] > self.params['volume_multiplier']

        # Price action confirmation
        near_support = df['Close'] < df['bb_lower'] * 1.01
        near_resistance = df['Close'] > df['bb_upper'] * 0.99

        # LONG: Oversold RSI + volume + near support
        long_signal = rsi_oversold & high_volume & near_support
        signals[long_signal] = 1

        # SHORT: Overbought RSI + volume + near resistance
        short_signal = rsi_overbought & high_volume & near_resistance
        signals[short_signal] = -1

        return signals

    def _volume_breakout_signals(self) -> pd.Series:
        """Volume breakout scalping"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # Volume spikes
        volume_spike = df['volume_ratio'] > self.params['volume_multiplier'] * 1.5

        # Price breakouts
        high_breakout = df['high_breakout']
        low_breakout = df['low_breakout']

        # RSI filter to avoid extreme conditions
        rsi_neutral = (df['rsi'] > 35) & (df['rsi'] < 65)

        # LONG: High breakout + volume spike + neutral RSI
        long_signal = high_breakout & volume_spike & rsi_neutral
        signals[long_signal] = 1

        # SHORT: Low breakout + volume spike + neutral RSI
        short_signal = low_breakout & volume_spike & rsi_neutral
        signals[short_signal] = -1

        return signals

    def _time_based_scalping_signals(self) -> pd.Series:
        """Session-based scalping"""
        df = self.data
        signals = pd.Series(0, index=df.index)

        # Session identification
        ny_am = df['session'] == 2  # NY AM session
        ny_pm = df['session'] == 3  # NY PM session
        asia = df['session'] == 0   # Asia session
        london = df['session'] == 1 # London session

        # Volume and momentum
        high_volume = df['volume_ratio'] > self.params['volume_multiplier']
        momentum_up = df['momentum'] > 0
        momentum_down = df['momentum'] < 0

        # NY AM: Focus on momentum continuation
        nyam_long = ny_am & momentum_up & high_volume
        nyam_short = ny_am & momentum_down & high_volume

        # NY PM: Profit-taking patterns
        nypm_long = ny_pm & (df['rsi'] < 40) & high_volume
        nypm_short = ny_pm & (df['rsi'] > 60) & high_volume

        # London: Opening range breakouts
        london_long = london & df['high_breakout'] & high_volume
        london_short = london & df['low_breakout'] & high_volume

        # Combine signals
        signals[nyam_long | nypm_long | london_long] = 1
        signals[nyam_short | nypm_short | london_short] = -1

        return signals

    def backtest(self) -> Dict[str, Any]:
        """Run backtest and return results"""
        signals = self._get_signals()

        if signals.sum() == 0:
            return {
                'total_return': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'avg_trade_return': 0.0,
                'holding_time_avg': 0.0,
                'trades': []
            }

        # Simulate trades
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        peak_capital = capital
        max_drawdown = 0

        for i in range(len(signals)):
            if signals.iloc[i] != 0 and position == 0:
                # Enter position
                position = signals.iloc[i]
                entry_price = self.data['Close'].iloc[i]
                entry_time = self.data.index[i]
                shares = capital // entry_price

            elif position != 0:
                current_price = self.data['Close'].iloc[i]
                current_time = self.data.index[i]

                # Check exit conditions
                exit_trade = False
                exit_reason = ""

                # Stop loss
                if position == 1 and current_price <= entry_price * (1 - self.stop_loss_pct):
                    exit_trade = True
                    exit_reason = "stop_loss"
                elif position == -1 and current_price >= entry_price * (1 + self.stop_loss_pct):
                    exit_trade = True
                    exit_reason = "stop_loss"

                # Take profit
                elif position == 1 and current_price >= entry_price * (1 + self.take_profit_pct):
                    exit_trade = True
                    exit_reason = "take_profit"
                elif position == -1 and current_price <= entry_price * (1 - self.take_profit_pct):
                    exit_trade = True
                    exit_reason = "take_profit"

                # Max hold time
                elif (current_time - entry_time).total_seconds() / 60 > self.max_hold_time * 5:  # Assuming 5min bars
                    exit_trade = True
                    exit_reason = "max_time"

                if exit_trade:
                    # Exit position
                    exit_price = current_price
                    pnl = (exit_price - entry_price) * shares * position
                    capital += pnl

                    trade = {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position': position,
                        'pnl': pnl,
                        'return_pct': pnl / (entry_price * shares),
                        'holding_time': (current_time - entry_time).total_seconds() / 60,
                        'exit_reason': exit_reason
                    }
                    trades.append(trade)

                    # Update drawdown
                    if capital > peak_capital:
                        peak_capital = capital
                    current_drawdown = (peak_capital - capital) / peak_capital
                    max_drawdown = max(max_drawdown, current_drawdown)

                    position = 0

        # Calculate metrics
        if trades:
            returns = [t['return_pct'] for t in trades]
            winning_trades = [t for t in trades if t['pnl'] > 0]

            total_return = (capital - 10000) / 10000
            win_rate = len(winning_trades) / len(trades)
            avg_trade_return = np.mean(returns) if returns else 0
            holding_time_avg = np.mean([t['holding_time'] for t in trades])

            # Sharpe ratio (simplified)
            if len(returns) > 1:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            total_return = 0
            win_rate = 0
            avg_trade_return = 0
            holding_time_avg = 0
            sharpe_ratio = 0

        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_return': avg_trade_return,
            'holding_time_avg': holding_time_avg,
            'trades': trades
        }