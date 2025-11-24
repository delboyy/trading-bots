"""
Grok Strategy V3: Swing Detection Optimization
Tests different swing parameters and trend configurations
Based on tuning results showing different swing methods work better
"""

import sys
import os
from pathlib import Path

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def run_strategy_v3a_zigzag_optimized():
    """
    Strategy V3A: Zigzag with optimized parameters
    Based on tuning: zigzag 0.5% deviation gave best 5m results
    """
    print("=" * 60)
    print("GROK STRATEGY V3A: Optimized Zigzag")
    print("Parameters: zigzag(0.005), EMA(50), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="zigzag",
        swing_param=0.005,     # 0.5% - best zigzag from tuning
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


def run_strategy_v3b_local_extrema_variations():
    """
    Strategy V3B: Test different local_extrema lookbacks
    Based on tuning: lookback 15 gave best 15m results
    """
    print("=" * 60)
    print("GROK STRATEGY V3B: Local Extrema Lookback 15")
    print("Parameters: local_extrema(15), EMA(50), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
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


def run_strategy_v3c_trend_optimized():
    """
    Strategy V3C: Different trend configurations
    Based on tuning: EMA 30 with different TP settings worked well
    """
    print("=" * 60)
    print("GROK STRATEGY V3C: Shorter EMA Trend")
    print("Parameters: local_extrema(5), EMA(30), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",
        swing_param=5,
        trend_ma_type="EMA",
        trend_ma_period=30,    # Shorter EMA from tuning trials
        trend_filter=True,
        entry_retrace=0.5,     # From best tuning trials
        sl_retrace=0.786,
        tp_retrace=0.5,        # Wider TP from tuning
        tp1_retrace=0.618,
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


def run_strategy_v3d_no_trend_filter():
    """
    Strategy V3D: No trend filter for comparison
    Sometimes no filter allows more trades and different opportunities
    """
    print("=" * 60)
    print("GROK STRATEGY V3D: No Trend Filter")
    print("Parameters: local_extrema(5), trend_filter=False")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",
        swing_param=5,
        trend_filter=False,    # No trend filter
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


if __name__ == "__main__":
    # Run all swing optimization variations
    results_v3a = run_strategy_v3a_zigzag_optimized()
    print("\n\n")
    results_v3b = run_strategy_v3b_local_extrema_variations()
    print("\n\n")
    results_v3c = run_strategy_v3c_trend_optimized()
    print("\n\n")
    results_v3d = run_strategy_v3d_no_trend_filter()

    # Summary comparison
    print("=" * 60)
    print("STRATEGY V3 SWING OPTIMIZATION COMPARISON SUMMARY")
    print("=" * 60)
    print("<30")
    print("<30")
    print("<30")
    print("<30")
