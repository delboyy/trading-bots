import os
import sys
from pathlib import Path
import pandas as pd

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def main():
    data_file = Path(os.getenv("DATA_FILE", "data/processed/GLD_5mins.parquet"))
    interval = os.getenv("INTERVAL", "5m")

    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        return

    df = pd.read_parquet(data_file)
    if "Time" in df.columns:
        df["Time"] = pd.to_datetime(df["Time"])

    res = backtest_fib_strategy(
        interval=interval,
        data=df,
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
    )
    print_full_report(res)


if __name__ == "__main__":
    main()
