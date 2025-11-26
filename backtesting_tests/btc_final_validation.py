#!/usr/bin/env python3
"""
BTC Final Validation - Overfitting Check
Quick validation to ensure VWAP Range BTC strategy is not overfitted
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class BTCFinalValidation:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')
        self.fee_rate = 0.00035

    def quick_validation_test(self):
        """Quick overfitting validation"""
        print("🔍 BTC FINAL VALIDATION - OVERFITTING CHECK")
        print("=" * 60)

        # Test on 3 different time segments
        all_files = sorted(self.raw_dir.glob('*.parquet'))

        segments = {
            'Q4_2020': all_files[:50],      # Early data
            'Q2_2021': all_files[150:200],  # Mid bull
            'Q4_2024': all_files[600:650]   # Recent
        }

        base_params = {'entry_threshold': 0.015, 'profit_target': 0.005, 'min_bars': 25}

        results = {}
        for segment_name, files in segments.items():
            data_list = []
            for file in files[:8]:  # 8 files per segment
                try:
                    df = pd.read_parquet(file)
                    if not df.empty:
                        data_list.append(df)
                except:
                    continue

            if data_list:
                segment_data = pd.concat(data_list, ignore_index=False)
                result = self.test_strategy(segment_data, **base_params)

                bars_per_day = 288
                days = len(segment_data) / bars_per_day
                daily_return = result['total_return'] / max(days, 1)

                results[segment_name] = daily_return
                print(".2%")

        # Check consistency
        if results:
            returns = list(results.values())
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            cv = std_return / abs(avg_return) if avg_return != 0 else float('inf')

            print("
📊 CONSISTENCY ANALYSIS:"            print(".2%")
            print(".2%")

            if cv <= 0.5:
                verdict = "✅ ROBUST - No overfitting detected"
            elif cv <= 0.8:
                verdict = "⚠️ ACCEPTABLE - Minor variation"
            else:
                verdict = "❌ CONCERNS - Possible overfitting"

            print(f"Verdict: {verdict}")

            if cv <= 0.8:
                print("
🚀 STRATEGY READY FOR LIVE IMPLEMENTATION!"                return True
            else:
                print("
⚠️ FURTHER TESTING RECOMMENDED"                return False

    def test_strategy(self, df, entry_threshold=0.015, profit_target=0.005, min_bars=25):
        """Test strategy with given parameters"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -min_bars

        df = df.copy()
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = typical_price.rolling(25).sum() / df['Volume'].rolling(25).sum()

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

        return {
            'total_return': (capital - 10000) / 10000,
            'trades': len(trades),
            'win_rate': sum(1 for t in trades if t > 0) / len(trades) if trades else 0,
            'total_fees': total_fees
        }

def main():
    validator = BTCFinalValidation()
    is_robust = validator.quick_validation_test()

    if is_robust:
        print("
🎉 VALIDATION PASSED - Strategy is robust and ready for live implementation!"        return True
    else:
        print("
⚠️ VALIDATION FAILED - Further testing needed"        return False

if __name__ == "__main__":
    main()
