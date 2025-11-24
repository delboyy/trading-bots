#!/usr/bin/env python3
"""
Quick audit of key original strategies
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_fib_strategy(timeframe, swing_method="zigzag", swing_param=0.01):
    """Test a fib strategy directly"""
    try:
        start_time = time.time()

        from backtesting.strategies.fib_gold_backtest import backtest_fib_strategy

        result = backtest_fib_strategy(
            interval=timeframe,
            swing_method=swing_method,
            swing_param=swing_param,
            trend_ma_type="EMA",
            trend_ma_period=50,
            verbose=False,
        )

        elapsed = time.time() - start_time

        return {
            'strategy': f'fib_{timeframe}_{swing_method}',
            'total_return': result.get('total_return', 0),
            'max_drawdown': result.get('max_drawdown', 0),
            'win_rate': result.get('win_rate', 0),
            'total_trades': result.get('total_trades', 0),
            'status': 'success',
            'test_time': elapsed
        }

    except Exception as e:
        return {
            'strategy': f'fib_{timeframe}_{swing_method}',
            'error': str(e),
            'status': 'failed'
        }

def main():
    print("🔍 QUICK AUDIT: Key Original Strategies")
    print("=" * 60)

    # Test the key fib strategies that were originally created
    test_cases = [
        ("5m", "zigzag", 0.01),
        ("15m", "zigzag", 0.01),
        ("30m", "zigzag", 0.01),
        ("1h", "zigzag", 0.01),
        ("4h", "zigzag", 0.01),
        ("5m", "fractal", 3),
        ("1h", "fractal", 3),
        ("1d", "local_extrema", 5),
    ]

    results = []

    for timeframe, swing_method, swing_param in test_cases:
        print(f"🔍 Testing Fib {timeframe} {swing_method}...")
        result = test_fib_strategy(timeframe, swing_method, swing_param)
        results.append(result)

        if result['status'] == 'success':
            ret = result.get('total_return', 0)
            win_rate = result.get('win_rate', 0)
            trades = result.get('total_trades', 0)
            print(".3f")
        else:
            print(f"❌ Failed: {result.get('error', 'unknown')}")

    # Analyze results
    print("\n📈 QUICK AUDIT RESULTS")
    print("=" * 60)

    successful_results = [r for r in results if r['status'] == 'success']

    if successful_results:
        # Sort by total return
        sorted_results = sorted(successful_results, key=lambda x: x['total_return'])

        print("🎯 TOP PERFORMERS:")
        for result in sorted_results[-5:]:
            ret = result.get('total_return', 0)
            win_rate = result.get('win_rate', 0)
            trades = result.get('total_trades', 0)
            print(".3f")

        print("\n💸 WORST PERFORMERS (UNPROFITABLE):")
        unprofitable = [r for r in sorted_results if r['total_return'] < -0.05]
        for result in unprofitable[:5]:
            ret = result.get('total_return', 0)
            print(".3f")

        print("\n⚠️  ANALYSIS:")
        profitable = [r for r in successful_results if r['total_return'] > 0.1]
        high_win = [r for r in successful_results if r['win_rate'] > 0.8]

        print(f"✅ Highly profitable strategies: {len(profitable)}")
        print(f"🎯 High win rate strategies: {len(high_win)}")
        print(f"❌ Unprofitable strategies: {len(unprofitable)}")

if __name__ == "__main__":
    main()
