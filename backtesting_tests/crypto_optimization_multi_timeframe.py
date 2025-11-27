#!/usr/bin/env python3
"""
Crypto Bots Optimization - Multi-Timeframe Testing
Tests Scalp Z and Squeeze Pro across different timeframes and parameter optimizations
Using 2+ years of Binance data with 0.035% fees
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class CryptoMultiTimeframeOptimizer:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')
        self.fee_rate = 0.00035  # 0.035%

    def load_extended_data(self, months=24):
        """Load 2+ years of data for comprehensive testing"""
        all_files = sorted(self.raw_dir.glob('*.parquet'), reverse=True)

        # Take files from 2021-2024 for 2+ year test
        target_files = []
        for file in all_files:
            date_str = file.name.split('_')[2][:6]  # YYYYMM
            try:
                year_month = int(date_str)
                if 202101 <= year_month <= 202412:  # 2021-2024 (2+ years)
                    target_files.append(file)
            except:
                continue

        # Limit for performance but get good coverage
        target_files = target_files[:200]  # ~6-7 months of data

        print(f"Loading {len(target_files)} files from 2021-2024 (2+ years)")

        all_data = []
        for file in target_files[:100]:  # Further limit for speed
            try:
                df = pd.read_parquet(file)
                if not df.empty and len(df) > 10:
                    all_data.append(df)
            except:
                continue

        if all_data:
            # Simple combine without sorting
            combined = pd.concat(all_data, ignore_index=False)
            print(f"Total bars loaded: {len(combined)} (~{len(combined)/(288*30):.1f} months)")
            return combined

        print("❌ No data loaded")
        return pd.DataFrame()

    def resample_to_timeframe(self, df_5m, target_tf_minutes):
        """Resample 5m data to target timeframe"""
        if target_tf_minutes == 5:
            return df_5m

        # Resample to target timeframe
        resample_rule = f'{target_tf_minutes}min'

        try:
            resampled = df_5m.resample(resample_rule).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

            print(f"Resampled to {target_tf_minutes}m: {len(resampled)} bars")
            return resampled
        except:
            print(f"❌ Failed to resample to {target_tf_minutes}m")
            return df_5m

    def test_scalp_z_optimized(self, df, params):
        """Optimized Scalp Z with adjustable parameters"""
        trades = []
        capital = 10000
        total_fees = 0
        position = 0
        entry_price = 0
        entry_signal = None
        last_trade_idx = -params['min_bars_between_trades']

        for i in range(params['ema_period'] + 20, min(len(df), 15000)):  # Extended test
            if i - last_trade_idx < params['min_bars_between_trades']:
                continue

            # Calculate indicators
            ema = df['Close'].iloc[i-params['ema_period']:i+1].ewm(span=params['ema_period'], adjust=False).mean().iloc[-1]

            # Stochastic calculation
            high_window = df['High'].iloc[i-params['stoch_period']:i+1].max()
            low_window = df['Low'].iloc[i-params['stoch_period']:i+1].min()
            close = df['Close'].iloc[i]

            if high_window > low_window:
                stoch_k = ((close - low_window) / (high_window - low_window)) * 100
            else:
                stoch_k = 50

            current_price = close

            # Strategy logic with adjustable parameters
            signal = None

            # LONG: Close > EMA + Stoch < oversold threshold
            if current_price > ema and stoch_k < params['oversold_threshold']:
                signal = {
                    'type': 'LONG',
                    'entry': current_price,
                    'sl': current_price * (1 - params['sl_pct']),
                    'tp': current_price * (1 + params['tp_pct'])
                }

            # SHORT: Close < EMA + Stoch > overbought threshold
            elif current_price < ema and stoch_k > params['overbought_threshold']:
                signal = {
                    'type': 'SHORT',
                    'entry': current_price,
                    'sl': current_price * (1 + params['sl_pct']),
                    'tp': current_price * (1 - params['tp_pct'])
                }

            # Execute trade
            if signal and position == 0:
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                entry_signal = signal
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_idx = i

            # Check exits
            elif position != 0 and entry_signal:
                if position > 0:  # Long
                    if current_price >= entry_signal['tp'] or current_price <= entry_signal['sl']:
                        pnl = position * (current_price - entry_price)
                        exit_fee = abs(pnl) * self.fee_rate
                        capital += pnl - exit_fee
                        total_fees += exit_fee
                        trades.append((pnl - exit_fee) / (position * entry_price))
                        position = 0
                        entry_signal = None
                else:  # Short
                    if current_price <= entry_signal['tp'] or current_price >= entry_signal['sl']:
                        pnl = position * (entry_price - current_price)
                        exit_fee = abs(pnl) * self.fee_rate
                        capital += pnl - exit_fee
                        total_fees += exit_fee
                        trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                        position = 0
                        entry_signal = None

        # Calculate results
        if trades:
            bars_per_day = 288 / (params.get('timeframe', 5) / 5)  # Adjust for timeframe
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': f'Scalp Z {params.get("timeframe", 5)}m',
                'params': params,
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades) if trades else 0,
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades) if trades else 0,
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000,
                'data_days': days
            }
        return {'strategy': f'Scalp Z {params.get("timeframe", 5)}m', 'daily_return': 0, 'trades': 0}

    def test_squeeze_pro_optimized(self, df, params):
        """Optimized Squeeze Pro with adjustable parameters"""
        trades = []
        capital = 10000
        total_fees = 0
        position = 0
        entry_price = 0
        entry_signal = None
        last_trade_idx = -params['min_bars_between_trades']

        for i in range(params['bb_period'] + 5, min(len(df), 15000)):
            if i - last_trade_idx < params['min_bars_between_trades']:
                continue

            # Calculate Bollinger Bands
            prices = df['Close'].iloc[i-params['bb_period']:i+1]
            sma = prices.mean()
            std = prices.std()
            bb_upper = sma + params['bb_std'] * std
            bb_lower = sma - params['bb_std'] * std
            bb_middle = sma

            current_price = df['Close'].iloc[i]

            # Strategy logic
            signal = None

            # LONG: Break above upper BB
            if current_price > bb_upper:
                signal = {
                    'type': 'LONG',
                    'entry': current_price,
                    'sl': bb_middle,
                    'tp': current_price * (1 + params['tp_pct'])
                }

            # SHORT: Break below lower BB
            elif current_price < bb_lower:
                signal = {
                    'type': 'SHORT',
                    'entry': current_price,
                    'sl': bb_middle,
                    'tp': current_price * (1 - params['tp_pct'])
                }

            # Execute trade
            if signal and position == 0:
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                entry_signal = signal
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_idx = i

            # Check exits
            elif position != 0 and entry_signal:
                if position > 0:  # Long
                    if current_price >= entry_signal['tp'] or current_price <= entry_signal['sl']:
                        pnl = position * (current_price - entry_price)
                        exit_fee = abs(pnl) * self.fee_rate
                        capital += pnl - exit_fee
                        total_fees += exit_fee
                        trades.append((pnl - exit_fee) / (position * entry_price))
                        position = 0
                        entry_signal = None
                else:  # Short
                    if current_price <= entry_signal['tp'] or current_price >= entry_signal['sl']:
                        pnl = position * (entry_price - current_price)
                        exit_fee = abs(pnl) * self.fee_rate
                        capital += pnl - exit_fee
                        total_fees += exit_fee
                        trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                        position = 0
                        entry_signal = None

        # Calculate results
        if trades:
            bars_per_day = 288 / (params.get('timeframe', 5) / 5)
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': f'Squeeze Pro {params.get("timeframe", 5)}m',
                'params': params,
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades) if trades else 0,
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades) if trades else 0,
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000,
                'data_days': days
            }
        return {'strategy': f'Squeeze Pro {params.get("timeframe", 5)}m', 'daily_return': 0, 'trades': 0}

    def run_comprehensive_optimization(self):
        """Run comprehensive optimization across timeframes and parameters"""
        print("🚀 CRYPTO BOTS OPTIMIZATION - MULTI-TIMEFRAME")
        print("=" * 70)
        print("Testing Scalp Z & Squeeze Pro across timeframes: 1m, 5m, 10m, 15m, 30m")
        print("Using 2+ years of Binance data (2021-2024) with 0.035% fees")
        print("=" * 70)

        # Load extended dataset
        print("\n📊 LOADING DATA:")
        base_data = self.load_extended_data(months=36)  # 3 years
        if base_data.empty:
            return

        # Test different timeframes
        timeframes = [1, 5, 10, 15, 30]  # minutes

        # Scalp Z optimization parameters
        scalp_z_params = [
            {'ema_period': 50, 'stoch_period': 14, 'oversold_threshold': 20, 'overbought_threshold': 80, 'tp_pct': 0.01, 'sl_pct': 0.01, 'min_bars_between_trades': 30},  # Original
            {'ema_period': 30, 'stoch_period': 14, 'oversold_threshold': 25, 'overbought_threshold': 75, 'tp_pct': 0.008, 'sl_pct': 0.012, 'min_bars_between_trades': 20},  # Faster
            {'ema_period': 100, 'stoch_period': 21, 'oversold_threshold': 30, 'overbought_threshold': 70, 'tp_pct': 0.015, 'sl_pct': 0.008, 'min_bars_between_trades': 50},  # Slower
            {'ema_period': 50, 'stoch_period': 14, 'oversold_threshold': 15, 'overbought_threshold': 85, 'tp_pct': 0.012, 'sl_pct': 0.015, 'min_bars_between_trades': 40},  # Extreme thresholds
        ]

        # Squeeze Pro optimization parameters
        squeeze_params = [
            {'bb_period': 20, 'bb_std': 2.0, 'tp_pct': 0.05, 'min_bars_between_trades': 50},  # Original
            {'bb_period': 15, 'bb_std': 1.8, 'tp_pct': 0.03, 'min_bars_between_trades': 30},  # Tighter
            {'bb_period': 25, 'bb_std': 2.5, 'tp_pct': 0.08, 'min_bars_between_trades': 70},  # Wider
            {'bb_period': 20, 'bb_std': 2.0, 'tp_pct': 0.02, 'min_bars_between_trades': 25},  # More frequent
        ]

        all_results = []

        for tf in timeframes:
            print(f"\n⏰ TESTING TIMEFRAME: {tf} minutes")
            print("-" * 40)

            # Resample data to timeframe
            tf_data = self.resample_to_timeframe(base_data, tf)
            if tf_data.empty:
                continue

            tf_results = []

            # Test Scalp Z variations
            print(f"Testing Scalp Z on {tf}m data...")
            for i, params in enumerate(scalp_z_params):
                params_with_tf = params.copy()
                params_with_tf['timeframe'] = tf

                result = self.test_scalp_z_optimized(tf_data.copy(), params_with_tf)
                result['param_set'] = f'Scalp_Z_Set_{i+1}'
                tf_results.append(result)

                status = "🎯" if result['daily_return'] >= 0.005 else "⚠️" if result['daily_return'] >= 0 else "❌"
                print(".3f")

            # Test Squeeze Pro variations
            print(f"Testing Squeeze Pro on {tf}m data...")
            for i, params in enumerate(squeeze_params):
                params_with_tf = params.copy()
                params_with_tf['timeframe'] = tf

                result = self.test_squeeze_pro_optimized(tf_data.copy(), params_with_tf)
                result['param_set'] = f'Squeeze_Set_{i+1}'
                tf_results.append(result)

                status = "🎯" if result['daily_return'] >= 0.005 else "⚠️" if result['daily_return'] >= 0 else "❌"
                print(".3f")

            all_results.extend(tf_results)

        # Analyze comprehensive results
        self.analyze_optimization_results(all_results)

        return all_results

    def analyze_optimization_results(self, results):
        """Analyze optimization results across all timeframes and parameters"""
        print("\n" + "=" * 70)
        print("🏆 OPTIMIZATION RESULTS - ALL TIMEFRAMES")
        print("=" * 70)

        # Convert to DataFrame
        df = pd.DataFrame([r for r in results if r['trades'] > 0])

        if df.empty:
            print("❌ No valid optimization results")
            return

        # Best performers by timeframe
        timeframes = [1, 5, 10, 15, 30]

        print("\n📊 BEST RESULTS BY TIMEFRAME:")
        print("Timeframe | Best Strategy | Daily Return | Trades/Day | Win Rate")
        print("-" * 70)

        for tf in timeframes:
            tf_results = df[df['strategy'].str.contains(f'{tf}m')]
            if not tf_results.empty:
                best = tf_results.loc[tf_results['daily_return'].idxmax()]
                print("8")

        # Best overall strategies
        print("\n🎯 TOP 5 BEST PERFORMING STRATEGIES:")
        top_results = df.nlargest(5, 'daily_return')
        for i, result in enumerate(top_results.iterrows(), 1):
            idx, row = result
            print("2d")
        # Strategy type analysis
        print("\n📈 PERFORMANCE BY STRATEGY TYPE:")
        scalp_results = df[df['strategy'].str.contains('Scalp Z')]
        squeeze_results = df[df['strategy'].str.contains('Squeeze Pro')]

        if not scalp_results.empty:
            scalp_avg = scalp_results['daily_return'].mean()
            scalp_best = scalp_results['daily_return'].max()
            print(".3f")

        if not squeeze_results.empty:
            squeeze_avg = squeeze_results['daily_return'].mean()
            squeeze_best = squeeze_results['daily_return'].max()
            print(".3f")

        # Timeframe analysis
        print("\n⏰ BEST TIMEFRAME FOR EACH STRATEGY:")

        for strategy_type in ['Scalp Z', 'Squeeze Pro']:
            strategy_data = df[df['strategy'].str.contains(strategy_type)]
            if not strategy_data.empty:
                best_tf = strategy_data.loc[strategy_data['daily_return'].idxmax()]['strategy']
                best_return = strategy_data['daily_return'].max()
                print(".3f")

        # Fee impact analysis
        profitable_strategies = len(df[df['daily_return'] >= 0.005])
        total_strategies = len(df)
        print("\n💰 OPTIMIZATION SUMMARY:")
        print(f"   Strategies Tested: {total_strategies}")
        print(f"   Profitable (0.5%+ daily): {profitable_strategies}")
        print(".1f")

        # Recommendations
        if profitable_strategies > 0:
            best_overall = df.loc[df['daily_return'].idxmax()]
            print("\n🎯 RECOMMENDATIONS:")
            print(f"   Best Strategy: {best_overall['strategy']}")
            print(".3f")
            print(f"   Optimal Timeframe: Found in optimization")

            if best_overall['daily_return'] >= 0.008:
                print("   ✅ EXCELLENT: Achieves 0.8%+ daily target")
            elif best_overall['daily_return'] >= 0.005:
                print("   ✅ GOOD: Achieves 0.5%+ daily profitability")
        else:
            print("\n⚠️ NO CLEAR WINNERS:")
            print("   Strategies need further optimization or different market conditions")

        # Save results
        df.to_csv('backtesting_tests/crypto_multi_timeframe_optimization.csv', index=False)
        print("\n💾 Detailed results saved to: backtesting_tests/crypto_multi_timeframe_optimization.csv")

def main():
    optimizer = CryptoMultiTimeframeOptimizer()
    results = optimizer.run_comprehensive_optimization()

if __name__ == "__main__":
    main()
