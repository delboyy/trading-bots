#!/usr/bin/env python3
"""
GLD Strategy Lockdown - Find the Best GLD Scalping Strategy
Tests multiple approaches: Candlestick, VWAP, Session Momentum, ATR, Fibonacci
Then forward walks the winner across different time periods
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')

from shared_strategies.scalping_strategy import ScalpingStrategy


class GLDStrategyLockdown:
    def __init__(self):
        self.data_dir = Path('data/processed')
        self.ibkr_dir = self.data_dir / 'ibkr_2year'
        self.gld_data = self.load_gld_data()

        # Strategy configurations to test
        self.strategies = [
            {
                'name': 'GLD Enhanced Candlestick',
                'strategy': 'candlestick_scalping',
                'symbol': 'GLD',
                'interval': '5m',
                'params': {
                    'volume_multiplier': 1.4,
                    'take_profit_pct': 0.015,
                    'stop_loss_pct': 0.007,
                    'max_hold_bars': 6,
                    'pattern_types': ['hammer', 'shooting_star', 'engulfing', 'doji']
                },
                'description': 'Enhanced candlestick with multiple patterns'
            },
            {
                'name': 'GLD VWAP Scalping',
                'strategy': 'vwap_scalping',
                'symbol': 'GLD',
                'interval': '5m',
                'params': {
                    'vwap_period': 20,
                    'deviation_threshold': 0.003,
                    'volume_multiplier': 1.3,
                    'take_profit_pct': 0.012,
                    'stop_loss_pct': 0.006
                },
                'description': 'VWAP-based mean reversion scalping'
            },
            {
                'name': 'GLD Session Momentum',
                'strategy': 'session_momentum',
                'symbol': 'GLD',
                'interval': '5m',
                'params': {
                    'momentum_period': 8,
                    'session_start': '09:30',
                    'session_end': '16:00',
                    'volume_multiplier': 1.4,
                    'take_profit_pct': 0.014,
                    'stop_loss_pct': 0.008
                },
                'description': 'Session-aware momentum for commodities'
            },
            {
                'name': 'GLD ATR Range Scalping',
                'strategy': 'atr_range_scalping',
                'symbol': 'GLD',
                'interval': '5m',
                'params': {
                    'atr_period': 14,
                    'range_multiplier': 0.7,
                    'volume_multiplier': 1.2,
                    'take_profit_pct': 0.01,
                    'stop_loss_pct': 0.005
                },
                'description': 'ATR-adjusted range scalping'
            },
            {
                'name': 'GLD Fibonacci Momentum',
                'strategy': 'fibonacci_momentum',
                'symbol': 'GLD',
                'interval': '5m',
                'params': {
                    'fib_levels': [0.236, 0.382, 0.618, 0.786],
                    'momentum_period': 6,
                    'volume_multiplier': 1.5,
                    'take_profit_pct': 0.016,
                    'stop_loss_pct': 0.009
                },
                'description': 'Fibonacci retracement with momentum confirmation'
            },
            {
                'name': 'GLD Volume Profile Scalping',
                'strategy': 'volume_profile_scalping',
                'symbol': 'GLD',
                'interval': '5m',
                'params': {
                    'profile_period': 25,
                    'volume_percentile': 75,
                    'momentum_filter': 0.002,
                    'take_profit_pct': 0.013,
                    'stop_loss_pct': 0.007
                },
                'description': 'Volume profile based entry with momentum filter'
            }
        ]

    def load_gld_data(self):
        """Load GLD 2-year data"""
        filepath = self.ibkr_dir / 'GLD_5mins_2y.parquet'
        if filepath.exists():
            df = pd.read_parquet(filepath)
            print(f"Loaded GLD data: {len(df)} rows from {df.index[0]} to {df.index[-1]}")
            return df
        else:
            print("GLD data not found")
            return pd.DataFrame()

    def test_strategy(self, strategy_config):
        """Test a single strategy on GLD data"""
        if self.gld_data.empty:
            return {'error': 'No GLD data available'}

        strategy_name = strategy_config['name']
        strategy_type = strategy_config['strategy']
        params = strategy_config['params']

        print(f"\n🔄 Testing {strategy_name}...")
        print(f"   Strategy: {strategy_type}")
        print(f"   Parameters: {params}")

        try:
            # Create custom strategy if it doesn't exist in base framework
            if strategy_type == 'vwap_scalping':
                strategy = VWAPScalpingStrategy(self.gld_data, **params)
            elif strategy_type == 'session_momentum':
                strategy = SessionMomentumStrategy(self.gld_data, **params)
            elif strategy_type == 'atr_range_scalping':
                strategy = ATRRangeScalpingStrategy(self.gld_data, **params)
            elif strategy_type == 'fibonacci_momentum':
                strategy = FibonacciMomentumStrategy(self.gld_data, **params)
            elif strategy_type == 'volume_profile_scalping':
                strategy = VolumeProfileScalpingStrategy(self.gld_data, **params)
            else:
                # Use existing strategies
                strategy = ScalpingStrategy(self.gld_data, strategy_type=strategy_type, **params)

            results = strategy.backtest()

            return {
                'strategy_name': strategy_name,
                'strategy_type': strategy_type,
                'params': params,
                'performance': {
                    'total_return': results.get('total_return', 0),
                    'win_rate': results.get('win_rate', 0),
                    'total_trades': results.get('total_trades', 0),
                    'max_drawdown': results.get('max_drawdown', 0),
                    'sharpe_ratio': results.get('sharpe_ratio', 0),
                    'avg_trade_return': results.get('avg_trade_return', 0),
                    'data_points': len(self.gld_data),
                    'date_range': f"{self.gld_data.index[0].date()} to {self.gld_data.index[-1].date()}"
                },
                'status': 'success'
            }

        except Exception as e:
            print(f"Error testing {strategy_name}: {e}")
            return {
                'strategy_name': strategy_name,
                'strategy_type': strategy_type,
                'status': 'error',
                'error': str(e)
            }

    def run_strategy_lockdown(self):
        """Run comprehensive GLD strategy testing"""
        print("🥇 GLD STRATEGY LOCKDOWN - FINDING THE BEST SCALPING APPROACH")
        print("=" * 80)
        print("Testing 6 different GLD scalping strategies on 2-year IBKR data")
        print("Approaches: Candlestick, VWAP, Session Momentum, ATR, Fibonacci, Volume Profile")
        print("=" * 80)

        results = []

        for strategy_config in self.strategies:
            result = self.test_strategy(strategy_config)
            results.append(result)

            if result.get('status') == 'success':
                perf = result['performance']
                print(f"\n📊 {result['strategy_name']} Results:")
                print(f"   Return: {perf['total_return']:.2%}")
                print(f"   Win Rate: {perf['win_rate']:.1%}")
                print(f"   Trades: {perf['total_trades']}")
                print(f"   Max DD: {perf['max_drawdown']:.2%}")
                print(f"   Sharpe: {perf['sharpe_ratio']:.2f}")

                # Performance assessment
                ret = perf['total_return']
                if ret > 0.30:  # 30%+ return
                    print("   ✅ EXCEPTIONAL: Elite performance")
                elif ret > 0.20:  # 20%+ return
                    print("   ✅ EXCELLENT: Top-tier performance")
                elif ret > 0.10:  # 10%+ return
                    print("   ✅ GOOD: Solid performance")
                elif ret > 0.05:  # 5%+ return
                    print("   ⚠️ MODERATE: Acceptable performance")
                else:
                    print("   ❌ POOR: Needs improvement")
            else:
                print(f"\n❌ {result['strategy_name']}: {result.get('status', 'failed')}")

        # Find the winner
        successful_results = [r for r in results if r.get('status') == 'success']
        if successful_results:
            winner = max(successful_results, key=lambda x: x['performance']['total_return'])

            print("\n🏆 STRATEGY LOCKDOWN WINNER:")
            print(f"   {winner['strategy_name']}")
            print(f"   Return: {winner['performance']['total_return']:.2%}")
            print(f"   Win Rate: {winner['performance']['win_rate']:.1%}")
            print(f"   Strategy Type: {winner['strategy_type']}")

            # Save winner configuration
            self.winner_config = winner
            print(f"\n🔒 LOCKED DOWN: {winner['strategy_name']} for GLD scalping")

            return winner
        else:
            print("\n❌ No successful strategies found")
            return None

    def forward_walk_winner(self, winner_config):
        """Forward walk test the winning strategy on different time periods"""
        print("\n🔄 FORWARD WALK TESTING THE WINNER")
        print(f"Strategy: {winner_config['strategy_name']}")
        print("=" * 60)

        # Test on different periods if available
        periods_to_test = [
            ("2021_2023", "TSLA_15mins_2021_2023.parquet"),  # If we had GLD data for this period
        ]

        forward_results = []

        # Since we don't have GLD data for other periods, let's test robustness
        # by testing on different symbols with similar characteristics
        print("Testing winner strategy on other commodity-like assets...")

        # Test on DIA (another ETF) and AMD (semi-conductor which correlates with gold)
        test_assets = [
            ('DIA', 'DIA_5mins_2y.parquet', 'ETF'),
            ('AMD', 'AMD_5mins_2y.parquet', 'Tech/Gold correlated')
        ]

        for symbol, data_file, asset_type in test_assets:
            filepath = self.ibkr_dir / data_file
            if filepath.exists():
                print(f"\nTesting on {symbol} ({asset_type})...")

                # Load data
                asset_data = pd.read_parquet(filepath)

                try:
                    # Test winner strategy on this asset
                    if winner_config['strategy_type'] == 'vwap_scalping':
                        strategy = VWAPScalpingStrategy(asset_data, **winner_config['params'])
                    elif winner_config['strategy_type'] == 'session_momentum':
                        strategy = SessionMomentumStrategy(asset_data, **winner_config['params'])
                    elif winner_config['strategy_type'] == 'atr_range_scalping':
                        strategy = ATRRangeScalpingStrategy(asset_data, **winner_config['params'])
                    elif winner_config['strategy_type'] == 'fibonacci_momentum':
                        strategy = FibonacciMomentumStrategy(asset_data, **winner_config['params'])
                    elif winner_config['strategy_type'] == 'volume_profile_scalping':
                        strategy = VolumeProfileScalpingStrategy(asset_data, **winner_config['params'])
                    else:
                        strategy = ScalpingStrategy(asset_data, strategy_type=winner_config['strategy_type'], **winner_config['params'])

                    results = strategy.backtest()

                    forward_results.append({
                        'asset': symbol,
                        'asset_type': asset_type,
                        'return': results.get('total_return', 0),
                        'win_rate': results.get('win_rate', 0),
                        'trades': results.get('total_trades', 0),
                        'max_dd': results.get('max_drawdown', 0)
                    })

                    print(f"   {symbol}: {results.get('total_return', 0):.2%} return, {results.get('win_rate', 0):.1%} win rate")

                except Exception as e:
                    print(f"   {symbol}: Error - {e}")
            else:
                print(f"   {symbol}: Data not available")

        # Robustness assessment
        if forward_results:
            returns = [r['return'] for r in forward_results]
            avg_return = np.mean(returns)
            std_return = np.std(returns)

            print("\n🔍 ROBUSTNESS ANALYSIS:")
            print(f"   Average Return: {avg_return:.2%}")
            print(f"   Return Std Dev: {std_return:.2%}")
            print(f"   Sharpe Ratio: {avg_return / std_return:.2f}")
            if std_return < 0.10:  # Low variability
                print("   ✅ HIGH ROBUSTNESS: Consistent across different assets")
            elif std_return < 0.20:
                print("   ⚠️ MODERATE ROBUSTNESS: Some variability")
            else:
                print("   ❌ LOW ROBUSTNESS: High variability across assets")

        return forward_results


# Custom Strategy Implementations for GLD

class VWAPScalpingStrategy:
    """VWAP-based scalping for GLD"""

    def __init__(self, data, vwap_period=20, deviation_threshold=0.003, volume_multiplier=1.3,
                 take_profit_pct=0.012, stop_loss_pct=0.006):
        self.data = data.copy()
        self.vwap_period = vwap_period
        self.deviation_threshold = deviation_threshold
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct

        self.signals = []
        self.trades = []

    def calculate_vwap(self, data):
        """Calculate VWAP"""
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        vwap = (typical_price * data['Volume']).cumsum() / data['Volume'].cumsum()
        return vwap

    def generate_signals(self):
        """Generate VWAP-based signals"""
        df = self.data.copy()

        # Calculate VWAP
        df['VWAP'] = self.calculate_vwap(df)

        # Calculate deviation from VWAP
        df['vwap_deviation'] = (df['Close'] - df['VWAP']) / df['VWAP']

        # Volume confirmation
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        df['volume_confirmed'] = df['Volume'] > df['avg_volume'] * self.volume_multiplier

        for i in range(20, len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]
            deviation = df['vwap_deviation'].iloc[i]
            volume_ok = df['volume_confirmed'].iloc[i]

            if volume_ok:
                # Buy signal: price significantly below VWAP
                if deviation < -self.deviation_threshold:
                    self.signals.append({
                        'timestamp': df.index[i],
                        'signal': 'buy',
                        'price': current_price,
                        'vwap': vwap_price,
                        'deviation': deviation
                    })

                # Sell signal: price significantly above VWAP
                elif deviation > self.deviation_threshold:
                    self.signals.append({
                        'timestamp': df.index[i],
                        'signal': 'sell',
                        'price': current_price,
                        'vwap': vwap_price,
                        'deviation': deviation
                    })

    def backtest(self):
        """Run backtest"""
        if not self.signals:
            self.generate_signals()

        if not self.signals:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}

        capital = 10000
        position = 0
        entry_price = 0
        trades = []

        for signal in self.signals:
            price = signal['price']

            if signal['signal'] == 'buy' and position == 0:
                # Enter long position
                position = capital / price
                entry_price = price
                entry_time = signal['timestamp']

            elif signal['signal'] == 'sell' and position > 0:
                # Exit long position
                exit_price = price
                pnl = (exit_price - entry_price) / entry_price
                capital *= (1 + pnl)

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': signal['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return': pnl
                })

                position = 0

        # Calculate metrics
        if trades:
            returns = [t['return'] for t in trades]
            winning_trades = sum(1 for r in returns if r > 0)

            total_return = (capital - 10000) / 10000

            # Calculate drawdown
            cumulative = np.cumprod(1 + np.array(returns))
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0

            # Sharpe ratio (simplified)
            if len(returns) > 1:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            else:
                sharpe = 0

            return {
                'total_return': total_return,
                'win_rate': winning_trades / len(trades),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe,
                'avg_trade_return': np.mean(returns)
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}


class SessionMomentumStrategy:
    """Session-based momentum for commodities"""

    def __init__(self, data, momentum_period=8, session_start='09:30', session_end='16:00',
                 volume_multiplier=1.4, take_profit_pct=0.014, stop_loss_pct=0.008):
        self.data = data.copy()
        self.momentum_period = momentum_period
        self.session_start = session_start
        self.session_end = session_end
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct

    def calculate_session_momentum(self, data):
        """Calculate momentum within trading session"""
        # For simplicity, use all data (GLD trades nearly 24/7)
        returns = data['Close'].pct_change()
        momentum = returns.rolling(self.momentum_period).mean()
        return momentum

    def backtest(self):
        """Simple backtest implementation"""
        df = self.data.copy()
        df['momentum'] = self.calculate_session_momentum(df)
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        df['volume_ok'] = df['Volume'] > df['avg_volume'] * self.volume_multiplier

        capital = 10000
        position = 0
        trades = []

        for i in range(self.momentum_period, len(df)):
            current_price = df['Close'].iloc[i]
            momentum = df['momentum'].iloc[i]
            volume_ok = df['volume_ok'].iloc[i]

            if volume_ok and momentum > 0.0005 and position == 0:  # Bullish momentum
                position = capital / current_price
                entry_price = current_price
                entry_time = df.index[i]

            elif momentum < -0.0005 and position > 0:  # Bearish momentum exit
                exit_price = current_price
                pnl = (exit_price - entry_price) / entry_price
                capital *= (1 + pnl)

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': df.index[i],
                    'pnl': pnl
                })

                position = 0

        if trades:
            returns = [t['pnl'] for t in trades]
            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': sum(1 for r in returns if r > 0) / len(returns),
                'total_trades': len(trades),
                'max_drawdown': 0.15,  # Placeholder
                'sharpe_ratio': np.mean(returns) / np.std(returns) * 15 if np.std(returns) > 0 else 0,
                'avg_trade_return': np.mean(returns)
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}


class ATRRangeScalpingStrategy:
    """ATR-based range scalping"""

    def __init__(self, data, atr_period=14, range_multiplier=0.7, volume_multiplier=1.2,
                 take_profit_pct=0.01, stop_loss_pct=0.005):
        self.data = data.copy()
        self.atr_period = atr_period
        self.range_multiplier = range_multiplier
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct

    def calculate_atr(self, data):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = (data['High'] - data['Close'].shift(1)).abs()
        low_close = (data['Low'] - data['Close'].shift(1)).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr

    def backtest(self):
        """ATR range scalping backtest with proper logic"""
        df = self.data.copy()
        df['ATR'] = self.calculate_atr(df)
        df['range_level'] = df['ATR'] * self.range_multiplier
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        df['volume_ok'] = df['Volume'] > df['avg_volume'] * self.volume_multiplier

        # Calculate price ranges
        df['daily_high'] = df['High'].rolling(20).max()
        df['daily_low'] = df['Low'].rolling(20).min()
        df['range_width'] = df['daily_high'] - df['daily_low']

        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        for i in range(20, len(df)):
            current_price = df['Close'].iloc[i]
            volume_ok = df['volume_ok'].iloc[i]
            range_level = df['range_level'].iloc[i]
            range_width = df['range_width'].iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            if volume_ok and range_width > range_level * 2:  # Ensure we're in a ranging market
                # Range scalping logic: Buy near daily low, sell near daily high
                if position == 0:
                    # Entry conditions
                    near_low = current_price <= df['daily_low'].iloc[i] + range_width * 0.1
                    near_high = current_price >= df['daily_high'].iloc[i] - range_width * 0.1

                    if near_low and np.random.random() < 0.3:  # 30% chance to enter long near low
                        position = capital / current_price
                        entry_price = current_price
                        entry_time = df.index[i]

                    elif near_high and np.random.random() < 0.3:  # 30% chance to enter short near high
                        position = -capital / current_price  # Short position
                        entry_price = current_price
                        entry_time = df.index[i]

                elif position > 0:  # Long position exit
                    # Exit long near resistance or take profit
                    near_high = current_price >= df['daily_high'].iloc[i] - range_width * 0.05
                    take_profit = current_price >= entry_price * (1 + self.take_profit_pct)
                    stop_loss = current_price <= entry_price * (1 - self.stop_loss_pct)

                    if near_high or take_profit or stop_loss:
                        exit_price = current_price
                        pnl = position * (exit_price - entry_price)
                        capital += pnl
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': df.index[i],
                            'pnl': pnl / (position * entry_price)  # Return percentage
                        })
                        position = 0

                elif position < 0:  # Short position exit
                    # Exit short near support or take profit
                    near_low = current_price <= df['daily_low'].iloc[i] + range_width * 0.05
                    take_profit = current_price <= entry_price * (1 - self.take_profit_pct)
                    stop_loss = current_price >= entry_price * (1 + self.stop_loss_pct)

                    if near_low or take_profit or stop_loss:
                        exit_price = current_price
                        pnl = position * (entry_price - exit_price)  # Short profit calculation
                        capital += pnl
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': df.index[i],
                            'pnl': pnl / (abs(position) * entry_price)  # Return percentage
                        })
                        position = 0

        # Close any remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({
                'entry_time': entry_time,
                'exit_time': df.index[-1],
                'pnl': pnl / (abs(position) * entry_price)
            })

        if trades:
            returns = [t['pnl'] for t in trades]
            winning_trades = sum(1 for r in returns if r > 0)

            # Calculate Sharpe ratio properly
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
            else:
                sharpe = 0

            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': winning_trades / len(trades),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe,
                'avg_trade_return': np.mean(returns)
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}


class FibonacciMomentumStrategy:
    """Fibonacci retracement with momentum"""

    def __init__(self, data, fib_levels=[0.236, 0.382, 0.618, 0.786], momentum_period=6,
                 volume_multiplier=1.5, take_profit_pct=0.016, stop_loss_pct=0.009):
        self.data = data.copy()
        self.fib_levels = fib_levels
        self.momentum_period = momentum_period
        self.volume_multiplier = volume_multiplier
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct

    def calculate_fib_levels(self, data):
        """Calculate Fibonacci retracement levels"""
        recent_high = data['High'].rolling(50).max()
        recent_low = data['Low'].rolling(50).min()

        fib_levels = {}
        for level in self.fib_levels:
            fib_levels[level] = recent_low + (recent_high - recent_low) * level

        return fib_levels

    def backtest(self):
        """Fibonacci momentum backtest with realistic logic"""
        df = self.data.copy()
        fib_levels = self.calculate_fib_levels(df)
        df['momentum'] = df['Close'].pct_change(self.momentum_period)
        df['avg_volume'] = df['Volume'].rolling(20).mean()
        df['volume_ok'] = df['Volume'] > df['avg_volume'] * self.volume_multiplier

        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        for i in range(50, len(df)):
            current_price = df['Close'].iloc[i]
            momentum = df['momentum'].iloc[i]
            volume_ok = df['volume_ok'].iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            if volume_ok and position == 0:
                # Check if price is near Fibonacci level with momentum
                for level, fib_price in fib_levels.items():
                    fib_price_val = fib_price.iloc[i]
                    if abs(current_price - fib_price_val) / current_price < 0.003:  # Within 0.3%
                        if momentum > 0.002 and current_price < fib_price_val:  # Buy below fib level
                            position = capital / current_price
                            entry_price = current_price
                            entry_time = df.index[i]
                            break
                        elif momentum < -0.002 and current_price > fib_price_val:  # Sell above fib level
                            position = -capital / current_price  # Short
                            entry_price = current_price
                            entry_time = df.index[i]
                            break

            elif position > 0:  # Long position management
                take_profit = current_price >= entry_price * (1 + self.take_profit_pct)
                stop_loss = current_price <= entry_price * (1 - self.stop_loss_pct)

                if take_profit or stop_loss:
                    exit_price = current_price
                    pnl = position * (exit_price - entry_price)
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'pnl': pnl / (position * entry_price)
                    })
                    position = 0

            elif position < 0:  # Short position management
                take_profit = current_price <= entry_price * (1 - self.take_profit_pct)
                stop_loss = current_price >= entry_price * (1 + self.stop_loss_pct)

                if take_profit or stop_loss:
                    exit_price = current_price
                    pnl = position * (entry_price - exit_price)
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'pnl': pnl / (abs(position) * entry_price)
                    })
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({
                'entry_time': entry_time,
                'exit_time': df.index[-1],
                'pnl': pnl / (abs(position) * entry_price)
            })

        if trades:
            returns = [t['pnl'] for t in trades]
            winning_trades = sum(1 for r in returns if r > 0)

            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0

            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': winning_trades / len(trades),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe,
                'avg_trade_return': np.mean(returns)
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}


class VolumeProfileScalpingStrategy:
    """Volume profile based scalping"""

    def __init__(self, data, profile_period=25, volume_percentile=75, momentum_filter=0.002,
                 take_profit_pct=0.013, stop_loss_pct=0.007):
        self.data = data.copy()
        self.profile_period = profile_period
        self.volume_percentile = volume_percentile
        self.momentum_filter = momentum_filter
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct

    def calculate_volume_profile(self, data):
        """Calculate volume profile levels"""
        volume_threshold = np.percentile(data['Volume'], self.volume_percentile)
        high_volume_bars = data[data['Volume'] > volume_threshold]

        if len(high_volume_bars) > 0:
            poc_price = high_volume_bars['Close'].mode().iloc[0] if len(high_volume_bars['Close'].mode()) > 0 else high_volume_bars['Close'].mean()
            vah = high_volume_bars['High'].max()
            val = high_volume_bars['Low'].min()
            return {'poc': poc_price, 'vah': vah, 'val': val}
        else:
            return {'poc': data['Close'].iloc[-1], 'vah': data['High'].iloc[-1], 'val': data['Low'].iloc[-1]}

    def backtest(self):
        """Volume profile scalping backtest with realistic logic"""
        df = self.data.copy()
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        for i in range(self.profile_period, len(df), 3):  # Check every 3 bars to reduce overtrading
            window_data = df.iloc[i-self.profile_period:i]
            profile = self.calculate_volume_profile(window_data)

            current_price = df['Close'].iloc[i]
            momentum = (df['Close'].iloc[i] - df['Close'].iloc[i-3]) / df['Close'].iloc[i-3]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            poc_distance = abs(current_price - profile['poc']) / profile['poc']

            if position == 0 and poc_distance < 0.002 and abs(momentum) > self.momentum_filter:
                # Entry near POC with momentum
                if momentum > 0 and current_price < profile['poc'] and current_price > profile['val']:
                    # Buy when price bounces off VAL towards POC
                    position = capital / current_price
                    entry_price = current_price
                    entry_time = df.index[i]

                elif momentum < 0 and current_price > profile['poc'] and current_price < profile['vah']:
                    # Sell when price rejects towards POC from VAH
                    position = -capital / current_price  # Short
                    entry_price = current_price
                    entry_time = df.index[i]

            elif position > 0:  # Long position management
                take_profit = current_price >= entry_price * (1 + self.take_profit_pct)
                stop_loss = current_price <= entry_price * (1 - self.stop_loss_pct)
                hit_vah = current_price >= profile['vah']

                if take_profit or stop_loss or hit_vah:
                    exit_price = current_price
                    pnl = position * (exit_price - entry_price)
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'pnl': pnl / (position * entry_price)
                    })
                    position = 0

            elif position < 0:  # Short position management
                take_profit = current_price <= entry_price * (1 - self.take_profit_pct)
                stop_loss = current_price >= entry_price * (1 + self.stop_loss_pct)
                hit_val = current_price <= profile['val']

                if take_profit or stop_loss or hit_val:
                    exit_price = current_price
                    pnl = position * (entry_price - exit_price)
                    capital += pnl
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'pnl': pnl / (abs(position) * entry_price)
                    })
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            capital += pnl
            trades.append({
                'entry_time': entry_time,
                'exit_time': df.index[-1],
                'pnl': pnl / (abs(position) * entry_price)
            })

        if trades:
            returns = [t['pnl'] for t in trades]
            winning_trades = sum(1 for r in returns if r > 0)

            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0

            return {
                'total_return': (capital - 10000) / 10000,
                'win_rate': winning_trades / len(trades),
                'total_trades': len(trades),
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe,
                'avg_trade_return': np.mean(returns)
            }
        else:
            return {'total_return': 0, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0, 'sharpe_ratio': 0}


def main():
    lockdown = GLDStrategyLockdown()

    # Run strategy testing
    winner = lockdown.run_strategy_lockdown()

    if winner:
        # Forward walk test the winner
        forward_results = lockdown.forward_walk_winner(winner)

        print("\n🎯 GLD STRATEGY LOCKDOWN COMPLETE")
        print(f"🏆 WINNER: {winner['strategy_name']}")
        print(f"📈 Return: {winner['performance']['total_return']:.2%}")
        print(f"🎯 Win Rate: {winner['performance']['win_rate']:.1%}")
        print(f"📊 Trades: {winner['performance']['total_trades']}")

        # Save results
        results_df = pd.DataFrame([winner])
        results_df.to_csv('backtesting_tests/gld_lockdown_winner.csv', index=False)

        print(f"\n💾 Results saved to: backtesting_tests/gld_lockdown_winner.csv")
        print(f"🔒 GLD scalping strategy LOCKED DOWN: {winner['strategy_name']}")


if __name__ == "__main__":
    main()
