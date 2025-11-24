"""
Chunked downloader for Binance OHLCV using CCXT.
Defaults: BTC/USDT, 5m bars, ~60 months back in 30-day slices.
Saves raw parquet chunks to data/raw/binance_<SYMBOL>_<TF>/,
merges to data/processed/binance_<SYMBOL>_<TF>.parquet.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import ccxt


def fetch_chunk(exchange, symbol: str, timeframe: str, since_ms: int, limit: int = 1500):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        return bars
    except Exception as e:
        return []


def main():
    symbol = os.getenv("BINANCE_SYMBOL", "BTC/USDT")
    timeframe = os.getenv("BINANCE_TIMEFRAME", "5m")
    months = int(os.getenv("BINANCE_MONTHS", "60"))
    days_per_chunk = int(os.getenv("BINANCE_DAYS_PER_CHUNK", "30"))
    sleep_s = float(os.getenv("BINANCE_SLEEP", "0.2"))

    raw_dir = Path("data/raw") / f"binance_{symbol.replace('/', '')}_{timeframe}"
    proc_path = Path("data/processed") / f"binance_{symbol.replace('/', '')}_{timeframe}.parquet"
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_path.parent.mkdir(parents=True, exist_ok=True)

    exchange = ccxt.binance({"enableRateLimit": True})
    now = exchange.milliseconds()
    days_total = int(months * 30.4)
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=days_total)).timestamp() * 1000)

    all_paths = []
    cursor = start_ms
    chunk_ms = days_per_chunk * 24 * 60 * 60 * 1000
    idx = 0
    while cursor < now:
        idx += 1
        bars = fetch_chunk(exchange, symbol, timeframe, since_ms=cursor)
        if not bars:
            print(f"[{idx}] empty chunk at {datetime.fromtimestamp(cursor/1000, tz=timezone.utc)}")
            cursor += chunk_ms
            time.sleep(sleep_s)
            continue
        df = pd.DataFrame(bars, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
        df["Time"] = pd.to_datetime(df["Time"], unit="ms", utc=True)
        chunk_start = df["Time"].min()
        chunk_end = df["Time"].max()
        fpath = raw_dir / f"{symbol.replace('/','')}_{timeframe}_{chunk_start.strftime('%Y%m%d')}.parquet"
        df.to_parquet(fpath, index=False)
        all_paths.append(fpath)
        print(f"[{idx}] {chunk_start} -> {chunk_end} rows={len(df)} saved={fpath.name}")
        cursor = int((chunk_end + pd.Timedelta(minutes=5)).timestamp() * 1000)
        time.sleep(sleep_s)

    if not all_paths:
        print("No chunks downloaded.")
        return

    dfs = [pd.read_parquet(p) for p in all_paths]
    df_all = pd.concat(dfs, ignore_index=True)
    df_all.drop_duplicates(subset=["Time"], inplace=True)
    df_all.sort_values("Time", inplace=True)
    df_all = df_all[["Time", "Open", "High", "Low", "Close", "Volume"]]
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    aligned = df_all[(df_all["Time"] - epoch).dt.total_seconds() % (5 * 60) == 0]
    df_all = aligned
    df_all.to_parquet(proc_path, index=False)
    print(f"Merged {len(all_paths)} chunks -> {len(df_all)} rows saved to {proc_path}")
    print(f"Start: {df_all['Time'].iloc[0]} | End: {df_all['Time'].iloc[-1]}")


if __name__ == "__main__":
    main()
