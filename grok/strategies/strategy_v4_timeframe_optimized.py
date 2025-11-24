"""
Grok Strategy V4: Timeframe Optimization
Higher timeframes performed much better in tuning results
15m and 30m had positive returns while 5m was always negative
"""

import sys
import os
from pathlib import Path

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def run_strategy_v4a_15m_optimized():
    """
    Strategy V4A: 15m timeframe with best parameters from tuning
    Best 15m: local_extrema lookback 15, EMA 50
    """
    print("=" * 60)
    print("GROK STRATEGY V4A: 15m Optimized")
    print("Parameters: 15m, local_extrema(15), EMA(50), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="15m",
        swing_method="local_extrema",
        swing_param=15,        # Best from 15m tuning
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.618,
        sl_retrace=0.786,
        tp_retrace=0.236,
        tp1_retrace=0.382,
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


def run_strategy_v4b_30m_optimized():
    """
    Strategy V4B: 30m timeframe with best parameters from tuning
    Best 30m: local_extrema lookback 5, EMA 50
    """
    print("=" * 60)
    print("GROK STRATEGY V4B: 30m Optimized")
    print("Parameters: 30m, local_extrema(5), EMA(50), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="30m",
        swing_method="local_extrema",
        swing_param=5,         # Best from 30m tuning
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.618,
        sl_retrace=0.786,
        tp_retrace=0.236,
        tp1_retrace=0.382,
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


def run_strategy_v4c_1h_conservative():
    """
    Strategy V4C: 1h timeframe for even longer-term trends
    Using conservative parameters for hourly charts
    """
    print("=" * 60)
    print("GROK STRATEGY V4C: 1h Conservative")
    print("Parameters: 1h, local_extrema(5), EMA(50), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="1h",
        swing_method="local_extrema",
        swing_param=5,
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.618,
        sl_retrace=0.786,
        tp_retrace=0.236,
        tp1_retrace=0.382,
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


def run_strategy_v4d_15m_crypto_style():
    """
    Strategy V4D: 15m with crypto-optimized retracements
    Wider stops and targets for crypto volatility
    """
    print("=" * 60)
    print("GROK STRATEGY V4D: 15m Crypto Style")
    print("Parameters: 15m, local_extrema(15), EMA(50), wider SL/TP")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="15m",
        swing_method="local_extrema",
        swing_param=15,
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.5,     # More conservative entry
        sl_retrace=1.0,        # Wider stop for crypto
        tp_retrace=0.5,        # Wider profit target
        tp1_retrace=0.618,     # TP1 between entry and TP2
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


if __name__ == "__main__":
    # Run all timeframe variations
    results_v4a = run_strategy_v4a_15m_optimized()
    print("\n\n")
    results_v4b = run_strategy_v4b_30m_optimized()
    print("\n\n")
    results_v4c = run_strategy_v4c_1h_conservative()
    print("\n\n")
    results_v4d = run_strategy_v4d_15m_crypto_style()

    # Summary comparison
    print("=" * 60)
    print("STRATEGY V4 TIMEFRAME OPTIMIZATION COMPARISON SUMMARY")
    print("=" * 60)
    print("<30")
    print("<30")
    print("<30")
    print("<30")
