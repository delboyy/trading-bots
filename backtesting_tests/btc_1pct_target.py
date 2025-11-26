#!/usr/bin/env python3
"""
BTC 1% Daily Target - Comprehensive Testing with Fees
Tests multiple timeframes and logic approaches to achieve 1% net daily returns
Includes 0.035% trading fees in all calculations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import time
warnings.filterwarnings('ignore')

class BTCOnePercentTarget:
    def __init__(self):
        self.raw_dir = Path('data/raw/binance_BTCUSDT_5m')
        self.btc_data_5m = self.load_btc_data('5m')
        self.btc_data_15m = self.load_btc_data('15m')
        self.btc_data_30m = self.load_btc_data('30m')

        # Target: 1% net daily returns with 0.035% fees
        self.target_daily_return = 0.01
        self.fee_rate = 0.00035  # 0.035% per trade
        self.required_gross_return = self.target_daily_return + 0.004  # Account for fees

    def load_btc_data(self, timeframe):
        """Load BTC data for specific timeframe"""
        if timeframe == '5m':
            # Load from existing 5m data
            if not self.raw_dir.exists():
                print("❌ No BTC data found")
                return pd.DataFrame()

            # Get just the 10 most recent files for speed
            all_files = sorted(self.raw_dir.glob('*.parquet'), reverse=True)
            recent_files = all_files[:10]

            print(f"Loading {len(recent_files)} recent 5m BTC files...")

            all_data = []
            for file in recent_files:
                try:
                    df = pd.read_parquet(file)
                    if not df.empty:
                        all_data.append(df)
                except:
                    continue

        elif timeframe == '15m':
            # Resample 5m data to 15m
            if self.btc_data_5m.empty:
                return pd.DataFrame()
            df_5m = self.btc_data_5m.copy()
            # Resample to 15m
            df_15m = df_5m.resample('15min').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            return df_15m

        elif timeframe == '30m':
            # Resample 5m data to 30m
            if self.btc_data_5m.empty:
                return pd.DataFrame()
            df_5m = self.btc_data_5m.copy()
            # Resample to 30m
            df_30m = df_5m.resample('30min').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            return df_30m

        if 'all_data' in locals() and all_data:
            # Simple combine for 5m data
            combined_df = pd.concat(all_data, ignore_index=False)
            print(f"Loaded {len(combined_df)} total BTC {timeframe} bars")
            return combined_df

        return pd.DataFrame()

    def calculate_vwap(self, df, period=20):
        """Calculate VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = typical_price.rolling(period).sum() / df['Volume'].rolling(period).sum()
        return vwap

    def test_vwap_range_target(self, df, params):
        """VWAP range trading with higher profit targets for 1% goal"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0

        df = df.copy()
        df['VWAP'] = self.calculate_vwap(df, params['vwap_period'])

        for i in range(params['vwap_period'], len(df)):
            current_price = df['Close'].iloc[i]
            vwap_price = df['VWAP'].iloc[i]

            if position == 0:
                deviation_pct = abs(current_price - vwap_price) / vwap_price

                # Wider entry threshold for fewer but better signals
                if deviation_pct > params['entry_threshold']:
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee

            elif position > 0:
                pnl_pct = (current_price - entry_price) / entry_price

                # Higher profit target (0.2-0.3%) for 1% daily goal
                if pnl_pct >= params['profit_target']:
                    pnl = position * (current_price - entry_price)
                    # Exit fee
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

                # Stop loss
                elif pnl_pct <= -params['stop_loss']:
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

    def test_momentum_breakout(self, df, params):
        """Momentum breakout with higher targets"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0

        for i in range(params['lookback'], len(df)):
            current_price = df['Close'].iloc[i]

            # Calculate momentum over lookback period
            momentum_prices = df['Close'].iloc[i-params['lookback']:i]
            momentum = (current_price - momentum_prices.iloc[0]) / momentum_prices.iloc[0]

            if position == 0 and abs(momentum) > params['momentum_threshold']:
                if momentum > 0:
                    # Entry fee
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee

            elif position > 0:
                pnl_pct = (current_price - entry_price) / entry_price

                if pnl_pct >= params['profit_target']:
                    pnl = position * (current_price - entry_price)
                    exit_fee = abs(pnl) * self.fee_rate
                    capital += pnl - exit_fee
                    total_fees += exit_fee
                    trades.append((pnl - exit_fee) / (position * entry_price))
                    position = 0

                elif pnl_pct <= -params['stop_loss']:
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

    def test_range_breakout_target(self, df, params):
        """Range breakout with higher profit targets"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0

        for i in range(params['range_period'], len(df)):
            # Calculate recent range
            recent_high = df['High'].iloc[i-params['range_period']:i].max()
            recent_low = df['Low'].iloc[i-params['range_period']:i].min()
            range_size = recent_high - recent_low

            current_price = df['Close'].iloc[i]

            if position == 0:
                # Breakout entries
                if current_price > recent_high * (1 + params['breakout_pct']):
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee

                elif current_price < recent_low * (1 - params['breakout_pct']):
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = -effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee

            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                if abs(pnl_pct) >= params['profit_target']:
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

    def test_volume_price_breakout(self, df, params):
        """Volume + price breakout for bigger moves"""
        capital = 10000
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0

        df = df.copy()
        df['avg_volume'] = df['Volume'].rolling(params['volume_period']).mean()

        for i in range(params['volume_period'], len(df)):
            current_price = df['Close'].iloc[i]
            volume = df['Volume'].iloc[i]
            avg_volume = df['avg_volume'].iloc[i]

            # Volume + price confirmation
            volume_ok = volume > avg_volume * params['volume_mult']

            if position == 0 and volume_ok:
                # Look for price breakout with volume
                recent_high = df['High'].iloc[i-params['lookback']:i].max()
                recent_low = df['Low'].iloc[i-params['lookback']:i].min()

                if current_price > recent_high * (1 + params['breakout_pct']):
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee

                elif current_price < recent_low * (1 - params['breakout_pct']):
                    entry_fee = capital * self.fee_rate
                    effective_capital = capital - entry_fee
                    position = -effective_capital / current_price
                    entry_price = current_price
                    total_fees += entry_fee
                    capital -= entry_fee

            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

                if abs(pnl_pct) >= params['profit_target']:
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

    def run_comprehensive_test(self):
        """Run comprehensive test across timeframes and strategies"""
        print("🎯 BTC 1% DAILY TARGET - COMPREHENSIVE TESTING")
        print("=" * 80)
        print("Including 0.035% trading fees - targeting 1% NET daily returns")
        print("Testing multiple timeframes and logic approaches")
        print("=" * 80)

        if self.btc_data_5m.empty:
            print("❌ No BTC data available")
            return

        # Comprehensive strategy test configurations
        test_configs = [
            # VWAP Range Trading - Different timeframes
            {
                'name': 'VWAP Range 5m (Target)',
                'timeframe': '5m',
                'strategy': 'vwap_range',
                'params': {'vwap_period': 20, 'entry_threshold': 0.008, 'profit_target': 0.0025, 'stop_loss': 0.0015}
            },
            {
                'name': 'VWAP Range 15m (Target)',
                'timeframe': '15m',
                'strategy': 'vwap_range',
                'params': {'vwap_period': 25, 'entry_threshold': 0.012, 'profit_target': 0.0035, 'stop_loss': 0.002}
            },
            {
                'name': 'VWAP Range 30m (Target)',
                'timeframe': '30m',
                'strategy': 'vwap_range',
                'params': {'vwap_period': 30, 'entry_threshold': 0.015, 'profit_target': 0.0045, 'stop_loss': 0.0025}
            },

            # Momentum Breakout - Different timeframes
            {
                'name': 'Momentum Breakout 5m',
                'timeframe': '5m',
                'strategy': 'momentum_breakout',
                'params': {'lookback': 5, 'momentum_threshold': 0.005, 'profit_target': 0.002, 'stop_loss': 0.001}
            },
            {
                'name': 'Momentum Breakout 15m',
                'timeframe': '15m',
                'strategy': 'momentum_breakout',
                'params': {'lookback': 8, 'momentum_threshold': 0.008, 'profit_target': 0.003, 'stop_loss': 0.0015}
            },
            {
                'name': 'Momentum Breakout 30m',
                'timeframe': '30m',
                'strategy': 'momentum_breakout',
                'params': {'lookback': 12, 'momentum_threshold': 0.012, 'profit_target': 0.004, 'stop_loss': 0.002}
            },

            # Range Breakout - Different timeframes
            {
                'name': 'Range Breakout 5m',
                'timeframe': '5m',
                'strategy': 'range_breakout',
                'params': {'range_period': 12, 'breakout_pct': 0.003, 'profit_target': 0.002, 'stop_loss': 0.001}
            },
            {
                'name': 'Range Breakout 15m',
                'timeframe': '15m',
                'strategy': 'range_breakout',
                'params': {'range_period': 16, 'breakout_pct': 0.004, 'profit_target': 0.003, 'stop_loss': 0.0015}
            },
            {
                'name': 'Range Breakout 30m',
                'timeframe': '30m',
                'strategy': 'range_breakout',
                'params': {'range_period': 20, 'breakout_pct': 0.005, 'profit_target': 0.004, 'stop_loss': 0.002}
            },

            # Volume Price Breakout
            {
                'name': 'Volume Price Breakout 5m',
                'timeframe': '5m',
                'strategy': 'volume_price_breakout',
                'params': {'volume_period': 15, 'volume_mult': 1.8, 'lookback': 8, 'breakout_pct': 0.002, 'profit_target': 0.0025}
            },
            {
                'name': 'Volume Price Breakout 15m',
                'timeframe': '15m',
                'strategy': 'volume_price_breakout',
                'params': {'volume_period': 20, 'volume_mult': 2.0, 'lookback': 12, 'breakout_pct': 0.003, 'profit_target': 0.0035}
            },
            {
                'name': 'Volume Price Breakout 30m',
                'timeframe': '30m',
                'strategy': 'volume_price_breakout',
                'params': {'volume_period': 25, 'volume_mult': 2.2, 'lookback': 16, 'breakout_pct': 0.004, 'profit_target': 0.0045}
            }
        ]

        results = []

        for config in test_configs:
            print(f"\n🧪 Testing: {config['name']}")

            # Get appropriate data
            if config['timeframe'] == '5m':
                data = self.btc_data_5m
            elif config['timeframe'] == '15m':
                data = self.btc_data_15m
            elif config['timeframe'] == '30m':
                data = self.btc_data_30m
            else:
                continue

            if data.empty:
                print(f"   ❌ No {config['timeframe']} data available")
                continue

            start_time = time.time()

            try:
                # Run appropriate strategy
                if config['strategy'] == 'vwap_range':
                    result = self.test_vwap_range_target(data, config['params'])
                elif config['strategy'] == 'momentum_breakout':
                    result = self.test_momentum_breakout(data, config['params'])
                elif config['strategy'] == 'range_breakout':
                    result = self.test_range_breakout_target(data, config['params'])
                elif config['strategy'] == 'volume_price_breakout':
                    result = self.test_volume_price_breakout(data, config['params'])
                else:
                    continue

                # Calculate daily metrics
                bars_per_day = 288 if config['timeframe'] == '5m' else 96 if config['timeframe'] == '15m' else 48
                total_days = len(data) / bars_per_day
                trades_per_day = result['trades'] / max(total_days, 1)
                daily_return_pct = result['total_return'] / max(total_days, 1)

                # Check if meets target
                meets_target = (
                    daily_return_pct >= self.target_daily_return and
                    trades_per_day >= 3 and trades_per_day <= 10 and  # Reasonable frequency
                    result['win_rate'] >= 0.55  # Decent win rate
                )

                result.update({
                    'config': config,
                    'trades_per_day': trades_per_day,
                    'daily_return_pct': daily_return_pct,
                    'meets_target': meets_target,
                    'timeframe': config['timeframe'],
                    'strategy_type': config['strategy']
                })

                results.append(result)

                run_time = time.time() - start_time

                status = "🎯 TARGET HIT" if meets_target else "⚠️  CLOSE" if daily_return_pct >= 0.008 else "❌ LOW"
                print(".2%")
                print(".1f")
                print(".1%")
                print(".2%")
                print(".3f")

            except Exception as e:
                run_time = time.time() - start_time
                print(f"   ❌ Error: {e} ({run_time:.1f}s)")

        # Analyze results
        self.analyze_comprehensive_results(results)

        return results

    def analyze_comprehensive_results(self, results):
        """Analyze comprehensive results"""
        print("\n" + "=" * 80)
        print("🏆 BTC 1% TARGET - COMPREHENSIVE RESULTS")
        print("=" * 80)

        # Filter valid results
        valid_results = [r for r in results if r['trades'] > 5 and r['total_return'] > 0]

        if not valid_results:
            print("❌ No valid results with sufficient trades")
            return

        # Sort by daily return
        ranked_results = sorted(valid_results,
                              key=lambda x: (x['daily_return_pct'], x['win_rate'], -x['trades_per_day']),
                              reverse=True)

        print("\n🎯 STRATEGIES MEETING 1% DAILY TARGET:")
        print("Rank | Strategy | Timeframe | Daily Return | Trades/Day | Win Rate | Net Return")
        print("-" * 110)

        target_hits = []
        for i, result in enumerate(ranked_results[:15]):
            if result['meets_target']:
                print("2d")
                target_hits.append(result)

        if not target_hits:
            print("❌ No strategies fully meet the 1% target")
            print("\n📊 CLOSEST MATCHES:")
            for i, result in enumerate(ranked_results[:5]):
                if result['daily_return_pct'] >= 0.007:
                    print("2d")

        # Overall statistics
        if valid_results:
            all_daily_returns = [r['daily_return_pct'] for r in valid_results]
            all_trades_per_day = [r['trades_per_day'] for r in valid_results]
            all_win_rates = [r['win_rate'] for r in valid_results]

            print("\n📈 OVERALL STATISTICS:")
            print(f"Average Daily Return: {np.mean(all_daily_returns):.2%}")
            print(".1f")
            print(".1%")

            # Best performers
            best_daily = max(all_daily_returns)
            best_win_rate = max(all_win_rates)

            print("\n🏆 BEST INDIVIDUAL METRICS:")
            print(f"Best Daily Return: {max(all_daily_returns):.2%}")
            print(".1%")

            # Target achievement
            target_count = sum(1 for r in valid_results if r['meets_target'])
            close_count = sum(1 for r in valid_results if r['daily_return_pct'] >= 0.008 and not r['meets_target'])

            print("\n🎯 TARGET ACHIEVEMENT:")
            print(f"1% Daily Target Hit: {target_count} strategies")
            print(f"Close to Target (0.8%+): {close_count} strategies")
            print(f"Total Valid Strategies: {len(valid_results)}")

            if target_hits:
                print("\n✅ SUCCESS! We found strategies achieving 1%+ daily returns!")
                best = target_hits[0]
                print(f"Best: {best['config']['name']} - {best['daily_return_pct']:.2%} daily")
            else:
                print("\n⚠️ NO PERFECT MATCHES - but several close to 1%")
                print("Recommendation: Adjust profit targets or reduce fees for better results")

        # Save results
        results_df = pd.DataFrame(valid_results)
        results_df.to_csv('backtesting_tests/btc_1pct_comprehensive_results.csv', index=False)
        print("\n💾 Results saved to: backtesting_tests/btc_1pct_comprehensive_results.csv")
def main():
    btc_target = BTCOnePercentTarget()
    results = btc_target.run_comprehensive_test()

    print("\n🎯 COMPREHENSIVE 1% TARGET TESTING COMPLETE")
    print("Results include 0.035% trading fees - ready for IBKR testing!")

if __name__ == "__main__":
    main()
