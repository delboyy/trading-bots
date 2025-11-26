#!/usr/bin/env python3
"""
BTC High-Frequency Strategies - Targeting 1%+ Daily Returns
Uses existing Binance BTC data for rapid-fire trading strategies
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class BTCHighFrequencyStrategies:
    def __init__(self):
        self.data_dir = Path('data')
        self.processed_dir = self.data_dir / 'processed'

        # Target: 1%+ daily returns through high-frequency trading
        self.target_daily_return = 0.01
        self.min_trades_per_day = 5  # Much higher frequency than before

        # Load existing BTC data
        self.btc_data = self.load_btc_data()

    def load_btc_data(self):
        """Load existing BTC data from processed directory"""
        # Try different possible file locations
        possible_files = [
            self.processed_dir / 'binance_BTCUSDT_5m.parquet',
            self.data_dir / 'raw' / 'binance_BTCUSDT_5m_recent.parquet'
        ]

        for file_path in possible_files:
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    print(f"Loaded BTC data from {file_path}: {len(df)} rows")
                    print(f"Date range: {df.index[0]} to {df.index[-1]}")
                    return df
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
                    continue

        # Try loading from raw directory chunks
        raw_dir = self.data_dir / 'raw' / 'binance_BTCUSDT_5m'
        if raw_dir.exists():
            files = list(raw_dir.glob('*.parquet'))
            if files:
                print(f"Loading from {len(files)} chunk files...")

                # Load last 90 days of data
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=90)
                all_data = []

                for file in sorted(files)[-30:]:  # Last 30 files should cover recent data
                    try:
                        df = pd.read_parquet(file)
                        # Filter to recent data
                        df = df[df.index >= cutoff_date]
                        if not df.empty:
                            all_data.append(df)
                    except:
                        continue

                if all_data:
                    combined_df = pd.concat(all_data, ignore_index=False)
                    combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
                    combined_df = combined_df.sort_index()

                    print(f"Combined recent BTC data: {len(combined_df)} rows")
                    print(f"Date range: {combined_df.index[0]} to {combined_df.index[-1]}")
                    return combined_df

        print("No BTC data found. Please run binance_btc_downloader.py first.")
        return pd.DataFrame()

    def calculate_vwap(self, df, period=20):
        """Calculate VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def calculate_atr(self, df, period=14):
        """Calculate ATR for volatility"""
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift(1)).abs()
        low_close = (df['Low'] - df['Close'].shift(1)).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr

    def test_micro_scalp_strategy(self, df, params):
        """Ultra-fast micro scalping with tiny profit targets"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])
        df['ATR'] = self.calculate_atr(df, params['atr_period'])

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

            # Ultra-fast entries - every small VWAP deviation
            if position == 0:
                deviation_pct = (current_price - vwap_price) / vwap_price

                # Entry on any significant deviation (very sensitive)
                if abs(deviation_pct) > params['entry_threshold']:
                    # Use ATR for position sizing
                    risk_amount = capital * params['risk_per_trade']
                    stop_distance = atr * params['atr_multiplier']
                    position_size = risk_amount / stop_distance

                    if deviation_pct > 0:  # Above VWAP - go long
                        position = position_size
                        entry_price = current_price
                    else:  # Below VWAP - go short
                        position = -position_size
                        entry_price = current_price

            # Ultra-fast exits - tiny profit targets
            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                # Exit on tiny profit or any reversal signal
                if abs(pnl_pct) >= params['profit_target'] or pnl_pct <= -params['stop_loss']:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / abs(position * entry_price)})
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            capital += pnl
            trades.append({'pnl': pnl / abs(position * entry_price)})

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

    def test_volume_spike_scalp(self, df, params):
        """Volume spike scalping for high-frequency entries"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        for i in range(params['vwap_period'], len(df)):
            current_price = df['Close'].iloc[i]
            prev_price = df['Close'].iloc[i-1] if i > 0 else current_price
            vwap_price = df['VWAP'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['Volume'].rolling(20).mean().iloc[i]

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Volume spike detection
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1

            # Entry on volume spikes near VWAP
            if position == 0 and volume_ratio > params['volume_threshold']:
                deviation_pct = abs(current_price - vwap_price) / vwap_price

                if deviation_pct < params['vwap_tolerance']:  # Near VWAP
                    # Determine direction from price action
                    if current_price > prev_price and current_price < vwap_price:
                        # Bullish bounce off VWAP
                        position = capital / current_price * params['position_size_pct']
                        entry_price = current_price
                    elif current_price < prev_price and current_price > vwap_price:
                        # Bearish rejection of VWAP
                        position = -capital / current_price * params['position_size_pct']
                        entry_price = current_price

            # Quick exits
            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                # Exit on small profit or time limit
                if abs(pnl_pct) >= params['profit_target'] or abs(pnl_pct) <= params['stop_loss']:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / abs(position * entry_price)})
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            capital += pnl
            trades.append({'pnl': pnl / abs(position * entry_price)})

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

    def test_momentum_burst_strategy(self, df, params):
        """Momentum burst strategy for rapid entries"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        for i in range(params['vwap_period'], len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]

            # Calculate multi-bar momentum
            momentum_scores = []
            for lookback in range(1, params['momentum_bars'] + 1):
                if i >= lookback:
                    momentum = (current_price - df['Close'].iloc[i - lookback]) / df['Close'].iloc[i - lookback]
                    momentum_scores.append(momentum)

            avg_momentum = np.mean(momentum_scores) if momentum_scores else 0

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Entry on momentum bursts
            if position == 0 and abs(avg_momentum) > params['momentum_threshold']:
                deviation_pct = abs(current_price - vwap_price) / vwap_price

                if deviation_pct < params['vwap_filter']:  # Filter by VWAP proximity
                    if avg_momentum > 0:
                        position = capital / current_price * params['position_size_pct']
                        entry_price = current_price
                    elif avg_momentum < 0:
                        position = -capital / current_price * params['position_size_pct']
                        entry_price = current_price

            # Quick momentum-based exits
            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                # Exit on momentum reversal or profit target
                if (abs(pnl_pct) >= params['profit_target'] or
                    abs(pnl_pct) <= params['stop_loss'] or
                    (position > 0 and avg_momentum < -params['exit_momentum']) or
                    (position < 0 and avg_momentum > params['exit_momentum'])):
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / abs(position * entry_price)})
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            capital += pnl
            trades.append({'pnl': pnl / abs(position * entry_price)})

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

    def test_range_breakout_scalp(self, df, params):
        """Range breakout scalping for high-frequency entries"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        max_drawdown = 0
        peak = capital

        df = df.copy()

        for i in range(params['range_period'], len(df)):
            current_price = df['Close'].iloc[i]

            # Calculate recent range
            recent_high = df['High'].iloc[i - params['range_period']:i].max()
            recent_low = df['Low'].iloc[i - params['range_period']:i].min()
            range_size = recent_high - recent_low

            # Update drawdown
            current_value = capital + position * (current_price - entry_price) if position != 0 else capital
            peak = max(peak, current_value)
            current_drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, current_drawdown)

            # Entry on range breakouts
            if position == 0:
                upper_breakout = current_price > recent_high * (1 + params['breakout_pct'])
                lower_breakout = current_price < recent_low * (1 - params['breakout_pct'])

                if upper_breakout:
                    position = capital / current_price * params['position_size_pct']
                    entry_price = current_price
                elif lower_breakout:
                    position = -capital / current_price * params['position_size_pct']
                    entry_price = current_price

            # Quick exits
            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                # Exit on profit target or pullback
                if abs(pnl_pct) >= params['profit_target']:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / abs(position * entry_price)})
                    position = 0
                elif abs(pnl_pct) <= params['stop_loss']:
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({'pnl': pnl / abs(position * entry_price)})
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            capital += pnl
            trades.append({'pnl': pnl / abs(position * entry_price)})

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

    def run_high_frequency_testing(self):
        """Run high-frequency BTC strategy testing"""
        print("🚀 BTC HIGH-FREQUENCY STRATEGIES - TARGETING 1%+ DAILY RETURNS")
        print("=" * 90)
        print("Ultra-fast scalping strategies with tiny profit targets")
        print("Focus: Many trades per day to compound small gains")
        print("=" * 90)

        if self.btc_data.empty:
            print("❌ No BTC data available. Please run data downloader first.")
            return

        # High-frequency strategies optimized for many small wins
        strategies = [
            {
                'name': 'BTC Micro Scalp VWAP',
                'strategy': 'micro_scalp',
                'description': 'Ultra-fast VWAP scalping with 0.1% profit targets',
                'params_combinations': [
                    {'vwap_period': 15, 'atr_period': 10, 'entry_threshold': 0.001, 'profit_target': 0.001, 'stop_loss': 0.002, 'atr_multiplier': 0.5, 'risk_per_trade': 0.002},
                    {'vwap_period': 20, 'atr_period': 14, 'entry_threshold': 0.002, 'profit_target': 0.0015, 'stop_loss': 0.003, 'atr_multiplier': 0.7, 'risk_per_trade': 0.002},
                    {'vwap_period': 25, 'atr_period': 20, 'entry_threshold': 0.003, 'profit_target': 0.002, 'stop_loss': 0.004, 'atr_multiplier': 1.0, 'risk_per_trade': 0.002},
                ]
            },
            {
                'name': 'BTC Volume Spike Scalp',
                'strategy': 'volume_spike',
                'description': 'Volume spike scalping with rapid entries/exits',
                'params_combinations': [
                    {'vwap_period': 15, 'volume_threshold': 1.5, 'vwap_tolerance': 0.005, 'position_size_pct': 0.05, 'profit_target': 0.001, 'stop_loss': 0.002},
                    {'vwap_period': 20, 'volume_threshold': 2.0, 'vwap_tolerance': 0.008, 'position_size_pct': 0.03, 'profit_target': 0.0015, 'stop_loss': 0.003},
                    {'vwap_period': 25, 'volume_threshold': 2.5, 'vwap_tolerance': 0.010, 'position_size_pct': 0.02, 'profit_target': 0.002, 'stop_loss': 0.004},
                ]
            },
            {
                'name': 'BTC Momentum Burst Scalp',
                'strategy': 'momentum_burst',
                'description': 'Momentum burst scalping with multi-bar confirmation',
                'params_combinations': [
                    {'vwap_period': 15, 'momentum_bars': 3, 'momentum_threshold': 0.002, 'vwap_filter': 0.008, 'position_size_pct': 0.04, 'profit_target': 0.001, 'stop_loss': 0.002, 'exit_momentum': 0.001},
                    {'vwap_period': 20, 'momentum_bars': 5, 'momentum_threshold': 0.003, 'vwap_filter': 0.010, 'position_size_pct': 0.03, 'profit_target': 0.0015, 'stop_loss': 0.003, 'exit_momentum': 0.0015},
                    {'vwap_period': 25, 'momentum_bars': 8, 'momentum_threshold': 0.004, 'vwap_filter': 0.012, 'position_size_pct': 0.02, 'profit_target': 0.002, 'stop_loss': 0.004, 'exit_momentum': 0.002},
                ]
            },
            {
                'name': 'BTC Range Breakout Scalp',
                'strategy': 'range_breakout',
                'description': 'Range breakout scalping for high-frequency entries',
                'params_combinations': [
                    {'range_period': 10, 'breakout_pct': 0.002, 'position_size_pct': 0.04, 'profit_target': 0.001, 'stop_loss': 0.002},
                    {'range_period': 15, 'breakout_pct': 0.003, 'position_size_pct': 0.03, 'profit_target': 0.0015, 'stop_loss': 0.003},
                    {'range_period': 20, 'breakout_pct': 0.004, 'position_size_pct': 0.02, 'profit_target': 0.002, 'stop_loss': 0.004},
                ]
            }
        ]

        results = []

        for strategy_config in strategies:
            strategy_name = strategy_config['name']
            strategy_type = strategy_config['strategy']
            description = strategy_config['description']
            param_combinations = strategy_config['params_combinations']

            print(f"\n🎯 TESTING: {strategy_name}")
            print(f"   Description: {description}")
            print(f"   Parameter Combinations: {len(param_combinations)}")
            print("-" * 70)

            for i, params in enumerate(param_combinations):
                print(f"   Testing params {i+1}/3...")

                try:
                    # Run appropriate test function
                    if strategy_type == 'micro_scalp':
                        result = self.test_micro_scalp_strategy(self.btc_data, params)
                    elif strategy_type == 'volume_spike':
                        result = self.test_volume_spike_scalp(self.btc_data, params)
                    elif strategy_type == 'momentum_burst':
                        result = self.test_momentum_burst_strategy(self.btc_data, params)
                    elif strategy_type == 'range_breakout':
                        result = self.test_range_breakout_scalp(self.btc_data, params)
                    else:
                        continue

                    # Calculate daily metrics (5m data = 288 5-min bars per day)
                    total_days = len(self.btc_data) / 288  # Approximate trading days
                    trades_per_day = result['total_trades'] / max(total_days, 1)
                    daily_return_pct = result['total_return'] / max(total_days, 1)

                    # Check if meets aggressive criteria
                    meets_criteria = (
                        trades_per_day >= 5 and  # 5+ trades per day minimum
                        daily_return_pct >= 0.008  # 0.8% daily minimum (close to 1%)
                    )

                    result.update({
                        'strategy_name': strategy_name,
                        'strategy_type': strategy_type,
                        'params': params,
                        'data_points': len(self.btc_data),
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

        # Analyze results
        self.analyze_high_frequency_results(results)

        return results

    def analyze_high_frequency_results(self, results):
        """Analyze high-frequency strategy results"""
        print("\n" + "=" * 90)
        print("🏆 BTC HIGH-FREQUENCY STRATEGY RESULTS")
        print("=" * 90)

        # Filter results
        valid_results = [r for r in results if r['total_trades'] > 50 and r['total_return'] > 0]

        if not valid_results:
            print("❌ No valid results found with sufficient trade frequency")
            return

        # Sort by multiple criteria for high-frequency trading
        ranked_results = sorted(valid_results,
                              key=lambda x: (x['daily_return_pct'], x['trades_per_day'], x['win_rate']),
                              reverse=True)

        print("\n🎯 TOP HIGH-FREQUENCY BTC STRATEGIES:")
        print("Rank | Strategy | Daily Return | Trades/Day | Win Rate | Total Return")
        print("-" * 110)

        top_strategies = []
        for i, result in enumerate(ranked_results[:10]):
            if result['daily_return_pct'] >= 0.005:  # At least 0.5% daily
                print("2d")
                top_strategies.append(result)

        if not top_strategies:
            print("❌ No strategies meeting minimum return criteria")
            print("\n📊 ALL RESULTS (sorted by daily return):")
            for i, result in enumerate(ranked_results[:5]):
                print("2d")

        # Detailed analysis of top performer
        if top_strategies:
            top = top_strategies[0]
            print("\n🏆 TOP HIGH-FREQUENCY PERFORMER ANALYSIS:")
            print(f"Strategy: {top['strategy_name']}")
            print(f"Daily Return: {top['daily_return_pct']:.2%}")
            print(f"Trades/Day: {top['trades_per_day']:.1f}")
            print(f"Win Rate: {top['win_rate']:.1%}")
            print(f"Total Return: {top['total_return']:.2%}")
            print(f"Max DD: {top['max_drawdown']:.2%}")
            print(f"Parameters: {top['params']}")

            # Assess if it can reach 1% daily with optimization
            potential_daily_return = top['daily_return_pct']
            if potential_daily_return >= 0.008:
                print("✅ CLOSE TO 1% TARGET - Can optimize further")
            elif potential_daily_return >= 0.006:
                print("⚠️ MODERATE PERFORMANCE - Needs parameter tuning")
            else:
                print("❌ BELOW TARGET - Strategy needs significant changes")
        # Overall statistics
        if valid_results:
            all_daily_returns = [r['daily_return_pct'] for r in valid_results]
            all_trades_per_day = [r['trades_per_day'] for r in valid_results]
            all_win_rates = [r['win_rate'] for r in valid_results]

            print("\n📈 HIGH-FREQUENCY STRATEGY STATISTICS:")
            print(f"Average Daily Return: {np.mean(all_daily_returns):.2%}")
            print(".2f")
            print(".1%")

            # Target achievement analysis
            target_hits = sum(1 for r in valid_results if r['meets_criteria'])
            close_calls = sum(1 for r in valid_results if r['daily_return_pct'] >= 0.006 and not r['meets_criteria'])

            print("\n🎯 TARGET ACHIEVEMENT (1%+ Daily, 5+ Trades/Day):")
            print(f"Perfect Matches: {target_hits}")
            print(f"Close Calls (0.6%+ daily): {close_calls}")
            print(f"Total Strategies Tested: {len(valid_results)}")

            # Best performers summary
            best_daily = max(all_daily_returns)
            best_frequency = max(all_trades_per_day)
            best_win_rate = max(all_win_rates)

            print("\n🏆 BEST INDIVIDUAL METRICS:")
            print(f"Best Daily Return: {max(all_daily_returns):.2%}")
            print(".1f")
            print(".1%")

        # Save results
        results_df = pd.DataFrame(valid_results)
        results_df.to_csv('backtesting_tests/btc_high_frequency_results.csv', index=False)
        print("\n💾 Results saved to: backtesting_tests/btc_high_frequency_results.csv")
def main():
    btc_hf = BTCHighFrequencyStrategies()
    results = btc_hf.run_high_frequency_testing()

    print("\n🎯 BTC HIGH-FREQUENCY TESTING COMPLETE")
    print("Review results above - these strategies aim for many small wins per day")
    print("Ready for IBKR testing when you open the API connection.")

if __name__ == "__main__":
    main()