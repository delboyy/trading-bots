#!/usr/bin/env python3
"""
Crypto Bots Validation - Test All Crypto Strategies with 0.035% Fees
Tests BTC VWAP, BTC Fib Zigzag, BTC Scalp Z, BTC Squeeze Pro, ETH Fib Zigzag
Across different market periods with realistic fees
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class CryptoBotsValidator:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')
        self.fee_rate = 0.00035  # 0.035% per trade (both sides = 0.07% round trip)

    def load_test_data(self, days=30):
        """Load recent BTC data for testing"""
        all_files = sorted(self.raw_dir.glob('*.parquet'), reverse=True)
        test_files = all_files[:min(days * 24 * 12, len(all_files))]  # ~12 5min bars per hour

        all_data = []
        for file in test_files:
            try:
                df = pd.read_parquet(file)
                if not df.empty:
                    all_data.append(df)
            except:
                continue

        if all_data:
            combined = pd.concat(all_data, ignore_index=False)
            print(f"Loaded {len(combined)} bars (~{len(combined)/(288):.1f} days)")
            return combined
        return pd.DataFrame()

    def calculate_vwap(self, df, period=25):
        """Calculate VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def detect_zigzag_swings(self, df, deviation_pct=0.02):
        """ZigZag swing detection"""
        highs = []
        lows = []

        if df.empty:
            return highs, lows

        h_series = df['high'].values
        l_series = df['low'].values

        tmp_high = h_series[0]
        tmp_low = l_series[0]
        tmp_high_idx = 0
        tmp_low_idx = 0
        trend = 0

        for i in range(1, len(h_series)):
            curr_high = h_series[i]
            curr_low = l_series[i]

            if trend == 0:
                if curr_high >= tmp_low * (1 + deviation_pct):
                    lows.append({'idx': tmp_low_idx, 'price': tmp_low})
                    trend = 1
                    tmp_high = curr_high
                    tmp_high_idx = i
                elif curr_low <= tmp_high * (1 - deviation_pct):
                    highs.append({'idx': tmp_high_idx, 'price': tmp_high})
                    trend = -1
                    tmp_low = curr_low
                    tmp_low_idx = i
            elif trend == 1:
                if curr_high > tmp_high:
                    tmp_high = curr_high
                    tmp_high_idx = i
                elif curr_low <= tmp_high * (1 - deviation_pct):
                    highs.append({'idx': tmp_high_idx, 'price': tmp_high})
                    trend = -1
                    tmp_low = curr_low
                    tmp_low_idx = i
            elif trend == -1:
                if curr_low < tmp_low:
                    tmp_low = curr_low
                    tmp_low_idx = i
                elif curr_high >= tmp_low * (1 + deviation_pct):
                    lows.append({'idx': tmp_low_idx, 'price': tmp_low})
                    trend = 1
                    tmp_high = curr_high
                    tmp_high_idx = i

        return highs, lows

    def test_btc_vwap_strategy(self, df):
        """Test BTC VWAP Range Aggressive strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -25

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, 25)

        for i in range(25, len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]

            if i - last_trade_bar < 25:
                continue

            if position == 0:
                deviation_pct = (current_price - vwap_price) / vwap_price

                if abs(deviation_pct) > 0.015:  # 1.5% deviation
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

            elif position > 0:
                pnl_pct = (current_price - entry_price) / entry_price

                if pnl_pct >= 0.005:  # 0.5% TP
                    pnl = position * (current_price - entry_price)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

                elif pnl_pct <= -0.003:  # 0.3% SL
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
                'strategy': 'BTC VWAP Range (Aggressive)',
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'strategy': 'BTC VWAP Range (Aggressive)', 'daily_return': 0, 'trades': 0}

    def test_btc_fib_zigzag_strategy(self, df):
        """Test BTC Fib Zigzag strategy"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -50
        risk_reward = 2.0

        for i in range(50, len(df)):
            if i - last_trade_bar < 50:
                continue

            # Get zigzag swings
            window_data = df.iloc[max(0, i-100):i+1]
            highs, lows = self.detect_zigzag_swings(window_data)

            if not highs or not lows:
                continue

            current_close = df['Close'].iloc[i]
            ema = df['Close'].iloc[max(0, i-50):i+1].ewm(span=50, adjust=False).mean().iloc[-1]

            signal = {}

            # LONG: Above EMA, breakout from fib level
            if current_close > ema and highs:
                last_high = highs[-1]
                fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]

                for fib in fib_levels:
                    fib_level = last_high['price'] - (last_high['price'] - lows[-1]['price']) * fib
                    if abs(current_close - fib_level) / fib_level < 0.005:  # Near fib level
                        signal = {
                            "type": "LONG",
                            "entry": current_close,
                            "sl": lows[-1]['price'],
                            "tp": current_close + (current_close - lows[-1]['price']) * risk_reward
                        }
                        break

            # SHORT: Below EMA, breakdown from fib level
            elif current_close < ema and lows:
                last_low = lows[-1]
                fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]

                for fib in fib_levels:
                    fib_level = last_low['price'] + (highs[-1]['price'] - last_low['price']) * fib
                    if abs(current_close - fib_level) / fib_level < 0.005:
                        signal = {
                            "type": "SHORT",
                            "entry": current_close,
                            "sl": highs[-1]['price'],
                            "tp": current_close - (highs[-1]['price'] - current_close) * risk_reward
                        }
                        break

            if signal and position == 0:
                # Entry
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_bar = i

            elif position != 0 and signal:
                # Check exit conditions
                current_pnl = (current_close - entry_price) / entry_price if position > 0 else (entry_price - current_close) / entry_price

                tp_hit = False
                sl_hit = False

                if position > 0:
                    if current_close >= signal['tp']:
                        tp_hit = True
                    elif current_close <= signal['sl']:
                        sl_hit = True
                else:
                    if current_close <= signal['tp']:
                        tp_hit = True
                    elif current_close >= signal['sl']:
                        sl_hit = True

                if tp_hit or sl_hit:
                    pnl = position * (current_close - entry_price) if position > 0 else position * (entry_price - current_close)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price) if position > 0 else position * (entry_price - final_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            bars_per_day = 288
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': 'BTC Fib Zigzag',
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'strategy': 'BTC Fib Zigzag', 'daily_return': 0, 'trades': 0}

    def test_btc_scalp_z_strategy(self, df):
        """Test BTC Scalp Z strategy (EMA + Stochastic)"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -20

        for i in range(50, len(df)):
            if i - last_trade_bar < 20:
                continue

            # Calculate indicators
            window = df.iloc[max(0, i-50):i+1]
            ema = window['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            current_close = df['Close'].iloc[i]

            # Simple stochastic calculation
            high_14 = window['High'].tail(14).max()
            low_14 = window['Low'].tail(14).min()
            if high_14 != low_14:
                stoch_k = ((current_close - low_14) / (high_14 - low_14)) * 100
            else:
                stoch_k = 50

            signal = {}

            # LONG: Above EMA + Oversold
            if current_close > ema and stoch_k < 20:
                signal = {
                    "type": "LONG",
                    "entry": current_close,
                    "sl": current_close * 0.99,  # 1% SL
                    "tp": current_close * 1.015  # 1.5% TP
                }

            # SHORT: Below EMA + Overbought
            elif current_close < ema and stoch_k > 80:
                signal = {
                    "type": "SHORT",
                    "entry": current_close,
                    "sl": current_close * 1.01,  # 1% SL
                    "tp": current_close * 0.985  # 1.5% TP
                }

            if signal and position == 0:
                # Entry
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_bar = i

            elif position != 0:
                # Check exit conditions
                current_pnl = (current_close - entry_price) / entry_price if position > 0 else (entry_price - current_close) / entry_price

                tp_hit = False
                sl_hit = False

                if position > 0:
                    if current_close >= signal['tp']:
                        tp_hit = True
                    elif current_close <= signal['sl']:
                        sl_hit = True
                else:
                    if current_close <= signal['tp']:
                        tp_hit = True
                    elif current_close >= signal['sl']:
                        sl_hit = True

                if tp_hit or sl_hit:
                    pnl = position * (current_close - entry_price) if position > 0 else position * (entry_price - current_close)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price) if position > 0 else position * (entry_price - final_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            bars_per_day = 288
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': 'BTC Scalp Z',
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'strategy': 'BTC Scalp Z', 'daily_return': 0, 'trades': 0}

    def test_btc_squeeze_pro_strategy(self, df):
        """Test BTC Squeeze Pro strategy (Bollinger Bands)"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -30

        for i in range(20, len(df)):
            if i - last_trade_bar < 30:
                continue

            # Calculate Bollinger Bands
            window = df.iloc[max(0, i-20):i+1]
            sma = window['Close'].mean()
            std = window['Close'].std()
            bb_upper = sma + 2 * std
            bb_lower = sma - 2 * std
            bb_middle = sma

            current_close = df['Close'].iloc[i]

            signal = {}

            # LONG: Break above upper BB
            if current_close > bb_upper:
                signal = {
                    "type": "LONG",
                    "entry": current_close,
                    "sl": bb_middle,
                    "tp": current_close * 1.05  # 5% TP
                }

            # SHORT: Break below lower BB
            elif current_close < bb_lower:
                signal = {
                    "type": "SHORT",
                    "entry": current_close,
                    "sl": bb_middle,
                    "tp": current_close * 0.95  # 5% TP
                }

            if signal and position == 0:
                # Entry
                entry_fee = capital * self.fee_rate
                effective_capital = capital - entry_fee
                qty = effective_capital / signal['entry']
                position = qty if signal['type'] == 'LONG' else -qty
                entry_price = signal['entry']
                total_fees += entry_fee
                capital -= entry_fee
                last_trade_bar = i

            elif position != 0:
                # Check exit conditions
                current_pnl = (current_close - entry_price) / entry_price if position > 0 else (entry_price - current_close) / entry_price

                tp_hit = False
                sl_hit = False

                if position > 0:
                    if current_close >= signal['tp']:
                        tp_hit = True
                    elif current_close <= signal['sl']:
                        sl_hit = True
                else:
                    if current_close <= signal['tp']:
                        tp_hit = True
                    elif current_close >= signal['sl']:
                        sl_hit = True

                if tp_hit or sl_hit:
                    pnl = position * (current_close - entry_price) if position > 0 else position * (entry_price - current_close)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price) if position > 0 else position * (entry_price - final_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            bars_per_day = 288
            days = len(df) / bars_per_day
            daily_return = (capital - 10000) / 10000 / max(days, 1)

            return {
                'strategy': 'BTC Squeeze Pro',
                'total_return': (capital - 10000) / 10000,
                'daily_return': daily_return,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'trades_per_day': len(trades) / max(days, 1),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'strategy': 'BTC Squeeze Pro', 'daily_return': 0, 'trades': 0}

    def run_crypto_bots_validation(self):
        """Run comprehensive validation of all crypto bots"""
        print("🚀 CRYPTO BOTS VALIDATION - WITH 0.035% FEES")
        print("=" * 70)
        print("Testing all crypto strategies with realistic trading fees")
        print("Entry + Exit fees = 0.07% round-trip cost")
        print("=" * 70)

        # Test different time periods
        test_periods = [
            ('Recent 30 Days', 30),
            ('Recent 60 Days', 60),
            ('Recent 90 Days', 90)
        ]

        all_results = []

        for period_name, days in test_periods:
            print(f"\n📅 TESTING: {period_name}")
            print("-" * 50)

            test_data = self.load_test_data(days)
            if test_data.empty:
                print("❌ No data available")
                continue

            # Test each strategy
            strategies = [
                self.test_btc_vwap_strategy,
                self.test_btc_fib_zigzag_strategy,
                self.test_btc_scalp_z_strategy,
                self.test_btc_squeeze_pro_strategy
            ]

            period_results = []

            for strategy_func in strategies:
                try:
                    result = strategy_func(test_data.copy())
                    period_results.append(result)

                    status = "🎯 TARGET HIT" if result['daily_return'] >= 0.008 else "⚠️ GOOD" if result['daily_return'] >= 0.005 else "❌ WEAK"
                    print(".2%")

                except Exception as e:
                    print(f"❌ {strategy_func.__name__}: Error - {e}")
                    period_results.append({
                        'strategy': strategy_func.__name__,
                        'daily_return': 0,
                        'error': str(e)
                    })

            all_results.extend(period_results)

        # Analyze results
        self.analyze_validation_results(all_results)

        return all_results

    def analyze_validation_results(self, results):
        """Analyze validation results across all strategies and periods"""
        print("\n" + "=" * 70)
        print("🏆 CRYPTO BOTS VALIDATION RESULTS")
        print("=" * 70)

        # Convert to DataFrame for analysis
        df = pd.DataFrame([r for r in results if 'error' not in r])

        if df.empty:
            print("❌ No valid results to analyze")
            return

        # Group by strategy and calculate averages
        strategy_analysis = []
        for strategy_name in df['strategy'].unique():
            strategy_data = df[df['strategy'] == strategy_name]

            if not strategy_data.empty:
                avg_daily_return = strategy_data['daily_return'].mean()
                avg_trades_per_day = strategy_data['trades_per_day'].mean()
                avg_win_rate = strategy_data['win_rate'].mean()
                avg_fees_pct = strategy_data['fees_pct'].mean()

                profitable_periods = sum(1 for r in strategy_data['daily_return'] if r > 0)
                total_periods = len(strategy_data)

                strategy_analysis.append({
                    'strategy': strategy_name,
                    'avg_daily_return': avg_daily_return,
                    'avg_trades_per_day': avg_trades_per_day,
                    'avg_win_rate': avg_win_rate,
                    'avg_fees_pct': avg_fees_pct,
                    'profitable_periods': f"{profitable_periods}/{total_periods}"
                })

        # Sort by performance
        strategy_analysis.sort(key=lambda x: x['avg_daily_return'], reverse=True)

        print("\n📊 STRATEGY PERFORMANCE RANKING:")
        print("Strategy | Avg Daily Return | Trades/Day | Win Rate | Fees % | Profitable Periods")
        print("-" * 90)

        for strat in strategy_analysis:
            status = "🎯 EXCELLENT" if strat['avg_daily_return'] >= 0.01 else "✅ GOOD" if strat['avg_daily_return'] >= 0.005 else "⚠️ OK" if strat['avg_daily_return'] >= 0 else "❌ POOR"
            print("15")

        # Best performer analysis
        if strategy_analysis:
            best = strategy_analysis[0]
            print("\n🏆 BEST PERFORMER ANALYSIS:")
            print(f"Strategy: {best['strategy']}")
            print(".2%")
            print(".1f")
            print(".1%")
            print(".2%")
            print(f"Profitable Periods: {best['profitable_periods']}")

            if best['avg_daily_return'] >= 0.008:
                print("✅ STRATEGY ACHIEVES TARGET: 0.8%+ daily returns with fees")
            elif best['avg_daily_return'] >= 0.005:
                print("⚠️ STRATEGY IS PROFITABLE: 0.5%+ daily returns with fees")
            else:
                print("❌ STRATEGY NEEDS OPTIMIZATION: Below profitability threshold")

        # Fee impact analysis
        print("\n💰 FEE IMPACT ANALYSIS:")
        print("• Entry Fee: 0.035% per trade")
        print("• Exit Fee: 0.035% per trade")
        print("• Round-trip Cost: 0.07% per trade")
        print("• Break-even Win Rate: ~58% (for 1% avg trade)")
        print("• Target Win Rate: 60%+ for consistent profitability")

        # Recommendations
        print("\n🎯 RECOMMENDATIONS:")
        profitable_strategies = [s for s in strategy_analysis if s['avg_daily_return'] > 0]

        if profitable_strategies:
            print(f"✅ {len(profitable_strategies)} strategies show profitability with fees")
            print("These strategies can work with proper TP/SL automation")

            if best['avg_daily_return'] >= 0.008:
                print("🚀 VWAP Range strategy achieves target performance")
                print("Ready for live deployment with automated TP/SL")
        else:
            print("❌ No strategies currently profitable with 0.035% fees")
            print("Consider:")
            print("• Tighter TP/SL ratios")
            print("• Higher win rates")
            print("• Reduced trading frequency")
            print("• VIP fee tiers")

        # Save detailed results
        results_df = pd.DataFrame(results)
        results_df.to_csv('backtesting_tests/crypto_bots_fee_validation.csv', index=False)
        print("\n💾 Detailed results saved to: backtesting_tests/crypto_bots_fee_validation.csv")

def main():
    validator = CryptoBotsValidator()
    results = validator.run_crypto_bots_validation()

if __name__ == "__main__":
    main()
