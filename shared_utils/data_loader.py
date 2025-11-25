import yfinance as yf
import pandas as pd
from typing import Literal
from ib_insync import IB, Forex, Stock, Future, Contract
from datetime import datetime
import pandas as pd


def load_ohlcv_yfinance(symbol: str, period: str = "2y", interval: str = "1h") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval)
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.droplevel("Ticker")
        except ValueError:
            # Fallback if level name is different or index structure varies
            df.columns = df.columns.droplevel(1)
    df = df.dropna()
    return df


def load_ohlcv_ibkr(
    symbol: str,
    contract_kind: Literal["forex", "stock", "future"] = "forex",
    exchange: str | None = None,
    currency: str = "USD",
    duration: str = "1 Y",
    bar_size: str = "5 mins",
    what_to_show: str = "MIDPOINT",
    use_rth: bool = False,
    host: str = "127.0.0.1",
    port: int = 7496,
    client_id: int | None = None,
    contract_kwargs: dict | None = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV from IBKR using ib_insync. Assumes TWS or Gateway is running.
    contract_kind: forex|stock|future
    """
    if contract_kwargs is None:
        contract_kwargs = {}

    ib = IB()
    if client_id is not None:
        ib.connect(host, port, clientId=client_id, readonly=True, timeout=10)
    else:
        ib.connect(host, port, readonly=True, timeout=10)

    if contract_kind == "forex":
        contract = Forex(symbol, **contract_kwargs)
    elif contract_kind == "stock":
        contract = Stock(symbol, exchange or "SMART", currency, **contract_kwargs)
    elif contract_kind == "future":
        contract = Future(symbol, exchange or "NYMEX", currency=currency, **contract_kwargs)
    else:
        raise ValueError(f"Unsupported contract_kind: {contract_kind}")

    ib.qualifyContracts(contract)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=use_rth,
        formatDate=1,
        keepUpToDate=False,
    )
    df = pd.DataFrame(bars)
    if df.empty:
        return df

    df.rename(columns={"date": "Time", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
    df.set_index("Time", inplace=False)
    return df


def load_ohlcv_ibkr_chunked(
    symbol: str,
    contract_kind: Literal["forex", "stock", "future"] = "forex",
    exchange: str | None = None,
    currency: str = "USD",
    total_months: int = 60,
    chunk_months: int = 3,
    bar_size: str = "5 mins",
    what_to_show: str = "TRADES",
    use_rth: bool = False,
    host: str = "127.0.0.1",
    port: int = 7497,
    client_id: int = 1,
    contract_kwargs: dict | None = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV from IBKR in chunks (e.g., 3M slices) to avoid timeouts.
    total_months: how far back to fetch (60 = ~5 years)
    chunk_months: duration per request (e.g., 3)
    """
    if contract_kwargs is None:
        contract_kwargs = {}

    ib = IB()
    ib.connect(host, port, clientId=client_id, readonly=True, timeout=15)

    if contract_kind == "forex":
        contract = Forex(symbol, **contract_kwargs)
    elif contract_kind == "stock":
        contract = Stock(symbol, exchange or "SMART", currency, **contract_kwargs)
    elif contract_kind == "future":
        contract = Future(symbol, exchange or "NYMEX", currency=currency, **contract_kwargs)
    else:
        raise ValueError(f"Unsupported contract_kind: {contract_kind}")

    ib.qualifyContracts(contract)

    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.DateOffset(months=total_months)

    dfs = []
    cursor_end = end
    while cursor_end > start:
        duration_str = f"{chunk_months} M"
        end_dt = cursor_end.strftime("%Y%m%d %H:%M:%S")
        bars = ib.reqHistoricalData(
            contract,
            endDateTime=end_dt,
            durationStr=duration_str,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
            keepUpToDate=False,
        )
        df_chunk = pd.DataFrame(bars)
        if df_chunk.empty:
            break
        df_chunk.rename(columns={"date": "Time", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
        dfs.append(df_chunk)

        oldest = pd.to_datetime(df_chunk["Time"].min())
        cursor_end = oldest - pd.Timedelta(minutes=1)

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)
    df_all.drop_duplicates(subset=["Time"], inplace=True)
    df_all.sort_values("Time", inplace=True)
    return df_all
