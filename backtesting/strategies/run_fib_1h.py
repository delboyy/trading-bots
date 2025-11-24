import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report

def run():
    print("Running 1h Backtest...")
    # Using optimized settings: ZigZag 1%, EMA 50
    results = backtest_fib_strategy(
        interval="1h",
        swing_method="zigzag",
        swing_param=0.01,
        trend_ma_type="EMA",
        trend_ma_period=50,
        verbose=False
    )
    print_full_report(results)

if __name__ == "__main__":
    run()
