#!/usr/bin/env python3
"""
Strategy Audit: Quick backtest of all strategies to identify unprofitable ones
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from pathlib import Path
import sys
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import our custom modules
from shared_utils.data_loader import load_ohlcv_yfinance

def quick_backtest_strategy(strategy_name: str, symbol: str = "SPY", period: str = "1y", interval: str = "1d") -> dict:
    """Quick backtest of a strategy"""
    try:
        start_time = time.time()

        # Load data
        data = load_ohlcv_yfinance(symbol, period=period, interval=interval)

        # Import strategy dynamically
        if strategy_name == 'mean_reversion':
            from shared_strategies.mean_reversion import Strategy as MeanReversionStrategy
            strategy_class = MeanReversionStrategy
        elif strategy_name == 'momentum':
            from shared_strategies.momentum import Strategy as MomentumStrategy
            strategy_class = MomentumStrategy
        elif strategy_name == 'breakout':
            from shared_strategies.breakout import Strategy as BreakoutStrategy
            strategy_class = BreakoutStrategy
        elif strategy_name == 'volatility_breakout':
            from shared_strategies.volatility_breakout import Strategy as VolatilityBreakoutStrategy
            strategy_class = VolatilityBreakoutStrategy
        else:
            return {'error': f'Strategy {strategy_name} not found'}

        strategy = strategy_class(data)

        # Generate signals
        signals = strategy.generate_signals()

        # Run backtest
        pf = vbt.Portfolio.from_signals(
            data["Close"],
            entries=signals == 1,
            exits=signals == -1,
            init_cash=100_000,
            fees=0.001,
            freq='D'
        )

        # Calculate metrics
        total_return = pf.total_return()
        max_drawdown = pf.max_drawdown()
        win_rate = pf.trades.win_rate()
        total_trades = len(pf.trades)

        elapsed = time.time() - start_time

        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'period': period,
            'total_return': float(total_return),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'total_trades': int(total_trades),
            'sharpe_ratio': float(pf.sharpe_ratio()),
            'profit_factor': float(pf.trades.profit_factor()),
            'test_time': elapsed,
            'status': 'success'
        }

    except Exception as e:
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'error': str(e),
            'status': 'failed'
        }

def test_fib_strategies():
    """Test the old Fibonacci strategies"""
    print("\n🌀 TESTING FIBONACCI STRATEGIES")
    print("=" * 60)

    fib_results = []

    # Test different fib strategies with different timeframes
    fib_tests = [
        ('fib_gold_backtest', 'BTC-USD', '3mo', '5m'),
        ('fib_gold_backtest', 'SPY', '1y', '1d'),
        ('fib_fractal_live', 'ETH-USD', '3mo', '1h'),
    ]

    for strategy_file, symbol, period, interval in fib_tests:
        try:
            print(f"\n🔍 Testing {strategy_file} on {symbol} {period} {interval}")

            # Import and run the strategy
            if strategy_file == 'fib_gold_backtest':
                from backtesting.strategies.fib_gold_backtest import backtest_fib_strategy
                result = backtest_fib_strategy(
                    interval=interval,
                    data=None,  # Will fetch data
                    swing_method="fractal",
                    swing_param=3,
                    trend_filter=False,
                    trend_ma_type="EMA",
                    trend_ma_period=50,
                    entry_retrace=0.618,
                    tp1_retrace=0.382,
                    tp1_frac=0.5,
                    tp_retrace=0.236,
                    sl_retrace=0.5,
                    verbose=False,
                    fee_rate=0.002
                )
                fib_results.append({
                    'strategy': f'fib_{strategy_file}_{symbol}_{interval}',
                    'total_return': result.get('total_return', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'win_rate': result.get('win_rate', 0),
                    'total_trades': result.get('total_trades', 0),
                    'status': 'success'
                })
            elif strategy_file == 'fib_fractal_live':
                from shared_strategies.fib_fractal_live import FibFractalLiveStrategy
                data = load_ohlcv_yfinance(symbol, period=period, interval=interval)
                strategy = FibFractalLiveStrategy(data)
                signals = strategy.generate_signals()

                pf = vbt.Portfolio.from_signals(
                    data["Close"],
                    entries=signals == 1,
                    exits=signals == -1,
                    init_cash=100_000,
                    fees=0.001
                )

                fib_results.append({
                    'strategy': f'fib_fractal_live_{symbol}_{interval}',
                    'total_return': float(pf.total_return()),
                    'max_drawdown': float(pf.max_drawdown()),
                    'win_rate': float(pf.trades.win_rate()),
                    'total_trades': len(pf.trades),
                    'status': 'success'
                })

        except Exception as e:
            print(f"❌ Failed: {e}")
            fib_results.append({
                'strategy': f'{strategy_file}_{symbol}_{interval}',
                'error': str(e),
                'status': 'failed'
            })

    return fib_results

def main():
    """Main audit function"""
    print("🔍 STRATEGY AUDIT: Finding Unprofitable Strategies")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")

    all_results = []

    # Test shared strategies
    print("\n📊 TESTING SHARED STRATEGIES")
    print("=" * 60)

    shared_strategies = ['mean_reversion', 'momentum', 'breakout', 'volatility_breakout']
    test_assets = ['SPY', 'QQQ', 'GLD', 'SLV']

    for strategy in shared_strategies:
        for asset in test_assets:
            print(f"🔍 Testing {strategy} on {asset}")
            result = quick_backtest_strategy(strategy, symbol=asset, period="1y", interval="1d")
            all_results.append(result)

            if result['status'] == 'success':
                print(".3f")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")

    # Test fib strategies
    fib_results = test_fib_strategies()
    all_results.extend(fib_results)

    # Analyze results
    print("\n📈 AUDIT RESULTS")
    print("=" * 80)

    successful_results = [r for r in all_results if r['status'] == 'success']
    failed_results = [r for r in all_results if r['status'] == 'failed']

    print(f"Total strategies tested: {len(all_results)}")
    print(f"Successful: {len(successful_results)}")
    print(f"Failed: {len(failed_results)}")

    if successful_results:
        # Sort by total return
        sorted_results = sorted(successful_results, key=lambda x: x['total_return'])

        print("\n🎯 TOP PERFORMERS:")
        for result in sorted_results[-5:]:
            print(".3f")

        print("\n💸 WORST PERFORMERS (UNPROFITABLE):")
        unprofitable = [r for r in sorted_results if r['total_return'] < -0.05]  # Less than -5%
        for result in unprofitable[:10]:  # Show top 10 worst
            print(".3f")

        print("\n⚠️  HIGH RISK STRATEGIES (High DD):")
        high_dd = [r for r in sorted_results if r['max_drawdown'] > 0.15]  # Over 15% DD
        for result in high_dd:
            print(".3f")

    # Save detailed results
    results_df = pd.DataFrame(all_results)
    results_df.to_csv('strategy_audit_results.csv', index=False)
    print("\n💾 Detailed results saved to: strategy_audit_results.csv")
    # Summary recommendations
    print("\n🎯 RECOMMENDATIONS:")
    print("=" * 40)

    if successful_results:
        profitable_strategies = [r for r in successful_results if r['total_return'] > 0.1]  # Over 10%
        print(f"✅ Keep {len(profitable_strategies)} highly profitable strategies")

        moderately_profitable = [r for r in successful_results if 0.05 <= r['total_return'] <= 0.1]
        print(f"⚠️  Review {len(moderately_profitable)} moderately profitable strategies")

        unprofitable_strategies = [r for r in successful_results if r['total_return'] < 0]
        print(f"❌ Remove {len(unprofitable_strategies)} unprofitable strategies")

        high_risk = [r for r in successful_results if r['max_drawdown'] > 0.2]
        print(f"🚨 High-risk strategies needing position size reduction: {len(high_risk)}")

    print("\n📋 FAILED STRATEGIES TO FIX:")
    for result in failed_results:
        print(f"❌ {result['strategy']}: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
