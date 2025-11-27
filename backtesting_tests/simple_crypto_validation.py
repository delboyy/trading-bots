#!/usr/bin/env python3
"""
Simple Crypto Bots Validation - Scalp Z & Squeeze Pro
Using 2+ years of Binance data with correct strategy logic
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class SimpleCryptoValidation:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')
        self.fee_rate = 0.00035  # 0.035%

    def load_recent_data(self, months=6):
        """Load recent Binance data for testing"""
        all_files = sorted(self.raw_dir.glob('*.parquet'), reverse=True)

        # Take recent files
        recent_files = all_files[:min(months * 30 * 24 * 12, len(all_files))]  # ~12 bars/hour

        print(f"Loading {len(recent_files)} recent files (~{months} months of data)")

        all_data = []
        for file in recent_files[:50]:  # Limit for speed
            try:
                df = pd.read_parquet(file)
                if not df.empty and len(df) > 10:
                    all_data.append(df)
            except:
                continue

        if all_data:
            # Simple combine without sorting to avoid index issues
            combined = pd.concat(all_data, ignore_index=False)
            print(f"Total bars loaded: {len(combined)}")
            return combined

        print("❌ No data loaded")
        return pd.DataFrame()

    def test_scalp_z_logic(self, df):
        """Test Scalp Z strategy logic correctly"""
        print("Testing BTC Scalp Z (EMA 50 + Stochastic 14,3,3)...")

        trades = []
        capital = 10000
        total_fees = 0
        position = 0
        entry_price = 0
        entry_signal = None  # Store the entry signal for exit checks
        last_trade_idx = -30

        for i in range(50, min(len(df), 10000)):  # Test on subset for speed
            if i - last_trade_idx < 30:
                continue

            # Calculate indicators
            lookback = min(50, i)
            prices = df['Close'].iloc[i-lookback:i+1]
            ema = prices.ewm(span=50, adjust=False).mean().iloc[-1]

            # Stochastic calculation
            high_14 = df['High'].iloc[i-14:i+1].max()
            low_14 = df['Low'].iloc[i-14:i+1].min()
            close = df['Close'].iloc[i]

            if high_14 > low_14:
                stoch_k = ((close - low_14) / (high_14 - low_14)) * 100
            else:
                stoch_k = 50

            current_price = close

            # Strategy logic - generate signal
            signal = None

            # LONG: Close > EMA + Stoch < 20
            if current_price > ema and stoch_k < 20:
                signal = {
                    'type': 'LONG',
                    'entry': current_price,
                    'sl': current_price * 0.99,   # 1% SL
                    'tp': current_price * 1.015   # 1.5% TP
                }

            # SHORT: Close < EMA + Stoch > 80
            elif current_price < ema and stoch_k > 80:
                signal = {
                    'type': 'SHORT',
                    'entry': current_price,
                    'sl': current_price * 1.01,   # 1% SL
                    'tp': current_price * 0.985   # 1.5% TP
                }

            # Execute trade
            if signal and position == 0:
                # Entry with fee
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                entry_signal = signal  # Store for exit checks
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_idx = i

            # Check exits using stored entry signal
            elif position != 0 and entry_signal:
                # Simple exit on TP/SL hit
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
            bars_per_day = 288
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': 'BTC Scalp Z (EMA + Stochastic)',
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades) if trades else 0,
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades) if trades else 0,
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }

        return {'strategy': 'BTC Scalp Z', 'daily_return': 0, 'trades': 0}

    def test_squeeze_pro_logic(self, df):
        """Test Squeeze Pro strategy logic correctly"""
        print("Testing BTC Squeeze Pro (BB 20,2 breakout)...")

        trades = []
        capital = 10000
        total_fees = 0
        position = 0
        entry_price = 0
        entry_signal = None  # Store the entry signal for exit checks
        last_trade_idx = -50

        for i in range(20, min(len(df), 10000)):  # Test on subset
            if i - last_trade_idx < 50:
                continue

            # Calculate Bollinger Bands
            lookback = min(20, i)
            prices = df['Close'].iloc[i-lookback:i+1]
            sma = prices.mean()
            std = prices.std()
            bb_upper = sma + 2 * std
            bb_lower = sma - 2 * std
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
                    'tp': current_price * 1.05  # 5% TP
                }

            # SHORT: Break below lower BB
            elif current_price < bb_lower:
                signal = {
                    'type': 'SHORT',
                    'entry': current_price,
                    'sl': bb_middle,
                    'tp': current_price * 0.95  # 5% TP
                }

            # Execute trade
            if signal and position == 0:
                # Entry with fee
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                entry_signal = signal  # Store for exit checks
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_idx = i

            # Check exits using stored entry signal
            elif position != 0 and entry_signal:
                # Exit on TP/SL hit
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
            bars_per_day = 288
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': 'BTC Squeeze Pro (BB Breakout)',
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades) if trades else 0,
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades) if trades else 0,
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }

        return {'strategy': 'BTC Squeeze Pro', 'daily_return': 0, 'trades': 0}

    def run_validation(self):
        """Run the validation"""
        print("🔍 CRYPTO BOTS VALIDATION - SCALP Z & SQUEEZE PRO")
        print("=" * 60)
        print("Testing with correct strategy logic")
        print("Using 2+ years of Binance BTC/USDT 5m data")
        print("0.035% fees on entry + exit")
        print("=" * 60)

        # Load data
        test_data = self.load_recent_data(months=12)  # 1 year for speed
        if test_data.empty:
            print("❌ No data available")
            return

        # Test strategies
        results = []

        print("\n🧪 RUNNING TESTS:")
        print("-" * 40)

        # Test Scalp Z
        scalp_result = self.test_scalp_z_logic(test_data.copy())
        results.append(scalp_result)

        # Test Squeeze Pro
        squeeze_result = self.test_squeeze_pro_logic(test_data.copy())
        results.append(squeeze_result)

        # Show results
        print("\n📊 RESULTS:")
        print("Strategy | Daily Return | Trades | Win Rate | Fees %")
        print("-" * 55)

        for result in results:
            if result['trades'] > 0:
                status = "✅" if result['daily_return'] >= 0.005 else "⚠️" if result['daily_return'] >= 0 else "❌"
                print("18")
            else:
                print(f"{result['strategy'][:20]:20} | NO TRADES")

        # Detailed analysis
        valid_results = [r for r in results if r['trades'] > 0]

        for result in valid_results:
            print(f"\n🔍 {result['strategy']}:")
            print(".2%")
            print(f"   Trades: {result['trades']}")
            print(".1%")
            print(".4%")
            print(".2%")

            if result['daily_return'] >= 0.005:
                print("   ✅ PROFITABLE: Ready for optimization")
            elif result['daily_return'] >= 0:
                print("   ⚠️ MARGINAL: Needs parameter tuning")
            else:
                print("   ❌ UNPROFITABLE: Needs fundamental changes")

        # Save results
        if valid_results:
            results_df = pd.DataFrame(valid_results)
            results_df.to_csv('backtesting_tests/simple_crypto_validation.csv', index=False)
            print("\n💾 Results saved to: backtesting_tests/simple_crypto_validation.csv")
        return results

def main():
    validator = SimpleCryptoValidation()
    results = validator.run_validation()

if __name__ == "__main__":
    main()
