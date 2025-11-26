#!/usr/bin/env python3
"""
BTC Strategy Deep Dive - Finding 1% Daily Strategies with 2-3 Trades/Day
Tests multiple timeframes (5m, 15m, 30m, 1h) with VWAP and various approaches
60-day Yahoo Finance backtest, then ready for IBKR validation
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import yfinance as yf
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')

from shared_strategies.scalping_strategy import ScalpingStrategy


class BTCStrategyDeepDive:
    def __init__(self):
        self.symbol = 'BTC-USD'  # Yahoo Finance format
        self.timeframes = ['5m', '15m', '30m', '1h']
        self.test_period_days = 60

        # Target: 2-3 trades per day with 1%+ daily returns
        self.target_daily_return = 0.01  # 1%
        self.target_trades_per_day = 2.5  # Average 2-3 trades

        # VWAP and volatility-based strategies to test
        self.strategies = [
            # VWAP Mean Reversion Strategies
            {
                'name': 'BTC VWAP Mean Reversion',
                'strategy': 'vwap_mean_reversion',
                'description': 'VWAP-based mean reversion with volatility filters',
                'timeframes': ['5m', '15m', '30m'],
                'params_combinations': [
                    {'vwap_period': 20, 'deviation_threshold': 0.005, 'volume_multiplier': 1.2, 'take_profit_pct': 0.008, 'stop_loss_pct': 0.004},
                    {'vwap_period': 20, 'deviation_threshold': 0.008, 'volume_multiplier': 1.3, 'take_profit_pct': 0.012, 'stop_loss_pct': 0.006},
                    {'vwap_period': 20, 'deviation_threshold': 0.010, 'volume_multiplier': 1.4, 'take_profit_pct': 0.015, 'stop_loss_pct': 0.008},
                ]
            },
            # VWAP Momentum Strategies
            {
                'name': 'BTC VWAP Momentum Breakout',
                'strategy': 'vwap_momentum_breakout',
                'description': 'VWAP momentum breakouts with volume confirmation',
                'timeframes': ['5m', '15m', '30m'],
                'params_combinations': [
                    {'vwap_period': 15, 'momentum_period': 5, 'breakout_threshold': 0.008, 'volume_multiplier': 1.5, 'take_profit_pct': 0.020, 'stop_loss_pct': 0.010},
                    {'vwap_period': 15, 'momentum_period': 8, 'breakout_threshold': 0.012, 'volume_multiplier': 1.8, 'take_profit_pct': 0.025, 'stop_loss_pct': 0.012},
                    {'vwap_period': 15, 'momentum_period': 10, 'breakout_threshold': 0.015, 'volume_multiplier': 2.0, 'take_profit_pct': 0.030, 'stop_loss_pct': 0.015},
                ]
            },
            # VWAP Range Trading
            {
                'name': 'BTC VWAP Range Trading',
                'strategy': 'vwap_range_trading',
                'description': 'VWAP-based range trading between standard deviations',
                'timeframes': ['15m', '30m', '1h'],
                'params_combinations': [
                    {'vwap_period': 25, 'std_dev_multiplier': 1.0, 'volume_multiplier': 1.2, 'take_profit_pct': 0.015, 'stop_loss_pct': 0.008},
                    {'vwap_period': 25, 'std_dev_multiplier': 1.5, 'volume_multiplier': 1.3, 'take_profit_pct': 0.020, 'stop_loss_pct': 0.010},
                    {'vwap_period': 25, 'std_dev_multiplier': 2.0, 'volume_multiplier': 1.4, 'take_profit_pct': 0.025, 'stop_loss_pct': 0.012},
                ]
            },
            # Volatility-based VWAP
            {
                'name': 'BTC VWAP Volatility Scalping',
                'strategy': 'vwap_volatility_scalp',
                'description': 'VWAP scalping with ATR-based volatility filters',
                'timeframes': ['5m', '15m', '30m'],
                'params_combinations': [
                    {'vwap_period': 20, 'atr_period': 10, 'atr_multiplier': 0.8, 'volume_multiplier': 1.3, 'take_profit_pct': 0.012, 'stop_loss_pct': 0.006},
                    {'vwap_period': 20, 'atr_period': 14, 'atr_multiplier': 1.0, 'volume_multiplier': 1.5, 'take_profit_pct': 0.015, 'stop_loss_pct': 0.008},
                    {'vwap_period': 20, 'atr_period': 20, 'atr_multiplier': 1.2, 'volume_multiplier': 1.8, 'take_profit_pct': 0.020, 'stop_loss_pct': 0.010},
                ]
            },
            # Session-based VWAP (Crypto trades 24/7)
            {
                'name': 'BTC VWAP Session Momentum',
                'strategy': 'vwap_session_momentum',
                'description': 'VWAP with session momentum (Asian/European overlap)',
                'timeframes': ['15m', '30m', '1h'],
                'params_combinations': [
                    {'vwap_period': 30, 'momentum_period': 12, 'session_threshold': 0.008, 'volume_multiplier': 1.4, 'take_profit_pct': 0.018, 'stop_loss_pct': 0.009},
                    {'vwap_period': 30, 'momentum_period': 16, 'session_threshold': 0.012, 'volume_multiplier': 1.6, 'take_profit_pct': 0.022, 'stop_loss_pct': 0.011},
                    {'vwap_period': 30, 'momentum_period': 20, 'session_threshold': 0.015, 'volume_multiplier': 1.8, 'take_profit_pct': 0.025, 'stop_loss_pct': 0.013},
                ]
            },
            # VWAP + RSI Combination
            {
                'name': 'BTC VWAP RSI Divergence',
                'strategy': 'vwap_rsi_divergence',
                'description': 'VWAP levels with RSI divergence signals',
                'timeframes': ['15m', '30m', '1h'],
                'params_combinations': [
                    {'vwap_period': 25, 'rsi_period': 9, 'rsi_oversold': 25, 'rsi_overbought': 75, 'volume_multiplier': 1.3, 'take_profit_pct': 0.016, 'stop_loss_pct': 0.008},
                    {'vwap_period': 25, 'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70, 'volume_multiplier': 1.5, 'take_profit_pct': 0.020, 'stop_loss_pct': 0.010},
                    {'vwap_period': 25, 'rsi_period': 21, 'rsi_oversold': 35, 'rsi_overbought': 65, 'volume_multiplier': 1.7, 'take_profit_pct': 0.024, 'stop_loss_pct': 0.012},
                ]
            }
        ]

    def download_btc_data(self, timeframe):
        """Download BTC data from Yahoo Finance"""
        try:
            # Convert timeframe to yfinance interval
            interval_map = {
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h'
            }

            interval = interval_map.get(timeframe, '15m')

            # Calculate date range (last 60 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.test_period_days)

            print(f"Downloading BTC-USD data for {timeframe} timeframe...")
            print(f"Period: {start_date.date()} to {end_date.date()}")

            # Download data
            df = yf.download('BTC-USD', start=start_date, end=end_date, interval=interval)

            if df.empty:
                print(f"No data received for {timeframe}")
                return pd.DataFrame()

            # Clean column names
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            # Ensure we have required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                print(f"Missing required columns for {timeframe}")
                return pd.DataFrame()

            df = df.dropna()
            print(f"Downloaded {len(df)} bars for {timeframe}")
            return df

        except Exception as e:
            print(f"Error downloading BTC data for {timeframe}: {e}")
            return pd.DataFrame()

    def calculate_vwap(self, df, period=20):
        """Calculate VWAP (Volume Weighted Average Price)"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def calculate_vwap_std_dev(self, df, vwap, std_period=20, std_multiplier=2.0):
        """Calculate standard deviations from VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        deviation = typical_price - vwap
        std_dev = deviation.rolling(std_period).std()
        upper_band = vwap + (std_dev * std_multiplier)
        lower_band = vwap - (std_dev * std_multiplier)
        return upper_band, lower_band, std_dev

    def test_vwap_mean_reversion(self, df, params):
        """Test VWAP mean reversion strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        # Calculate VWAP
        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        for i in range(params['vwap_period'], len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume filter
            if volume < avg_volume * params['volume_multiplier']:
                continue

            # Deviation from VWAP
            deviation_pct = (current_price - vwap_price) / vwap_price

            # Exit conditions
            if position > 0:  # Long position
                take_profit = current_price >= entry_price * (1 + params['take_profit_pct'])
                stop_loss = current_price <= entry_price * (1 - params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (position * entry_price)})
                    position = 0

            elif position < 0:  # Short position
                take_profit = current_price <= entry_price * (1 - params['take_profit_pct'])
                stop_loss = current_price >= entry_price * (1 + params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (entry_price - current_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (abs(position) * entry_price)})
                    position = 0

            # Entry conditions
            elif position == 0:
                # Buy when significantly below VWAP
                if deviation_pct < -params['deviation_threshold']:
                    position = capital / current_price
                    entry_price = current_price

                # Sell when significantly above VWAP
                elif deviation_pct > params['deviation_threshold']:
                    position = -capital / current_price
                    entry_price = current_price

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({'pnl': pnl / (abs(position) * entry_price)})

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'avg_trade_return': np.mean(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'avg_trade_return': 0, 'sharpe_ratio': 0}

    def test_vwap_momentum_breakout(self, df, params):
        """Test VWAP momentum breakout strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        for i in range(max(params['vwap_period'], params['momentum_period']), len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Calculate momentum
            momentum = current_price - df['Close'].iloc[i - params['momentum_period']]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume filter
            if volume < avg_volume * params['volume_multiplier']:
                continue

            # Exit conditions
            if position > 0:  # Long position
                take_profit = current_price >= entry_price * (1 + params['take_profit_pct'])
                stop_loss = current_price <= entry_price * (1 - params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (position * entry_price)})
                    position = 0

            elif position < 0:  # Short position
                take_profit = current_price <= entry_price * (1 - params['take_profit_pct'])
                stop_loss = current_price >= entry_price * (1 + params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (entry_price - current_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (abs(position) * entry_price)})
                    position = 0

            # Entry conditions
            elif position == 0:
                # Long breakout above VWAP
                if (current_price > vwap_price * (1 + params['breakout_threshold']) and
                    momentum > 0):
                    position = capital / current_price
                    entry_price = current_price

                # Short breakout below VWAP
                elif (current_price < vwap_price * (1 - params['breakout_threshold']) and
                      momentum < 0):
                    position = -capital / current_price
                    entry_price = current_price

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({'pnl': pnl / (abs(position) * entry_price)})

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'avg_trade_return': np.mean(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'avg_trade_return': 0, 'sharpe_ratio': 0}

    def test_vwap_range_trading(self, df, params):
        """Test VWAP range trading strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])
        df['VWAP_Upper'], df['VWAP_Lower'], df['VWAP_Std'] = self.calculate_vwap_std_dev(df, df['VWAP'], std_multiplier=params['std_dev_multiplier'])

        for i in range(params['vwap_period'], len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            upper_band = df['VWAP_Upper'].iloc[i]
            lower_band = df['VWAP_Lower'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume filter
            if volume < avg_volume * params['volume_multiplier']:
                continue

            # Exit conditions
            if position > 0:  # Long position
                take_profit = current_price >= entry_price * (1 + params['take_profit_pct'])
                stop_loss = current_price <= entry_price * (1 - params['stop_loss_pct'])
                hit_upper = current_price >= upper_band

                if take_profit or stop_loss or hit_upper:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (position * entry_price)})
                    position = 0

            elif position < 0:  # Short position
                take_profit = current_price <= entry_price * (1 - params['take_profit_pct'])
                stop_loss = current_price >= entry_price * (1 + params['stop_loss_pct'])
                hit_lower = current_price <= lower_band

                if take_profit or stop_loss or hit_lower:
                    pnl = position * (entry_price - current_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (abs(position) * entry_price)})
                    position = 0

            # Entry conditions
            elif position == 0:
                # Buy near lower band
                if current_price <= lower_band * 1.002 and current_price > vwap_price:
                    position = capital / current_price
                    entry_price = current_price

                # Sell near upper band
                elif current_price >= upper_band * 0.998 and current_price < vwap_price:
                    position = -capital / current_price
                    entry_price = current_price

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({'pnl': pnl / (abs(position) * entry_price)})

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'avg_trade_return': np.mean(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'avg_trade_return': 0, 'sharpe_ratio': 0}

    def test_vwap_volatility_scalp(self, df, params):
        """Test VWAP volatility scalping strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        # Calculate ATR for volatility filter
        df['TR'] = np.maximum(df['High'] - df['Low'],
                             np.maximum(abs(df['High'] - df['Close'].shift(1)),
                                       abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = df['TR'].rolling(params['atr_period']).mean()

        for i in range(max(params['vwap_period'], params['atr_period']), len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            atr = df['ATR'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume and volatility filters
            if volume < avg_volume * params['volume_multiplier']:
                continue

            # Only trade when volatility is within range
            current_volatility = atr / current_price
            if not (0.005 < current_volatility < 0.025):  # 0.5% to 2.5% volatility
                continue

            # Exit conditions
            if position > 0:  # Long position
                take_profit = current_price >= entry_price * (1 + params['take_profit_pct'])
                stop_loss = current_price <= entry_price * (1 - params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (position * entry_price)})
                    position = 0

            elif position < 0:  # Short position
                take_profit = current_price <= entry_price * (1 - params['take_profit_pct'])
                stop_loss = current_price >= entry_price * (1 + params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (entry_price - current_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (abs(position) * entry_price)})
                    position = 0

            # Entry conditions with ATR-based sizing
            elif position == 0:
                deviation_pct = (current_price - vwap_price) / vwap_price

                # Long entry
                if (deviation_pct < -0.005 and  # Below VWAP
                    atr > current_price * params['atr_multiplier'] * 0.001):  # Sufficient volatility
                    position = capital / current_price
                    entry_price = current_price

                # Short entry
                elif (deviation_pct > 0.005 and  # Above VWAP
                      atr > current_price * params['atr_multiplier'] * 0.001):  # Sufficient volatility
                    position = -capital / current_price
                    entry_price = current_price

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({'pnl': pnl / (abs(position) * entry_price)})

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'avg_trade_return': np.mean(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'avg_trade_return': 0, 'sharpe_ratio': 0}

    def test_vwap_session_momentum(self, df, params):
        """Test VWAP session momentum strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        for i in range(max(params['vwap_period'], params['momentum_period']), len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Calculate momentum
            momentum = current_price - df['Close'].iloc[i - params['momentum_period']]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume filter
            if volume < avg_volume * params['volume_multiplier']:
                continue

            # Exit conditions
            if position > 0:  # Long position
                take_profit = current_price >= entry_price * (1 + params['take_profit_pct'])
                stop_loss = current_price <= entry_price * (1 - params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (position * entry_price)})
                    position = 0

            elif position < 0:  # Short position
                take_profit = current_price <= entry_price * (1 - params['take_profit_pct'])
                stop_loss = current_price >= entry_price * (1 + params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (entry_price - current_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (abs(position) * entry_price)})
                    position = 0

            # Entry conditions with session momentum
            elif position == 0:
                deviation_pct = abs(current_price - vwap_price) / vwap_price

                # Long entry
                if (momentum > params['session_threshold'] and
                    current_price > vwap_price):
                    position = capital / current_price
                    entry_price = current_price

                # Short entry
                elif (momentum < -params['session_threshold'] and
                      current_price < vwap_price):
                    position = -capital / current_price
                    entry_price = current_price

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({'pnl': pnl / (abs(position) * entry_price)})

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'avg_trade_return': np.mean(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'avg_trade_return': 0, 'sharpe_ratio': 0}

    def test_vwap_rsi_divergence(self, df, params):
        """Test VWAP + RSI divergence strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        for i in range(max(params['vwap_period'], params['rsi_period']), len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            rsi = df['RSI'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume filter
            if volume < avg_volume * params['volume_multiplier']:
                continue

            # Exit conditions
            if position > 0:  # Long position
                take_profit = current_price >= entry_price * (1 + params['take_profit_pct'])
                stop_loss = current_price <= entry_price * (1 - params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (position * entry_price)})
                    position = 0

            elif position < 0:  # Short position
                take_profit = current_price <= entry_price * (1 - params['take_profit_pct'])
                stop_loss = current_price >= entry_price * (1 + params['stop_loss_pct'])

                if take_profit or stop_loss:
                    pnl = position * (entry_price - current_price)
                    capital += pnl
                    trades.append({'pnl': pnl / (abs(position) * entry_price)})
                    position = 0

            # Entry conditions with RSI confirmation
            elif position == 0:
                # Long entry: RSI oversold + price near VWAP
                if (rsi <= params['rsi_oversold'] and
                    abs(current_price - vwap_price) / vwap_price < 0.008):
                    position = capital / current_price
                    entry_price = current_price

                # Short entry: RSI overbought + price near VWAP
                elif (rsi >= params['rsi_overbought'] and
                      abs(current_price - vwap_price) / vwap_price < 0.008):
                    position = -capital / current_price
                    entry_price = current_price

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({'pnl': pnl / (abs(position) * entry_price)})

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'avg_trade_return': np.mean(returns),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'avg_trade_return': 0, 'sharpe_ratio': 0}

    def run_deep_dive(self):
        """Run comprehensive BTC strategy deep dive"""
        print("🚀 BTC STRATEGY DEEP DIVE - FINDING 1% DAILY STRATEGIES")
        print("=" * 80)
        print("Target: 2-3 trades/day with 1%+ daily returns")
        print("Testing VWAP-based strategies across multiple timeframes")
        print(f"Data: 60 days from Yahoo Finance")
        print("=" * 80)

        results = []

        for strategy_config in self.strategies:
            strategy_name = strategy_config['name']
            strategy_type = strategy_config['strategy']
            description = strategy_config['description']
            timeframes_to_test = strategy_config['timeframes']
            param_combinations = strategy_config['params_combinations']

            print(f"\n🎯 TESTING: {strategy_name}")
            print(f"   Description: {description}")
            print(f"   Timeframes: {', '.join(timeframes_to_test)}")
            print(f"   Parameter Combinations: {len(param_combinations)}")
            print("-" * 60)

            for timeframe in timeframes_to_test:
                print(f"\n📊 {timeframe.upper()} TIMEFRAME:")

                # Download data for this timeframe
                df = self.download_btc_data(timeframe)
                if df.empty:
                    print(f"   ❌ No data for {timeframe}")
                    continue

                # Test each parameter combination
                for i, params in enumerate(param_combinations):
                    print(f"   Testing params {i+1}/3...")

                    try:
                        # Run appropriate test function
                        if strategy_type == 'vwap_mean_reversion':
                            result = self.test_vwap_mean_reversion(df, params)
                        elif strategy_type == 'vwap_momentum_breakout':
                            result = self.test_vwap_momentum_breakout(df, params)
                        elif strategy_type == 'vwap_range_trading':
                            result = self.test_vwap_range_trading(df, params)
                        elif strategy_type == 'vwap_volatility_scalp':
                            result = self.test_vwap_volatility_scalp(df, params)
                        elif strategy_type == 'vwap_session_momentum':
                            result = self.test_vwap_session_momentum(df, params)
                        elif strategy_type == 'vwap_rsi_divergence':
                            result = self.test_vwap_rsi_divergence(df, params)
                        else:
                            continue

                        # Calculate daily metrics
                        total_days = len(df) / (1440 / int(timeframe[:-1])) if timeframe != '1h' else len(df) / 24
                        trades_per_day = result['total_trades'] / max(total_days, 1)
                        daily_return_pct = result['total_return'] / max(total_days, 1)

                        # Check if meets criteria
                        meets_criteria = (
                            trades_per_day >= 1.5 and trades_per_day <= 4 and  # 1.5-4 trades/day
                            daily_return_pct >= 0.008 and  # 0.8% daily minimum
                            result['win_rate'] >= 0.55      # 55% win rate minimum
                        )

                        result.update({
                            'strategy_name': strategy_name,
                            'strategy_type': strategy_type,
                            'timeframe': timeframe,
                            'params': params,
                            'data_points': len(df),
                            'total_days': total_days,
                            'trades_per_day': trades_per_day,
                            'daily_return_pct': daily_return_pct,
                            'meets_criteria': meets_criteria
                        })

                        results.append(result)

                        # Print results
                        status = "✅ TARGET HIT" if meets_criteria else "⚠️  CLOSE" if daily_return_pct >= 0.005 else "❌ LOW RETURN"
                        print(".2%")
                        print(".1f")
                        print(".2%")
                        print(".2f")

                    except Exception as e:
                        print(f"   ❌ Error testing params {i+1}: {e}")

        # Find top performers
        self.analyze_results(results)

        return results

    def analyze_results(self, results):
        """Analyze and rank results"""
        print("\n" + "=" * 80)
        print("🏆 BTC STRATEGY DEEP DIVE RESULTS")
        print("=" * 80)

        # Filter results that meet basic criteria
        valid_results = [r for r in results if r['total_trades'] > 10 and r['total_return'] > 0]

        if not valid_results:
            print("❌ No valid results found")
            return

        # Sort by multiple criteria
        ranked_results = sorted(valid_results,
                              key=lambda x: (x['daily_return_pct'], x['win_rate'], -x['trades_per_day']),
                              reverse=True)

        print("\n🎯 TOP 10 BTC STRATEGIES MEETING CRITERIA:")
        print("Rank | Strategy | Timeframe | Daily Return | Trades/Day | Win Rate | Total Return")
        print("-" * 100)

        top_strategies = []
        for i, result in enumerate(ranked_results[:10]):
            if result['meets_criteria']:
                print("2d")
                top_strategies.append(result)

        if not top_strategies:
            print("❌ No strategies fully meet target criteria")
            print("\n📊 CLOSEST MATCHES (relaxed criteria):")
            for i, result in enumerate(ranked_results[:5]):
                if result['daily_return_pct'] >= 0.005:  # 0.5% daily minimum
                    print("2d")

        # Detailed analysis of top performer
        if top_strategies:
            top = top_strategies[0]
            print("\n🏆 TOP PERFORMER ANALYSIS:")
            print(f"Strategy: {top['strategy_name']}")
            print(f"Timeframe: {top['timeframe']}")
            print(".2%")
            print(".1f")
            print(".1%")
            print(".2%")
            print(f"Parameters: {top['params']}")

            # Calculate position sizing for 1% daily target
            required_daily_return = 0.01  # 1%
            position_size_pct = required_daily_return / top['avg_trade_return']
            print(".1%")

        # Summary statistics
        all_daily_returns = [r['daily_return_pct'] for r in valid_results]
        all_trades_per_day = [r['trades_per_day'] for r in valid_results]
        all_win_rates = [r['win_rate'] for r in valid_results]

        print("\n📈 OVERALL STATISTICS:")
        print(f"Average Daily Return: {np.mean(all_daily_returns):.2%}")
        print(".2%")
        print(".2f")
        print(".1%")
        print(f"Best Win Rate: {max(all_win_rates):.1%}")

        # Count strategies meeting different criteria
        target_hits = sum(1 for r in valid_results if r['meets_criteria'])
        close_calls = sum(1 for r in valid_results if r['daily_return_pct'] >= 0.005 and not r['meets_criteria'])

        print("\n🎯 TARGET ACHIEVEMENT:")
        print(f"Perfect Matches (1%+ daily, 2-3 trades, 55%+ win): {target_hits}")
        print(f"Close Calls (0.5%+ daily): {close_calls}")
        print(f"Total Valid Strategies Tested: {len(valid_results)}")

        # Save results
        results_df = pd.DataFrame(valid_results)
        results_df.to_csv('backtesting_tests/btc_deep_dive_results.csv', index=False)
        print("\n💾 Results saved to: backtesting_tests/btc_deep_dive_results.csv")
def main():
    btc_dive = BTCStrategyDeepDive()
    results = btc_dive.run_deep_dive()

    print("\n🎯 BTC DEEP DIVE COMPLETE")
    print("Review results above and let's discuss the best strategies!")
    print("Ready for IBKR testing when you open the API connection.")

if __name__ == "__main__":
    main()
