"""
Grok Strategy V2: Retracement Level Optimization
Based on tuning results showing different entry/stop levels work better
Tests various retracement combinations for better win rates
"""

import sys
import os
from pathlib import Path

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def run_strategy_v2a_conservative():
    """
    Strategy V2A: Conservative retracements
    Based on tuning showing 0.5 entry/0.5 TP performed well
    """
    print("=" * 60)
    print("GROK STRATEGY V2A: Conservative Retracements")
    print("Parameters: entry=0.5, SL=0.786, TP=0.5, TP1=0.618")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",
        swing_param=5,
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.5,      # More conservative entry
        sl_retrace=0.786,       # Standard stop
        tp_retrace=0.5,         # Wider profit target
        tp1_retrace=0.618,      # TP1 between entry and TP2
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


def run_strategy_v2b_aggressive():
    """
    Strategy V2B: Aggressive entries with quick profits
    """
    print("=" * 60)
    print("GROK STRATEGY V2B: Aggressive Entries")
    print("Parameters: entry=0.382, SL=0.618, TP=0.236, TP1=0.5")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",
        swing_param=5,
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.382,    # Aggressive entry
        sl_retrace=0.618,       # Tighter stop
        tp_retrace=0.236,       # Quick profit target
        tp1_retrace=0.5,        # TP1 in middle
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


def run_strategy_v2c_breakout():
    """
    Strategy V2C: Breakout style - entry near swing, wider targets
    """
    print("=" * 60)
    print("GROK STRATEGY V2C: Breakout Style")
    print("Parameters: entry=0.236, SL=0.5, TP=0.786, TP1=0.618")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",
        swing_param=5,
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.236,    # Very aggressive entry near swing
        sl_retrace=0.5,         # Moderate stop
        tp_retrace=0.786,       # Very wide profit target
        tp1_retrace=0.618,      # TP1 at fib level
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


if __name__ == "__main__":
    # Run all retracement variations
    results_v2a = run_strategy_v2a_conservative()
    print("\n\n")
    results_v2b = run_strategy_v2b_aggressive()
    print("\n\n")
    results_v2c = run_strategy_v2c_breakout()

    # Summary comparison
    print("=" * 60)
    print("STRATEGY V2 RETRACEMENT COMPARISON SUMMARY")
    print("=" * 60)
    print("<30")
    print("<30")
    print("<30")
