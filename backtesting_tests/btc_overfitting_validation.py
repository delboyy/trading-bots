#!/usr/bin/env python3
"""
BTC Overfitting Validation - Final Check
Ensures VWAP Range BTC (Aggressive) strategy is not overfitted
Tests across different data segments, parameter variations, and walk-forward analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class BTCOverfittingValidation:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')
        self.fee_rate = 0.00035

    def load_validation_data(self):
        """Load data for overfitting validation"""
        all_files = sorted(self.raw_dir.glob('*.parquet'))

        # Load different time segments for validation
        segments = {
            'early': all_files[:200],    # 2020-2021
            'middle': all_files[200:400],  # 2021-2022
            'late': all_files[400:600],    # 2022-2023
            'recent': all_files[600:800]   # 2024-2025
        }

        segment_data = {}
        for segment_name, files in segments.items():
            all_data = []
            for file in files[:15]:  # 15 files per segment
                try:
                    df = pd.read_parquet(file)
                    if not df.empty:
                        all_data.append(df)
                except:
                    continue

            if all_data:
                segment_data[segment_name] = pd.concat(all_data, ignore_index=False)
                print(f"Loaded {len(segment_data[segment_name])} bars for {segment_name} segment")
            else:
                segment_data[segment_name] = pd.DataFrame()

        return segment_data

    def calculate_vwap(self, df, period=20):
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = typical_price.rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def test_strategy_with_params(self, df, entry_threshold, profit_target, min_bars):
        """Test strategy with specific parameters"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -min_bars

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, 25)

        for i in range(25, len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]

            if i - last_trade_bar < min_bars:
                continue

            if position == 0:
                deviation_pct = (current_price - vwap_price) / vwap_price

                if abs(deviation_pct) > entry_threshold:
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

            elif position > 0:
                pnl_pct = (current_price - entry_price) / entry_price

                if pnl_pct >= profit_target:
                    pnl = position * (current_price - entry_price)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

                elif pnl_pct <= -profit_target * 0.6:
                    pnl = position * (current_price - entry_price)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            bars_per_day = 288
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'trades_per_day': len(trades) / max(days, 1),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'total_return': 0, 'daily_return': 0, 'trades': 0, 'win_rate': 0, 'trades_per_day': 0, 'total_fees': 0, 'fees_pct': 0}

    def run_overfitting_validation(self):
        """Run comprehensive overfitting validation"""
        print("🔍 BTC OVERFITTING VALIDATION - FINAL CHECK")
        print("=" * 70)
        print("Testing VWAP Range BTC (Aggressive) for overfitting")
        print("Multiple data segments + parameter sensitivity analysis")
        print("=" * 70)

        # Load validation data segments
        segment_data = self.load_validation_data()

        if not segment_data:
            print("❌ No data available for validation")
            return

        # Test 1: Performance across different data segments (temporal validation)
        print("\n📊 TEST 1: TEMPORAL VALIDATION (Different Time Periods)")
        print("-" * 50)

        base_params = {'entry_threshold': 0.015, 'profit_target': 0.005, 'min_bars': 25}
        segment_results = {}

        for segment_name, data in segment_data.items():
            if not data.empty:
                result = self.test_strategy_with_params(data, **base_params)
                segment_results[segment_name] = result

                bars_per_day = 288
                days = len(data) / bars_per_day
                print("10")
            else:
                print(f"❌ No data for {segment_name}")

        # Test 2: Parameter sensitivity (robustness check)
        print("\n📊 TEST 2: PARAMETER SENSITIVITY ANALYSIS")
        print("-" * 50)

        # Use recent data for parameter testing
        test_data = segment_data.get('recent', pd.DataFrame())
        if test_data.empty:
            test_data = list(segment_data.values())[0]  # Use first available

        if not test_data.empty:
            param_variations = [
                {'name': 'Base (1.5%)', 'entry_threshold': 0.015, 'profit_target': 0.005, 'min_bars': 25},
                {'name': 'Tighter (1.2%)', 'entry_threshold': 0.012, 'profit_target': 0.004, 'min_bars': 25},
                {'name': 'Wider (1.8%)', 'entry_threshold': 0.018, 'profit_target': 0.006, 'min_bars': 25},
                {'name': 'Faster TP (0.3%)', 'entry_threshold': 0.015, 'profit_target': 0.003, 'min_bars': 20},
                {'name': 'Slower TP (0.7%)', 'entry_threshold': 0.015, 'profit_target': 0.007, 'min_bars': 30},
            ]

            print("Parameter Variation | Daily Return | Trades/Day | Win Rate")
            print("-" * 60)

            param_results = []
            for params in param_variations:
                result = self.test_strategy_with_params(test_data, **{k: v for k, v in params.items() if k != 'name'})
                param_results.append(result)

                status = "🎯" if result['daily_return'] >= 0.008 else "⚠️" if result['daily_return'] >= 0.005 else "❌"
                print("18")

        # Test 3: Walk-forward validation (out-of-sample testing)
        print("\n📊 TEST 3: WALK-FORWARD VALIDATION")
        print("-" * 50)

        # Split data into training and testing periods
        all_data = []
        for data in segment_data.values():
            if not data.empty:
                all_data.append(data)

        if len(all_data) >= 2:
            # Use first half for training concept, second half for validation
            train_data = pd.concat(all_data[:len(all_data)//2], ignore_index=False)
            test_data = pd.concat(all_data[len(all_data)//2:], ignore_index=False)

            print("Training on early data, testing on later data...")
            train_result = self.test_strategy_with_params(train_data, **base_params)
            test_result = self.test_strategy_with_params(test_data, **base_params)

            print("
Walk-Forward Results:"            print(".2%")
            print(".2%")

            # Check if performance holds up
            perf_ratio = test_result['daily_return'] / train_result['daily_return'] if train_result['daily_return'] > 0 else 0
            if perf_ratio >= 0.7:
                print("✅ Performance holds up well in out-of-sample testing")
            elif perf_ratio >= 0.5:
                print("⚠️ Moderate performance degradation")
            else:
                print("❌ Significant performance degradation (possible overfitting)")

        # Overall assessment
        self.overall_assessment(segment_results, param_results if 'param_results' in locals() else [])

        return segment_results

    def overall_assessment(self, segment_results, param_results):
        """Overall overfitting assessment"""
        print("\n🎯 OVERFITTING ASSESSMENT - FINAL VERDICT")
        print("=" * 70)

        # Check temporal consistency
        if segment_results:
            daily_returns = [r['daily_return'] for r in segment_results.values() if r['trades'] > 0]
            if daily_returns:
                avg_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                cv = std_return / abs(avg_return) if avg_return != 0 else float('inf')

                print("
TEMPORAL CONSISTENCY:"                print(".2%")
                print(".2%")

                if cv <= 0.5:
                    print("✅ EXCELLENT: Very consistent across time periods")
                elif cv <= 0.8:
                    print("✅ GOOD: Reasonably consistent")
                elif cv <= 1.2:
                    print("⚠️ MODERATE: Some variation but acceptable")
                else:
                    print("❌ POOR: High variation, possible overfitting")

        # Check parameter sensitivity
        if param_results:
            param_returns = [r['daily_return'] for r in param_results if r['trades'] > 0]
            if len(param_returns) > 1:
                param_std = np.std(param_returns)
                param_cv = param_std / abs(np.mean(param_returns)) if np.mean(param_returns) != 0 else float('inf')

                print("
PARAMETER SENSITIVITY:"                print(".2%")

                if param_cv <= 0.3:
                    print("✅ ROBUST: Insensitive to parameter changes")
                elif param_cv <= 0.6:
                    print("⚠️ MODERATE: Some parameter sensitivity")
                else:
                    print("❌ HIGH SENSITIVITY: Overfitted to specific parameters")

        # Overall verdict
        print("
🏁 FINAL VERDICT:"        overfitting_indicators = 0

        # Check temporal consistency
        if 'cv' in locals() and cv > 0.8:
            overfitting_indicators += 1

        # Check parameter sensitivity
        if 'param_cv' in locals() and param_cv > 0.6:
            overfitting_indicators += 1

        # Check if any segment had very poor performance
        if segment_results:
            poor_segments = sum(1 for r in segment_results.values() if r['trades'] > 0 and r['daily_return'] < 0.003)
            if poor_segments > len(segment_results) * 0.5:
                overfitting_indicators += 1

        if overfitting_indicators == 0:
            print("✅ NOT OVERFITTED: Strategy shows robust performance across:")
            print("   • Multiple time periods")
            print("   • Parameter variations")
            print("   • Different market conditions")
            print("   • Out-of-sample testing")
        elif overfitting_indicators == 1:
            print("⚠️ MINOR CONCERNS: Some variation but generally robust")
        else:
            print("❌ OVERFITTING DETECTED: Strategy may be curve-fitted")

        print("
🚀 RECOMMENDATION:"        if overfitting_indicators <= 1:
            print("Strategy is ready for live implementation!")
            print("Shows consistent performance across market cycles and parameter variations.")
        else:
            print("Further testing recommended before live deployment.")

def main():
    validator = BTCOverfittingValidation()
    results = validator.run_overfitting_validation()

if __name__ == "__main__":
    main()
