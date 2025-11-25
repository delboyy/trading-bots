#!/usr/bin/env python3
"""
IBKR 2-Year Validation Backtest
Tests top winning strategies on 2 years of IBKR data vs 60-day Yahoo data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')

from shared_strategies.scalping_strategy import ScalpingStrategy


class IBKR2YearValidator:
    def __init__(self):
        self.data_dir = Path('data/processed')
        self.ibkr_dir = self.data_dir / 'ibkr_2year'
        self.csv_data_dir = Path('data')  # Where CSV files are saved

        # Top 5 winners to validate on 2-year IBKR data
        self.top5_winners = [
            {
                'name': 'Time-Based TSLA 15m',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {'momentum_period': 7},
                'expected_return_60d': 0.3615,
                'expected_win_rate_60d': 0.623
            },
            {
                'name': 'Volume Breakout AMD 5m',
                'strategy': 'volume_breakout',
                'symbol': 'AMD',
                'interval': '5m',
                'params': {'volume_multiplier': 1.8},
                'expected_return_60d': 0.1375,
                'expected_win_rate_60d': 0.667
            },
            {
                'name': 'RSI GOOGL 15m',
                'strategy': 'rsi_scalping',
                'symbol': 'GOOGL',
                'interval': '15m',
                'params': {'rsi_period': 7, 'rsi_oversold': 25, 'rsi_overbought': 75},
                'expected_return_60d': 0.0950,
                'expected_win_rate_60d': 0.552
            },
            {
                'name': 'Candlestick DIA 5m',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {'volume_multiplier': 1.4},
                'expected_return_60d': 0.0716,
                'expected_win_rate_60d': 0.744
            },
            {
                'name': 'RSI MSFT 5m',
                'strategy': 'rsi_scalping',
                'symbol': 'MSFT',
                'interval': '5m',
                'params': {},  # Default parameters
                'expected_return_60d': 0.0400,
                'expected_win_rate_60d': 0.537
            }
        ]

    def load_ibkr_data(self, symbol: str, interval: str) -> pd.DataFrame:
        """Load IBKR 2-year data for a symbol"""
        # Look for CSV files in the main data directory
        interval_clean = interval.replace(' ', '').replace('m', 'mins')
        filename = f"{symbol}_{interval_clean}_2y.csv"
        filepath = self.csv_data_dir / filename

        print(f"Looking for CSV file: {filepath}")

        if filepath.exists():
            print(f"Loading IBKR CSV data: {filename}")
            df = pd.read_csv(filepath)

            # Set date column as index if it exists (IBKR CSV format)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], utc=True)
                # Convert to timezone-naive for compatibility with strategy
                df['date'] = df['date'].dt.tz_convert('US/Eastern').dt.tz_localize(None)
                df.set_index('date', inplace=True)
                # Rename columns to match our strategy format
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })

            print(f"Loaded {len(df)} rows of IBKR data")
            print(f"Date range: {df.index[0]} to {df.index[-1]}")
            return df

        print(f"CSV file not found: {filepath}")

        # Fallback: look for parquet files in ibkr_2year directory
        patterns = [
            f"ibkr_{symbol}_{interval.replace('m', 'mins')}_2year.parquet",
            f"ibkr_{symbol}_{interval}_2year.parquet"
        ]

        for pattern in patterns:
            filepath = self.ibkr_dir / pattern
            if filepath.exists():
                print(f"Loading IBKR parquet data: {pattern}")
                df = pd.read_parquet(filepath)

                # Set Time column as index if it exists
                if 'Time' in df.columns:
                    df['Time'] = pd.to_datetime(df['Time'])
                    df.set_index('Time', inplace=True)
                    # Rename columns to match our strategy format
                    df = df.rename(columns={
                        'Open': 'Open',
                        'High': 'High',
                        'Low': 'Low',
                        'Close': 'Close',
                        'Volume': 'Volume'
                    })

                print(f"Loaded {len(df)} rows of IBKR data")
                print(f"Date range: {df.index[0]} to {df.index[-1]}")
                return df

        print(f"No IBKR data found for {symbol} {interval}")
        return pd.DataFrame()

    def load_yahoo_comparison(self, symbol: str, interval: str) -> pd.DataFrame:
        """Load Yahoo 60-day data for comparison"""
        filename = f"{symbol}_{interval}_scalping.parquet"
        filepath = self.data_dir / filename

        if filepath.exists():
            df = pd.read_parquet(filepath)
            print(f"Loaded Yahoo comparison data: {len(df)} rows")
            return df

        print(f"No Yahoo comparison data for {symbol} {interval}")
        return pd.DataFrame()

    def run_strategy_comparison(self, strategy_config: dict) -> dict:
        """Run strategy on both IBKR 2-year and Yahoo 60-day data"""
        strategy_name = strategy_config['name']
        strategy_type = strategy_config['strategy']
        symbol = strategy_config['symbol']
        interval = strategy_config['interval']
        params = strategy_config['params']

        print(f"\n🔄 Comparing {strategy_name}...")

        results = {
            'strategy_name': strategy_name,
            'symbol': symbol,
            'interval': interval,
            'ibkr_2year': {},
            'yahoo_60day': {}
        }

        # Test on IBKR 2-year data
        ibkr_data = self.load_ibkr_data(symbol, interval)
        if not ibkr_data.empty:
            try:
                print(f"Running backtest on {len(ibkr_data)} data points...")
                strategy = ScalpingStrategy(ibkr_data, strategy_type=strategy_type, **params)
                ibkr_results = strategy.backtest()
                print("Backtest completed successfully")

                results['ibkr_2year'] = {
                    'total_return': ibkr_results.get('total_return', 0),
                    'win_rate': ibkr_results.get('win_rate', 0),
                    'total_trades': ibkr_results.get('total_trades', 0),
                    'max_drawdown': ibkr_results.get('max_drawdown', 0),
                    'sharpe_ratio': ibkr_results.get('sharpe_ratio', 0),
                    'data_points': len(ibkr_data),
                    'date_range': f"{ibkr_data.index[0].date()} to {ibkr_data.index[-1].date()}",
                    'status': 'success'
                }
            except Exception as e:
                print(f"Error during backtest: {e}")
                import traceback
                traceback.print_exc()
                results['ibkr_2year'] = {'status': 'error', 'error': str(e)}
        else:
            results['ibkr_2year'] = {'status': 'no_data'}

        # Test on Yahoo 60-day data for comparison
        yahoo_data = self.load_yahoo_comparison(symbol, interval)
        if not yahoo_data.empty:
            try:
                strategy = ScalpingStrategy(yahoo_data, strategy_type=strategy_type, **params)
                yahoo_results = strategy.backtest()

                results['yahoo_60day'] = {
                    'total_return': yahoo_results.get('total_return', 0),
                    'win_rate': yahoo_results.get('win_rate', 0),
                    'total_trades': yahoo_results.get('total_trades', 0),
                    'max_drawdown': yahoo_results.get('max_drawdown', 0),
                    'sharpe_ratio': yahoo_results.get('sharpe_ratio', 0),
                    'data_points': len(yahoo_data),
                    'status': 'success'
                }
            except Exception as e:
                results['yahoo_60day'] = {'status': 'error', 'error': str(e)}
        else:
            results['yahoo_60day'] = {'status': 'no_data'}

        return results

    def run_2year_validation(self):
        """Run comprehensive 2-year vs 60-day validation"""
        print("🏛️ IBKR 2-YEAR vs YAHOO 60-DAY VALIDATION")
        print("=" * 70)
        print("Comparing Top 5 Winners on IBKR 2-Year Data vs Yahoo 60-Day Data")
        print("=" * 70)

        all_results = []

        for winner in self.top5_winners:
            result = self.run_strategy_comparison(winner)
            all_results.append(result)

            # Print immediate results
            print(f"\n📊 {result['strategy_name']} Results:")

            # IBKR 2-year results
            if result['ibkr_2year'].get('status') == 'success':
                ibkr = result['ibkr_2year']
                print("  IBKR 2-Year Data:")
                print(f"    Return: {ibkr['total_return']:.2%}, Win Rate: {ibkr['win_rate']:.1%}")
                print(f"    Trades: {ibkr['total_trades']}, Max DD: {ibkr['max_drawdown']:.2%}")
                print(f"    Data: {ibkr['data_points']} points ({ibkr['date_range']})")
            else:
                print(f"  IBKR 2-Year: {result['ibkr_2year'].get('status', 'unknown')}")

            # Yahoo 60-day results
            if result['yahoo_60day'].get('status') == 'success':
                yahoo = result['yahoo_60day']
                print("  Yahoo 60-Day Data:")
                print(f"    Return: {yahoo['total_return']:.2%}, Win Rate: {yahoo['win_rate']:.1%}")
                print(f"    Trades: {yahoo['total_trades']}, Max DD: {yahoo['max_drawdown']:.2%}")
                print(f"    Data: {yahoo['data_points']} points")
            else:
                print(f"  Yahoo 60-Day: {result['yahoo_60day'].get('status', 'unknown')}")

            # Comparison
            if (result['ibkr_2year'].get('status') == 'success' and
                result['yahoo_60day'].get('status') == 'success'):

                ibkr_return = result['ibkr_2year']['total_return']
                yahoo_return = result['yahoo_60day']['total_return']
                return_diff = ibkr_return - yahoo_return

                ibkr_win_rate = result['ibkr_2year']['win_rate']
                yahoo_win_rate = result['yahoo_60day']['win_rate']
                win_rate_diff = ibkr_win_rate - yahoo_win_rate

                print("  Comparison (2-Year vs 60-Day):")
                print(f"    Return Diff: {return_diff:+.2%}")
                print(f"    Win Rate Diff: {win_rate_diff:+.1%}")

        # Save comprehensive results
        results_df = pd.DataFrame(all_results)
        results_df.to_csv('backtesting_tests/ibkr_2year_validation_results.csv', index=False)

        print("\n🎯 VALIDATION COMPLETE")
        print(f"Total strategies tested: {len(all_results)}")

        # Summary analysis
        successful_ibkr = sum(1 for r in all_results if r['ibkr_2year'].get('status') == 'success')
        successful_yahoo = sum(1 for r in all_results if r['yahoo_60day'].get('status') == 'success')

        print(f"IBKR 2-year tests successful: {successful_ibkr}")
        print(f"Yahoo 60-day tests successful: {successful_yahoo}")

        # Performance comparison
        ibkr_returns = [r['ibkr_2year']['total_return'] for r in all_results
                       if r['ibkr_2year'].get('status') == 'success']
        yahoo_returns = [r['yahoo_60day']['total_return'] for r in all_results
                        if r['yahoo_60day'].get('status') == 'success']

        if ibkr_returns and yahoo_returns:
            print("\n📊 OVERALL PERFORMANCE COMPARISON:")
            print(f"Average IBKR 2-Year Return: {np.mean(ibkr_returns):.2%}")
            print(f"Average Yahoo 60-Day Return: {np.mean(yahoo_returns):.2%}")
            print(f"Average Return Difference: {np.mean(ibkr_returns) - np.mean(yahoo_returns):+.2%}")

        return results_df


def main():
    validator = IBKR2YearValidator()
    results = validator.run_2year_validation()

    # Final deployment recommendation
    print("\n🎯 DEPLOYMENT RECOMMENDATION BASED ON 2-YEAR DATA:")
    successful_strategies = []
    for result in results.to_dict('records'):
        if result['ibkr_2year'].get('status') == 'success':
            ibkr_return = result['ibkr_2year']['total_return']
            if ibkr_return > 0.03:  # 3%+ return on 2-year data
                successful_strategies.append({
                    'name': result['strategy_name'],
                    'return': ibkr_return,
                    'symbol': result['symbol']
                })

    if successful_strategies:
        successful_strategies.sort(key=lambda x: x['return'], reverse=True)
        print(f"✅ {len(successful_strategies)} strategies exceed 3% return threshold on 2-year IBKR data:")

        for i, strategy in enumerate(successful_strategies, 1):
            print(f"  {i}. {strategy['name']} ({strategy['symbol']}): {strategy['return']:.2%} return")

        print("\n🚀 RECOMMENDED FOR LIVE DEPLOYMENT")
    else:
        print("⚠️  No strategies exceed 3% return threshold on 2-year data")
        print("   Consider parameter optimization or different strategies")

if __name__ == "__main__":
    main()
