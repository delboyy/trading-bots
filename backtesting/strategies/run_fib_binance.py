import os
import sys
import time
from pathlib import Path
import ccxt
import pandas as pd

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def fetch_binance_ohlcv(symbol: str, timeframe: str, days: int = 90) -> pd.DataFrame:
    exchange = ccxt.binance()
    since = exchange.milliseconds() - days * 24 * 60 * 60 * 1000
    all_bars = []
    limit = 1500
    while True:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not bars:
            break
        all_bars.extend(bars)
        print(f"Fetched {len(all_bars)} bars up to {pd.to_datetime(bars[-1][0], unit='ms', utc=True)}")
        since = bars[-1][0] + 1
        # Pace to respect rate limits
        time.sleep(0.2)
        # Stop if we hit current time
        if since >= exchange.milliseconds():
            break
    if not all_bars:
        return pd.DataFrame()

    df = pd.DataFrame(
        all_bars,
        columns=["Time", "Open", "High", "Low", "Close", "Volume"],
    )
    df["Time"] = pd.to_datetime(df["Time"], unit="ms", utc=True)
    return df


def main():
    symbol = os.getenv("BINANCE_SYMBOL", "BTC/USDT")
    timeframe = os.getenv("BINANCE_TIMEFRAME", "5m")
    days = int(os.getenv("BINANCE_DAYS", "90"))
    refresh = os.getenv("BINANCE_REFRESH", "").lower() in {"1", "true", "yes"}
    verbose = os.getenv("BACKTEST_VERBOSE", "").lower() in {"1", "true", "yes"}

    out_file = Path(f"data/processed/binance_{symbol.replace('/', '')}_{timeframe}.parquet")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if out_file.exists() and not refresh:
        print(f"Loading cached data from {out_file}")
        df = pd.read_parquet(out_file)
        print(f"Loaded rows={len(df)} range {df['Time'].min()} -> {df['Time'].max()}")
    else:
        df = fetch_binance_ohlcv(symbol, timeframe, days)
        if df.empty:
            print("No data fetched from Binance.")
            return
        df.to_parquet(out_file, index=False)
        print(f"Saved Binance data to {out_file} rows={len(df)} range {df['Time'].min()} -> {df['Time'].max()}")

    res = backtest_fib_strategy(
        interval=timeframe,
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
        sl_retrace=0.736,
        verbose=verbose,
    )
    print_full_report(res)


if __name__ == "__main__":
    main()
