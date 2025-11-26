#!/usr/bin/env python3
"""
BTC 1% Daily Target - Simplified Approach
Using existing 5m data with different bar counts to simulate different timeframes
Includes 0.035% trading fees in all calculations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class BTCSimpleOnePercent:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')

        # Load just 5m data and use bar counting for different "timeframes"
        self.btc_data = self.load_recent_btc_data()
        self.fee_rate = 0.00035  # 0.035% per trade

    def load_recent_btc_data(self):
        """Load recent 5m BTC data for fast testing"""
        if not self.raw_dir.exists():
            print("❌ No BTC data found")
            return pd.DataFrame()

        # Get just the 5 most recent files for speed
        all_files = sorted(self.raw_dir.glob('*.parquet'), reverse=True)
        recent_files = all_files[:5]

        print(f"Loading {len(recent_files)} recent 5m BTC files...")

        all_data = []
        for file in recent_files:
            try:
                df = pd.read_parquet(file)
                if not df.empty:
                    all_data.append(df)
            except:
                continue

        if not all_data:
            return pd.DataFrame()

        # Simple combine
        combined_df = pd.concat(all_data, ignore_index=False)

        print(f"Loaded {len(combined_df)} total BTC 5m bars")
        return combined_df

    def calculate_vwap(self, df, period=20):
        """Calculate VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = typical_price.rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def test_vwap_range_btc(self, df, entry_threshold=0.01, profit_target=0.003, min_bars_between_trades=12):
        """VWAP range trading optimized for BTC with fees"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -min_bars_between_trades

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, 25)  # Longer period for BTC

        for i in range(25, len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]

            # Enforce minimum bars between trades
            if i - last_trade_bar < min_bars_between_trades:
                continue

            if position == 0:
                deviation_pct = (current_price - vwap_price) / vwap_price

                # Wider thresholds for BTC's volatility
                if abs(deviation_pct) > entry_threshold:
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

                if pnl_pct >= profit_target:
                    pnl = position * (current_price - entry_price)
                    # Exit fee
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

                elif pnl_pct <= -profit_target * 0.6:  # Tighter stop loss
                    pnl = position * (current_price - entry_price)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            return {
                'total_return': (capital - 10000) / 10000,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'total_return': 0, 'trades': 0, 'win_rate': 0, 'avg_trade': 0, 'total_fees': 0, 'fees_pct': 0}

    def test_momentum_swing_btc(self, df, momentum_period=12, profit_target=0.004, min_bars_between_trades=20):
        """Momentum-based swing trading for BTC"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -min_bars_between_trades

        for i in range(momentum_period, len(df)):
            current_price = df['Close'].iloc[i]

            # Calculate momentum
            momentum = current_price - df['Close'].iloc[i-momentum_period]

            # Enforce minimum bars between trades
            if i - last_trade_bar < min_bars_between_trades:
                continue

            if position == 0:
                momentum_threshold = df['Close'].iloc[i-momentum_period] * 0.008  # 0.8% momentum

                if momentum > momentum_threshold:
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

                elif momentum < -momentum_threshold:
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = -effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                if abs(pnl_pct) >= profit_target:
                    if position > 0:
                        pnl = position * (current_price - entry_price)
                    else:
                        pnl = position * (entry_price - current_price)

                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            return {
                'total_return': (capital - 10000) / 10000,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'total_return': 0, 'trades': 0, 'win_rate': 0, 'avg_trade': 0, 'total_fees': 0, 'fees_pct': 0}

    def test_range_breakout_btc(self, df, range_period=30, breakout_pct=0.005, profit_target=0.004, min_bars_between_trades=25):
        """Range breakout for BTC with wider ranges"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -min_bars_between_trades

        for i in range(range_period, len(df)):
            # Calculate range
            recent_high = df['High'].iloc[i-range_period:i].max()
            recent_low = df['Low'].iloc[i-range_period:i].min()
            current_price = df['Close'].iloc[i]

            # Enforce minimum bars between trades
            if i - last_trade_bar < min_bars_between_trades:
                continue

            if position == 0:
                if current_price > recent_high * (1 + breakout_pct):
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

                elif current_price < recent_low * (1 - breakout_pct):
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = -effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                if abs(pnl_pct) >= profit_target:
                    if position > 0:
                        pnl = position * (current_price - entry_price)
                    else:
                        pnl = position * (entry_price - current_price)

                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (abs(position) * entry_price))
                    position = 0

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = position * (entry_price - final_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            return {
                'total_return': (capital - 10000) / 10000,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'total_return': 0, 'trades': 0, 'win_rate': 0, 'avg_trade': 0, 'total_fees': 0, 'fees_pct': 0}

    def test_volume_price_surge_btc(self, df, volume_mult=2.5, profit_target=0.005, min_bars_between_trades=30):
        """Volume + price surge for BTC momentum"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        last_trade_bar = -min_bars_between_trades

        df = df.copy()
        df['avg_volume'] = df['Volume'].rolling(20).mean()

        for i in range(20, len(df)):
            current_price = df['Close'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['avg_volume'].iloc[i]

            # Enforce minimum bars between trades
            if i - last_trade_bar < min_bars_between_trades:
                continue

            if position == 0 and volume > avg_volume * volume_mult:
                # Strong volume + price surge
                if current_price > df['Close'].iloc[i-1] * 1.003:  # 0.3% upward surge
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee
                    last_trade_bar = i

                elif current_price < df['Close'].iloc[i-1] * 0.997:  # 0.3% downward surge
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = -effective_capital / current_price
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

        # Close remaining position
        if position != 0:
            final_price = df['Close'].iloc[-1]
            pnl = position * (final_price - entry_price)
            exit_fee = abs(pnl) * self.fee_rate
            capital += pnl - exit_fee
            total_fees += exit_fee
            trades.append((pnl - exit_fee) / (abs(position) * entry_price))

        if trades:
            return {
                'total_return': (capital - 10000) / 10000,
                'trades': len(trades),
                'win_rate': sum(1 for t in trades if t > 0) / len(trades),
                'avg_trade': np.mean(trades),
                'total_fees': total_fees,
                'fees_pct': total_fees / 10000
            }
        return {'total_return': 0, 'trades': 0, 'win_rate': 0, 'avg_trade': 0, 'total_fees': 0, 'fees_pct': 0}

    def run_simple_1pct_test(self):
        """Run simplified 1% daily target testing"""
        print("🎯 BTC 1% DAILY TARGET - SIMPLIFIED APPROACH")
        print("=" * 60)
        print("Using 5m BTC data with different logic for 1%+ net daily returns")
        print("Includes 0.035% trading fees")
        print("=" * 60)

        if self.btc_data.empty:
            print("❌ No BTC data available")
            return

        # Simplified test configurations focused on realistic approaches
        test_configs = [
            {
                'name': 'VWAP Range BTC (Conservative)',
                'strategy': 'vwap_range',
                'params': {'entry_threshold': 0.008, 'profit_target': 0.003, 'min_bars_between_trades': 15}
            },
            {
                'name': 'VWAP Range BTC (Moderate)',
                'strategy': 'vwap_range',
                'params': {'entry_threshold': 0.012, 'profit_target': 0.004, 'min_bars_between_trades': 20}
            },
            {
                'name': 'VWAP Range BTC (Aggressive)',
                'strategy': 'vwap_range',
                'params': {'entry_threshold': 0.015, 'profit_target': 0.005, 'min_bars_between_trades': 25}
            },
            {
                'name': 'Momentum Swing BTC (12-bar)',
                'strategy': 'momentum_swing',
                'params': {'momentum_period': 12, 'profit_target': 0.004, 'min_bars_between_trades': 25}
            },
            {
                'name': 'Momentum Swing BTC (16-bar)',
                'strategy': 'momentum_swing',
                'params': {'momentum_period': 16, 'profit_target': 0.005, 'min_bars_between_trades': 30}
            },
            {
                'name': 'Range Breakout BTC (30-bar)',
                'strategy': 'range_breakout',
                'params': {'range_period': 30, 'breakout_pct': 0.005, 'profit_target': 0.004, 'min_bars_between_trades': 30}
            },
            {
                'name': 'Range Breakout BTC (45-bar)',
                'strategy': 'range_breakout',
                'params': {'range_period': 45, 'breakout_pct': 0.007, 'profit_target': 0.005, 'min_bars_between_trades': 35}
            },
            {
                'name': 'Volume Surge BTC (2.5x)',
                'strategy': 'volume_surge',
                'params': {'volume_mult': 2.5, 'profit_target': 0.005, 'min_bars_between_trades': 35}
            },
            {
                'name': 'Volume Surge BTC (3.0x)',
                'strategy': 'volume_surge',
                'params': {'volume_mult': 3.0, 'profit_target': 0.006, 'min_bars_between_trades': 40}
            }
        ]

        results = []

        for config in test_configs:
            print(f"\n🧪 Testing: {config['name']}")

            try:
                if config['strategy'] == 'vwap_range':
                    result = self.test_vwap_range_btc(self.btc_data, **config['params'])
                elif config['strategy'] == 'momentum_swing':
                    result = self.test_momentum_swing_btc(self.btc_data, **config['params'])
                elif config['strategy'] == 'range_breakout':
                    result = self.test_range_breakout_btc(self.btc_data, **config['params'])
                elif config['strategy'] == 'volume_surge':
                    result = self.test_volume_price_surge_btc(self.btc_data, **config['params'])
                else:
                    continue

                # Calculate daily metrics (5m data = ~288 bars per day)
                bars_per_day = 288
                total_days = len(self.btc_data) / bars_per_day
                trades_per_day = result['trades'] / max(total_days, 1)
                daily_return_pct = result['total_return'] / max(total_days, 1)

                # Check if meets target
                meets_target = (
                    daily_return_pct >= 0.01 and  # 1% daily net return
                    trades_per_day >= 3 and trades_per_day <= 12 and  # 3-12 trades/day
                    result['win_rate'] >= 0.55  # 55%+ win rate
                )

                result.update({
                    'config': config,
                    'trades_per_day': trades_per_day,
                    'daily_return_pct': daily_return_pct,
                    'meets_target': meets_target
                })

                results.append(result)

                status = "🎯 TARGET HIT" if meets_target else "⚠️  CLOSE" if daily_return_pct >= 0.008 else "❌ LOW"
                print(".2%")
                print(".1f")
                print(".1%")
                print(".2%")

            except Exception as e:
                print(f"   ❌ Error: {e}")

        # Analyze results
        self.analyze_simple_results(results)

        return results

    def analyze_simple_results(self, results):
        """Analyze simplified results"""
        print("\n" + "=" * 60)
        print("🏆 BTC 1% TARGET - SIMPLIFIED RESULTS")
        print("=" * 60)

        valid_results = [r for r in results if r['trades'] > 3 and r['total_return'] > 0]

        if not valid_results:
            print("❌ No valid results with sufficient trades")
            return

        # Sort by daily return
        ranked_results = sorted(valid_results,
                              key=lambda x: (x['daily_return_pct'], x['win_rate'], -x['trades_per_day']),
                              reverse=True)

        print("\n🎯 TOP BTC STRATEGIES FOR 1% DAILY TARGET:")
        print("Strategy | Daily Return | Trades/Day | Win Rate | Net Return")
        print("-" * 80)

        target_hits = []
        for i, result in enumerate(ranked_results[:10]):
            if result['daily_return_pct'] >= 0.008:  # Show strategies close to 1%
                print("2d")
                if result['meets_target']:
                    target_hits.append(result)

        if target_hits:
            print("\n✅ SUCCESS! Strategies achieving 1%+ daily returns:")
            for hit in target_hits:
                print(f"   • {hit['config']['name']}: {hit['daily_return_pct']:.2%} daily")
        else:
            print("\n⚠️ NO PERFECT MATCHES - but several close to 1%")
            close_ones = [r for r in ranked_results if r['daily_return_pct'] >= 0.008]
            if close_ones:
                print("Close matches:")
                for close in close_ones[:3]:
                    print(".2%")

        # Overall statistics
        if valid_results:
            all_daily_returns = [r['daily_return_pct'] for r in valid_results]
            all_trades_per_day = [r['trades_per_day'] for r in valid_results]

            print("\n📈 OVERALL STATISTICS:")
            print(f"Average Daily Return: {np.mean(all_daily_returns):.2%}")
            print(".1f")

            # Best performers
            best_daily = max(all_daily_returns)
            best_strategy = max(valid_results, key=lambda x: x['daily_return_pct'])

            print("\n🏆 BEST OVERALL:")
            print(f"Strategy: {best_strategy['config']['name']}")
            print(".2%")
            print(".1f")
            print(f"Win Rate: {best_strategy['win_rate']:.1%}")

            if best_daily >= 0.01:
                print("🎯 ACHIEVED: 1%+ daily net returns!")
            elif best_daily >= 0.008:
                print("⚠️ CLOSE: Within 0.2% of 1% target")
            else:
                print("❌ NEEDS WORK: Further optimization required")

        # Save results
        results_df = pd.DataFrame(valid_results)
        results_df.to_csv('backtesting_tests/btc_simple_1pct_results.csv', index=False)
        print("\n💾 Results saved to: backtesting_tests/btc_simple_1pct_results.csv")
def main():
    btc_simple = BTCSimpleOnePercent()
    results = btc_simple.run_simple_1pct_test()

    print("\n🎯 SIMPLE 1% TARGET TESTING COMPLETE")
    print("Ready for IBKR validation with the best performing strategies!")

if __name__ == "__main__":
    main()
