#!/usr/bin/env python3
"""
WALK-FORWARD ANALYSIS OF TOP 5 HIGH-RETURN WINNERS
Tests strategies on rolling 10-day windows over 60 days for robustness validation
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')

from shared_utils.indicators import *
from shared_utils.data_loader import load_ohlcv_yfinance
from shared_strategies.scalping_strategy import ScalpingStrategy


class WalkForwardAnalyzer:
    def __init__(self):
        self.data_dir = Path('data/processed')
        self.walk_forward_results = []

        # Top 5 winners for walk-forward analysis
        self.top5_winners = [
            {
                'name': 'Time-Based TSLA 15m',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {'momentum_period': 7},
                'expected_return': 0.3615,
                'expected_win_rate': 0.623
            },
            {
                'name': 'Volume Breakout AMD 5m',
                'strategy': 'volume_breakout',
                'symbol': 'AMD',
                'interval': '5m',
                'params': {'volume_multiplier': 1.8},
                'expected_return': 0.1375,
                'expected_win_rate': 0.667
            },
            {
                'name': 'RSI GOOGL 15m',
                'strategy': 'rsi_scalping',
                'symbol': 'GOOGL',
                'interval': '15m',
                'params': {'rsi_period': 7, 'rsi_oversold': 25, 'rsi_overbought': 75},
                'expected_return': 0.0950,
                'expected_win_rate': 0.552
            },
            {
                'name': 'Candlestick DIA 5m',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {'volume_multiplier': 1.4},
                'expected_return': 0.0716,
                'expected_win_rate': 0.744
            },
            {
                'name': 'RSI MSFT 5m',
                'strategy': 'rsi_scalping',
                'symbol': 'MSFT',
                'interval': '5m',
                'params': {},  # Default parameters
                'expected_return': 0.0400,
                'expected_win_rate': 0.537
            }
        ]

    def get_60_day_data(self, symbol: str, interval: str) -> pd.DataFrame:
        """Get maximum available 60-day intraday data"""
        try:
            df = load_ohlcv_yfinance(symbol, period="60d", interval=interval)

            if len(df) < 500:  # Need sufficient data
                print(f"Insufficient 60-day data for {symbol} {interval}: {len(df)} bars")
                return pd.DataFrame()

            print(f"Loaded {len(df)} bars of 60-day data for {symbol} {interval}")
            print(f"Date range: {df.index[0]} to {df.index[-1]}")
            return df

        except Exception as e:
            print(f"Failed to get 60-day data for {symbol} {interval}: {e}")
            return pd.DataFrame()

    def create_rolling_windows(self, full_data: pd.DataFrame, window_days: int = 10) -> list:
        """Create rolling windows for walk-forward analysis"""
        windows = []
        start_date = full_data.index[0]

        # Create overlapping windows every 5 days
        current_start = start_date
        end_date = full_data.index[-1]

        while current_start < end_date - timedelta(days=window_days):
            window_end = current_start + timedelta(days=window_days)

            # Get data for this window
            window_data = full_data[(full_data.index >= current_start) & (full_data.index <= window_end)]

            if len(window_data) >= 50:  # Minimum bars for meaningful test
                windows.append({
                    'start_date': current_start,
                    'end_date': window_end,
                    'data': window_data,
                    'days': window_days,
                    'bars': len(window_data)
                })

            # Move window forward by 5 days
            current_start += timedelta(days=5)

        print(f"Created {len(windows)} rolling {window_days}-day windows")
        return windows

    def test_strategy_on_window(self, strategy_config: dict, window_data: pd.DataFrame,
                               window_info: dict) -> dict:
        """Test a strategy on a specific time window"""
        strategy_name = strategy_config['name']
        strategy_type = strategy_config['strategy']
        symbol = strategy_config['symbol']
        interval = strategy_config['interval']
        params = strategy_config['params']

        try:
            # Run backtest on window data
            strategy = ScalpingStrategy(window_data, strategy_type=strategy_type, **params)
            results = strategy.backtest()

            result = {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'interval': interval,
                'window_start': window_info['start_date'],
                'window_end': window_info['end_date'],
                'window_days': window_info['days'],
                'data_bars': window_info['bars'],
                'total_return': results.get('total_return', 0),
                'win_rate': results.get('win_rate', 0),
                'total_trades': results.get('total_trades', 0),
                'max_drawdown': results.get('max_drawdown', 0),
                'sharpe_ratio': results.get('sharpe_ratio', 0),
                'avg_trade_return': results.get('avg_trade_return', 0),
                'status': 'success'
            }

            return result

        except Exception as e:
            return {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'interval': interval,
                'window_start': window_info['start_date'],
                'window_end': window_info['end_date'],
                'window_days': window_info['days'],
                'data_bars': window_info['bars'],
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_trade_return': 0,
                'status': 'error',
                'error': str(e)
            }

    def run_walk_forward_analysis(self):
        """Run comprehensive walk-forward analysis"""
        print("🔄 STARTING WALK-FORWARD ANALYSIS")
        print("=" * 60)
        print("Testing Top 5 Winners on Rolling 10-Day Windows (60-Day Period)")
        print("=" * 60)

        for winner in self.top5_winners:
            print(f"\n📊 Analyzing {winner['name']}...")

            # Get 60-day data
            full_data = self.get_60_day_data(winner['symbol'], winner['interval'])
            if full_data.empty:
                continue

            # Create rolling windows
            windows = self.create_rolling_windows(full_data, window_days=10)

            # Test strategy on each window
            window_results = []
            for window_info in windows:
                result = self.test_strategy_on_window(winner, window_info['data'], window_info)
                window_results.append(result)
                self.walk_forward_results.append(result)

                # Show progress
                return_pct = result['total_return'] * 100
                win_rate_pct = result['win_rate'] * 100
                print(f"  Window {result['window_start'].date()} - {result['window_end'].date()}: "
                      f"{return_pct:.1f}% return, {win_rate_pct:.1f}% win rate, {result['total_trades']} trades")

            # Analyze window results for this strategy
            if window_results:
                self.analyze_strategy_windows(winner, window_results)

        # Save comprehensive results
        results_df = pd.DataFrame(self.walk_forward_results)
        results_df.to_csv('backtesting_tests/walk_forward_results.csv', index=False)

        print("\n🎯 WALK-FORWARD ANALYSIS COMPLETE")
        print(f"Total window tests: {len(self.walk_forward_results)}")

        # Overall analysis
        successful_tests = results_df[results_df['status'] == 'success']
        if len(successful_tests) > 0:
            print("\n📊 OVERALL WALK-FORWARD PERFORMANCE:")
            print(f"Average Return per Window: {successful_tests['total_return'].mean():.2%}")
            print(f"Average Win Rate: {successful_tests['win_rate'].mean():.1%}")
            print(f"Total Trades Across All Windows: {successful_tests['total_trades'].sum()}")

            # Best performing windows
            print("\n🏆 BEST PERFORMING WINDOWS:")
            best_windows = successful_tests.nlargest(5, 'total_return')[
                ['strategy_name', 'window_start', 'window_end', 'total_return', 'win_rate', 'total_trades']
            ]
            for _, window in best_windows.iterrows():
                print(f"  {window['strategy_name']} ({window['window_start'].date()}-{window['window_end'].date()}): "
                      f"{window['total_return']:.2%} return, {window['win_rate']:.1%} win rate")

        return results_df

    def analyze_strategy_windows(self, strategy_config: dict, window_results: list):
        """Analyze results across windows for a specific strategy"""
        strategy_name = strategy_config['name']

        # Convert to DataFrame for analysis
        df = pd.DataFrame(window_results)

        successful = df[df['status'] == 'success']
        if len(successful) == 0:
            print(f"  ❌ No successful windows for {strategy_name}")
            return

        # Calculate statistics
        returns = successful['total_return']
        win_rates = successful['win_rate']
        trades = successful['total_trades']

        print(f"  📈 {strategy_name} - {len(successful)} successful windows:")
        print(f"    Return Range: {returns.min():.2%} to {returns.max():.2%}")
        print(f"    Average Return: {returns.mean():.2%} ± {returns.std():.2%}")
        print(f"    Win Rate Range: {win_rates.min():.1%} to {win_rates.max():.1%}")
        print(f"    Average Win Rate: {win_rates.mean():.1%} ± {win_rates.std():.1%}")
        print(f"    Total Trades: {trades.sum()}")

        # Consistency analysis
        positive_returns = (returns > 0).sum()
        consistency = positive_returns / len(returns)
        print(f"    Consistency (Positive Returns): {consistency:.1%}")

        # Risk analysis
        max_dd = successful['max_drawdown'].abs().max()
        avg_dd = successful['max_drawdown'].abs().mean()
        print(f"    Max Drawdown (Worst Window): {max_dd:.2%}")
        print(f"    Average Drawdown: {avg_dd:.2%}")

        # Robustness score (combination of consistency, avg return, and risk)
        robustness_score = (consistency * 0.4 +  # 40% weight on consistency
                          min(returns.mean() / 0.05, 1.0) * 0.4 +  # 40% weight on return (capped at 5%)
                          (1 - min(avg_dd / 0.05, 1.0)) * 0.2) * 100  # 20% weight on risk (inverted)

        print(f"    Robustness Score: {robustness_score:.1f}/100")

        # Market condition analysis
        profitable_windows = successful[successful['total_return'] > 0]
        if len(profitable_windows) > 0:
            print(f"    Best Window: {profitable_windows.loc[profitable_windows['total_return'].idxmax(), 'window_start'].date()} "
                  f"({profitable_windows['total_return'].max():.2%} return)")


def main():
    analyzer = WalkForwardAnalyzer()
    results = analyzer.run_walk_forward_analysis()

    print("\n🔍 WALK-FORWARD ANALYSIS SUMMARY:")
    successful = results[results['status'] == 'success']

    if len(successful) > 0:
        # Group by strategy for final summary
        strategy_summary = successful.groupby('strategy_name').agg({
            'total_return': ['mean', 'std', 'min', 'max', 'count'],
            'win_rate': ['mean', 'std'],
            'total_trades': 'sum',
            'max_drawdown': lambda x: x.abs().mean()
        }).round(4)

        print("\n📊 STRATEGY ROBUSTNESS SUMMARY:")
        for strategy_name, stats in strategy_summary.iterrows():
            print(f"\n{strategy_name}:")
            print(f"  Windows Tested: {stats[('total_return', 'count')]:.0f}")
            print(f"  Avg Return: {stats[('total_return', 'mean')]:.2%} ± {stats[('total_return', 'std')]:.2%}")
            print(f"  Return Range: {stats[('total_return', 'min')]:.2%} to {stats[('total_return', 'max')]:.2%}")
            print(f"  Avg Win Rate: {stats[('win_rate', 'mean')]:.1%} ± {stats[('win_rate', 'std')]:.1%}")
            print(f"  Avg Drawdown: {stats[('max_drawdown', '<lambda>')]:.2%}")
            print(f"  Total Trades: {stats[('total_trades', 'sum')]:.0f}")

        # Rank strategies by robustness
        print("\n🏆 STRATEGY ROBUSTNESS RANKING:")
        robustness_scores = {}
        for strategy_name in successful['strategy_name'].unique():
            strategy_data = successful[successful['strategy_name'] == strategy_name]
            returns = strategy_data['total_return']
            win_rates = strategy_data['win_rate']
            drawdowns = strategy_data['max_drawdown'].abs()

            # Calculate robustness score
            consistency = (returns > 0).mean()
            avg_return_score = min(abs(returns.mean()) / 0.03, 1.0)  # Normalize to 3% target
            risk_score = 1 - min(drawdowns.mean() / 0.05, 1.0)  # Invert risk

            robustness = (consistency * 0.4 + avg_return_score * 0.4 + risk_score * 0.2) * 100
            robustness_scores[strategy_name] = robustness

        # Sort and display
        sorted_strategies = sorted(robustness_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (strategy, score) in enumerate(sorted_strategies, 1):
            print(f"{i}. {strategy}: {score:.1f}/100 robustness")

if __name__ == "__main__":
    main()
