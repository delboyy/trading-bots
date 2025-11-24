"""
Chunked IBKR downloader for 5m bars with strict pacing and logging.
Defaults: GLD (STK, SMART, USD), 5 years of 5m bars (60 monthly chunks).
Saves raw monthly parquet files to data/raw/<SYMBOL>_<INTERVAL>/.
Saves merged parquet to data/processed/<SYMBOL>_<INTERVAL>.parquet.
"""

import os
import time
from pathlib import Path
from typing import Literal, Tuple, List

import pandas as pd
from ib_insync import IB, Stock, Forex, Future


def build_contract(
    ib: IB,
    symbol: str,
    sec_type: Literal["STK", "FUT", "CASH", "CFD"],
    exchange: str,
    currency: str,
    expiry: str | None = None,
):
    if sec_type == "STK":
        contract = Stock(symbol, exchange, currency)
    elif sec_type == "CASH":
        contract = Forex(symbol)
    elif sec_type == "FUT":
        if not expiry:
            raise ValueError("Expiry required for futures.")
        contract = Future(symbol, lastTradeDateOrContractMonth=expiry, exchange=exchange, currency=currency)
    elif sec_type == "CFD":
        # ib_insync CFD constructor matches Stock signature
        contract = Stock(symbol, exchange, currency, secType="CFD")
    else:
        raise ValueError(f"Unsupported secType {sec_type}")

    qualified = ib.qualifyContracts(contract)
    if not qualified:
        raise RuntimeError(f"Could not qualify contract: {contract}")
    return qualified[0]


def request_chunk(
    ib: IB,
    contract,
    end_dt: pd.Timestamp,
    duration_str: str,
    bar_size: str,
    what_to_show: str,
    use_rth: bool,
) -> pd.DataFrame:
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=end_dt.strftime("%Y%m%d %H:%M:%S"),
        durationStr=duration_str,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=use_rth,
        formatDate=1,
        keepUpToDate=False,
    )
    df = pd.DataFrame(bars)
    if df.empty:
        return df
    df.rename(
        columns={
            "date": "Time",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        },
        inplace=True,
    )
    return df


def download_monthly_chunks(
    symbol: str,
    sec_type: str,
    exchange: str,
    currency: str,
    total_months: int,
    chunk_months: int,
    bar_size: str,
    what_to_show: str,
    use_rth: bool,
    host: str,
    port: int,
    client_id: int,
    expiry: str | None,
    raw_dir: Path,
) -> List[Path]:
    ib = IB()
    ib.connect(host, port, clientId=client_id, readonly=True, timeout=10)
    contract = build_contract(ib, symbol, sec_type, exchange, currency, expiry)

    raw_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []

    end_cursor = pd.Timestamp.now(tz="UTC")
    start_limit = end_cursor - pd.DateOffset(months=total_months)

    for idx in range(total_months // chunk_months * chunk_months):
        duration_str = f"{chunk_months} M"
        retries = 0
        while retries < 3:
            try:
                df_chunk = request_chunk(
                    ib,
                    contract,
                    end_cursor,
                    duration_str=duration_str,
                    bar_size=bar_size,
                    what_to_show=what_to_show,
                    use_rth=use_rth,
                )
                break
            except Exception:
                retries += 1
                time.sleep(1)
        else:
            print(f"[{idx+1}] Failed after retries, ending early.")
            break

        if df_chunk.empty:
            print(f"[{idx+1}] Empty chunk, stopping.")
            break

        df_chunk["Time"] = pd.to_datetime(df_chunk["Time"], utc=True)
        chunk_start = df_chunk["Time"].min()
        chunk_end = df_chunk["Time"].max()

        # Save raw chunk
        fname = f"{symbol}_{bar_size.replace(' ', '')}_{chunk_end.strftime('%Y%m%d')}.parquet"
        fpath = raw_dir / fname
        df_chunk.to_parquet(fpath, index=False)
        paths.append(fpath)

        print(f"[{idx+1:02d}] {chunk_start} -> {chunk_end} rows={len(df_chunk)} saved={fpath.name}")

        end_cursor = chunk_start - pd.Timedelta(minutes=5)
        if end_cursor <= start_limit:
            break

        time.sleep(1)  # pacing per requirements

    ib.disconnect()
    return paths


def merge_and_clean(paths: List[Path], bar_minutes: int, output_path: Path):
    dfs = []
    for p in paths:
        df = pd.read_parquet(p)
        dfs.append(df)
    if not dfs:
        raise RuntimeError("No chunks to merge.")

    df_all = pd.concat(dfs, ignore_index=True)
    df_all.drop_duplicates(subset=["Time"], inplace=True)
    df_all["Time"] = pd.to_datetime(df_all["Time"], utc=True)
    df_all.sort_values("Time", inplace=True)

    # Enforce expected columns
    cols = ["Time", "Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in cols if c not in df_all.columns]
    if missing:
        raise RuntimeError(f"Missing columns in merged data: {missing}")
    df_all = df_all[cols]

    # Optional uniform spacing check: drop bars not aligned to bar_minutes grid
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    aligned = df_all[(df_all["Time"] - epoch).dt.total_seconds() % (bar_minutes * 60) == 0]
    df_all = aligned

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_parquet(output_path, index=False)

    print(f"Merged {len(paths)} chunks -> {len(df_all)} rows saved to {output_path}")
    print(f"Start: {df_all['Time'].iloc[0]} | End: {df_all['Time'].iloc[-1]}")


def main():
    symbol = os.getenv("IB_SYMBOL", "GLD")
    sec_type = os.getenv("IB_SECTYPE", "STK")
    exchange = os.getenv("IB_EXCHANGE", "SMART")
    currency = os.getenv("IB_CURRENCY", "USD")
    expiry = os.getenv("IB_EXPIRY")  # for futures

    total_months = int(os.getenv("IB_TOTAL_MONTHS", "60"))
    chunk_months = int(os.getenv("IB_CHUNK_MONTHS", "1"))
    bar_size = os.getenv("IB_BAR_SIZE", "5 mins")
    what_to_show = os.getenv("IB_WHAT", "TRADES")
    use_rth = os.getenv("IB_USE_RTH", "False").lower() == "true"
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    client_id = int(os.getenv("IB_CLIENT_ID", "101"))

    raw_dir = Path("data/raw") / f"{symbol}_{bar_size.replace(' ', '')}"
    output_path = Path("data/processed") / f"{symbol}_{bar_size.replace(' ', '')}.parquet"

    paths = download_monthly_chunks(
        symbol=symbol,
        sec_type=sec_type,
        exchange=exchange,
        currency=currency,
        total_months=total_months,
        chunk_months=chunk_months,
        bar_size=bar_size,
        what_to_show=what_to_show,
        use_rth=use_rth,
        host=host,
        port=port,
        client_id=client_id,
        expiry=expiry,
        raw_dir=raw_dir,
    )

    if not paths:
        print("No chunks downloaded.")
        return

    merge_and_clean(paths, bar_minutes=5, output_path=output_path)


if __name__ == "__main__":
    main()
