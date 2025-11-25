#!/usr/bin/env python3
"""
LONG-TERM BACKTESTING OF TOP 5 HIGH-RETURN WINNERS
Tests winners over 3-6 months of data and on major indices (SPY, QQQ, DIA)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')

from shared_utils.indicators import *
from shared_utils.data_loader import load_ohlcv_yfinance
from shared_strategies.scalping_strategy import ScalpingStrategy


class LongTermBacktester:
    def __init__(self):
        self.data_dir = Path('data/processed')
        self.results_dir = self.data_dir / 'long_term_results'
        self.results_dir.mkdir(exist_ok=True)

        # Top 5 winners to test long-term
        self.top5_winners = [
            {
                'name': 'Time-Based TSLA 15m',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {'momentum_period': 7},
                'expected_return': 0.3615,
                'expected_win_rate': 0.623,
                'expected_trades': 53
            },
            {
                'name': 'Volume Breakout AMD 5m',
                'strategy': 'volume_breakout',
                'symbol': 'AMD',
                'interval': '5m',
                'params': {'volume_multiplier': 1.8},
                'expected_return': 0.1375,
                'expected_win_rate': 0.667,
                'expected_trades': 15
            },
            {
                'name': 'RSI GOOGL 15m',
                'strategy': 'rsi_scalping',
                'symbol': 'GOOGL',
                'interval': '15m',
                'params': {'rsi_period': 7, 'rsi_oversold': 25, 'rsi_overbought': 75},
                'expected_return': 0.0950,
                'expected_win_rate': 0.552,
                'expected_trades': 29
            },
            {
                'name': 'Candlestick DIA 5m',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {'volume_multiplier': 1.4},
                'expected_return': 0.0716,
                'expected_win_rate': 0.744,
                'expected_trades': 39
            },
            {
                'name': 'RSI MSFT 5m',
                'strategy': 'rsi_scalping',
                'symbol': 'MSFT',
                'interval': '5m',
                'params': {},  # Default parameters
                'expected_return': 0.0400,
                'expected_win_rate': 0.537,
                'expected_trades': 54
            }
        ]

        # Indices to test strategies on
        self.indices = ['SPY', 'QQQ', 'DIA']

        self.long_term_results = []

    def get_long_term_data(self, symbol: str, interval: str, months: int = 6) -> pd.DataFrame:
        """Get longer-term historical data (3-6 months)"""
        try:
            # Convert interval format
            yf_interval = interval
            if interval == '5m':
                yf_interval = '5m'
            elif interval == '15m':
                yf_interval = '15m'
            else:
                yf_interval = '5m'

            # Get data for specified months
            period = f"{months}mo"

            df = load_ohlcv_yfinance(symbol, period=period, interval=yf_interval)

            # Ensure we have enough data
            min_bars = 1000 if interval == '5m' else 300  # More bars for 5m
            if len(df) < min_bars:
                print(f"Insufficient long-term data for {symbol} {interval}: {len(df)} bars (need {min_bars})")
                return pd.DataFrame()

            print(f"Loaded {len(df)} bars of {months}-month data for {symbol} {interval}")
            return df

        except Exception as e:
            print(f"Failed to get long-term data for {symbol} {interval}: {e}")
            return pd.DataFrame()

    def backtest_strategy_long_term(self, strategy_config: dict, test_data: pd.DataFrame) -> dict:
        """Backtest a strategy on long-term data"""
        strategy_name = strategy_config['name']
        strategy_type = strategy_config['strategy']
        symbol = strategy_config['symbol']
        interval = strategy_config['interval']
        params = strategy_config['params']

        print(f"\n🔄 Backtesting {strategy_name} on {len(test_data)} bars...")

        if test_data.empty:
            return {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'interval': interval,
                'data_period': 'N/A',
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_trade_return': 0,
                'status': 'no_data'
            }

        try:
            # Split data into monthly segments for rolling analysis
            test_data = test_data.sort_index()
            start_date = test_data.index[0]
            end_date = test_data.index[-1]
            total_days = (end_date - start_date).days

            # Run backtest on full period
            strategy = ScalpingStrategy(test_data, strategy_type=strategy_type, **params)
            results = strategy.backtest()

            result = {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'interval': interval,
                'data_period_days': total_days,
                'data_period_months': round(total_days / 30, 1),
                'total_return': results.get('total_return', 0),
                'win_rate': results.get('win_rate', 0),
                'total_trades': results.get('total_trades', 0),
                'max_drawdown': results.get('max_drawdown', 0),
                'sharpe_ratio': results.get('sharpe_ratio', 0),
                'avg_trade_return': results.get('avg_trade_return', 0),
                'expected_return': strategy_config.get('expected_return', 0),
                'expected_win_rate': strategy_config.get('expected_win_rate', 0),
                'return_diff': results.get('total_return', 0) - strategy_config.get('expected_return', 0),
                'win_rate_diff': results.get('win_rate', 0) - strategy_config.get('expected_win_rate', 0),
                'status': 'success'
            }

            print(f"   Result: {result['total_return']:.2%} return, {result['win_rate']:.1%} win rate, {result['total_trades']} trades")
            print(f"   Expected: {result['expected_return']:.2%} return, {result['expected_win_rate']:.1%} win rate")
            print(f"   Difference: {result['return_diff']:+.2%} return, {result['win_rate_diff']:+.1%} win rate")

            return result

        except Exception as e:
            print(f"Error in long-term backtest for {strategy_name}: {e}")
            return {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'interval': interval,
                'data_period_days': total_days if 'total_days' in locals() else 0,
                'data_period_months': 0,
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_trade_return': 0,
                'expected_return': strategy_config.get('expected_return', 0),
                'expected_win_rate': strategy_config.get('expected_win_rate', 0),
                'return_diff': 0,
                'win_rate_diff': 0,
                'status': 'error',
                'error': str(e)
            }

    def test_on_indices(self, strategy_config: dict):
        """Test a winning strategy on major indices"""
        strategy_name = strategy_config['name']
        print(f"\n📊 Testing {strategy_name} on Major Indices...")

        for index_symbol in self.indices:
            # Test on both 5m and 15m timeframes
            for interval in ['5m', '15m']:
                try:
                    # Get 3 months of index data
                    index_data = self.get_long_term_data(index_symbol, interval, months=3)

                    if not index_data.empty:
                        result = self.backtest_strategy_long_term(strategy_config, index_data)
                        result['original_symbol'] = strategy_config['symbol']
                        result['index_symbol'] = index_symbol
                        result['test_type'] = 'index_adaptation'

                        self.long_term_results.append(result)

                except Exception as e:
                    print(f"Failed to test {strategy_name} on {index_symbol} {interval}: {e}")

    def run_long_term_analysis(self):
        """Run comprehensive long-term analysis"""
        print("📈 STARTING LONG-TERM BACKTEST ANALYSIS")
        print("=" * 60)
        print("Testing Top 5 Winners over 3-6 months of historical data")
        print("=" * 60)

        # Test each winner on its original asset with longer timeframe
        print("\n🔍 PHASE 1: Testing Winners on Original Assets (Long-Term)")

        for winner in self.top5_winners:
            # Test with 6 months of data on original asset
            long_term_data = self.get_long_term_data(
                winner['symbol'],
                winner['interval'],
                months=6
            )

            if not long_term_data.empty:
                result = self.backtest_strategy_long_term(winner, long_term_data)
                result['test_type'] = 'original_long_term'
                self.long_term_results.append(result)

        # Test winners on major indices
        print("\n🏛️ PHASE 2: Testing Winners on Major Indices (SPY, QQQ, DIA)")

        for winner in self.top5_winners:
            self.test_on_indices(winner)

        # Save comprehensive results
        results_df = pd.DataFrame(self.long_term_results)
        results_df.to_csv('backtesting_tests/long_term_backtest_results.csv', index=False)

        print("\n🎯 LONG-TERM ANALYSIS COMPLETE")
        print(f"Total long-term tests: {len(self.long_term_results)}")

        # Show summary
        successful_tests = results_df[results_df['status'] == 'success']
        if len(successful_tests) > 0:
            print("\n📊 LONG-TERM PERFORMANCE SUMMARY:")
            print(f"Average Return: {successful_tests['total_return'].mean():.2%}")
            print(f"Average Win Rate: {successful_tests['win_rate'].mean():.1%}")
            print(f"Average Max DD: {successful_tests['max_drawdown'].mean():.2%}")
            print(f"Total Trades: {successful_tests['total_trades'].sum()}")

            # Show top performers in long-term test
            print("\n🏆 TOP LONG-TERM PERFORMERS:")
            top_long_term = successful_tests.nlargest(5, 'total_return')[
                ['strategy_name', 'symbol', 'interval', 'data_period_months', 'total_return', 'win_rate', 'total_trades']
            ]
            for _, perf in top_long_term.iterrows():
                print(f"📈 {perf['strategy_name']} on {perf['symbol']} {perf['interval']} "
                      f"({perf['data_period_months']} months): "
                      f"{perf['total_return']:.2%} return, {perf['win_rate']:.1%} win rate, "
                      f"{perf['total_trades']} trades")

        return results_df


def main():
    backtester = LongTermBacktester()
    results = backtester.run_long_term_analysis()

    # Additional analysis
    print("\n🔍 DETAILED ANALYSIS:")
    successful = results[results['status'] == 'success']

    if len(successful) > 0:
        # Original vs Long-term comparison
        original_tests = successful[successful['test_type'] == 'original_long_term']
        if len(original_tests) > 0:
            print("\n📊 ORIGINAL ASSETS - SHORT VS LONG TERM:")
            for _, test in original_tests.iterrows():
                expected_return = test['expected_return']
                actual_return = test['total_return']
                return_diff = actual_return - expected_return

                print(f"  {test['strategy_name']}:")
                print(f"    Expected (30 days): {expected_return:.2%}")
                print(f"    Actual ({test['data_period_months']} months): {actual_return:.2%}")
                print(f"    Difference: {return_diff:+.2%}")
                print(f"    Win Rate: {test['win_rate']:.1%} (expected: {test['expected_win_rate']:.1%})")
                print()

        # Index adaptation analysis
        index_tests = successful[successful['test_type'] == 'index_adaptation']
        if len(index_tests) > 0:
            print("\n🏛️ INDEX ADAPTATION RESULTS:")
            for _, test in index_tests.iterrows():
                if test['total_return'] > 0.02:  # Show only profitable adaptations
                    print(f"  {test['strategy_name']} → {test['index_symbol']} {test['interval']}: "
                          f"{test['total_return']:.2%} return, {test['win_rate']:.1%} win rate, "
                          f"{test['total_trades']} trades")

if __name__ == "__main__":
    main()
