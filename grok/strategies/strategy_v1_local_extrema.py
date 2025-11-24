"""
Grok Strategy V1: Local Extrema with Trend Filter
Based on tuning results showing local_extrema outperforms fractal
Includes EMA trend filter which improved win rates significantly
"""

import sys
import os
from pathlib import Path

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def run_strategy_v1():
    """
    Strategy V1: Local Extrema (5) + EMA 50 Trend Filter
    Based on tuning results: local_extrema lookback 5 gave best 30m results
    EMA 50 trend filter improved win rates across all timeframes
    """
    print("=" * 60)
    print("GROK STRATEGY V1: Local Extrema + Trend Filter")
    print("Parameters: local_extrema(5), EMA(50), trend_filter=True")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",  # Switch from fractal to local_extrema
        swing_param=5,                 # Based on best 30m results
        trend_ma_type="EMA",
        trend_ma_period=50,           # EMA 50 performed best in tuning
        trend_filter=True,            # Enable trend filter (key improvement)
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


def run_strategy_v1_crypto_optimized():
    """
    Strategy V1 Crypto: Wider stops/targets for crypto volatility
    """
    print("=" * 60)
    print("GROK STRATEGY V1 CRYPTO: Wider stops for BTC volatility")
    print("Parameters: local_extrema(5), EMA(50), wider SL/TP")
    print("=" * 60)

    results = backtest_fib_strategy(
        interval="5m",
        swing_method="local_extrema",
        swing_param=5,
        trend_ma_type="EMA",
        trend_ma_period=50,
        trend_filter=True,
        entry_retrace=0.618,
        sl_retrace=1.0,      # Wider stop loss (from 0.786)
        tp_retrace=0.5,      # Wider take profit (from 0.236)
        tp1_retrace=0.618,   # Adjust TP1 for wider range
        tp1_frac=0.5,
        move_stop_to_be=True,
        verbose=False,
    )

    print_full_report(results)
    return results


if __name__ == "__main__":
    # Run both variations
    results_v1 = run_strategy_v1()
    print("\n\n")
    results_v1_crypto = run_strategy_v1_crypto_optimized()

    # Summary comparison
    print("=" * 60)
    print("STRATEGY V1 COMPARISON SUMMARY")
    print("=" * 60)
    print("<30")
    print("<30")
