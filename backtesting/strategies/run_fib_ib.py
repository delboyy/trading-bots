import os
import sys
from pathlib import Path
from ib_insync import IB

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from utils.data_loader import load_ohlcv_ibkr, load_ohlcv_ibkr_chunked
from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report


def main():
    # Defaults: XAUUSD forex 5m bars, 1 year (easier than futures without specifying month)
    symbol = os.getenv("IB_SYMBOL", "XAUUSD")
    contract_kind = os.getenv("IB_KIND", "forex")
    exchange = os.getenv("IB_EXCHANGE", None)
    duration = os.getenv("IB_DURATION", "1 Y")
    bar_size = os.getenv("IB_BAR_SIZE", "5 mins")
    what_to_show = os.getenv("IB_WHAT", "TRADES")
    use_rth = os.getenv("IB_USE_RTH", "False").lower() == "true"
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    client_id = int(os.getenv("IB_CLIENT_ID", "1"))

    contract_kwargs = {}
    contract_month = os.getenv("IB_CONTRACT_MONTH")
    if contract_month:
        contract_kwargs["lastTradeDateOrContractMonth"] = contract_month

    chunk_total = os.getenv("IB_TOTAL_MONTHS")
    chunk_size = os.getenv("IB_CHUNK_MONTHS")

    if chunk_total and chunk_size:
        data = load_ohlcv_ibkr_chunked(
            symbol=symbol,
            contract_kind=contract_kind,
            exchange=exchange,
            total_months=int(chunk_total),
            chunk_months=int(chunk_size),
            bar_size=bar_size,
            what_to_show=what_to_show,
            use_rth=use_rth,
            host=host,
            port=port,
            client_id=client_id,
            contract_kwargs=contract_kwargs,
        )
    else:
        data = load_ohlcv_ibkr(
            symbol=symbol,
            contract_kind=contract_kind,
            exchange=exchange,
            duration=duration,
            bar_size=bar_size,
            what_to_show=what_to_show,
            use_rth=use_rth,
            host=host,
            port=port,
            client_id=client_id,
            contract_kwargs=contract_kwargs,
        )

    if data.empty:
        print("No data returned from IBKR.")
        return

    # Use best-performing intraday config found in sweeps (partial TP)
    res = backtest_fib_strategy(
        interval=bar_size.replace(" ", ""),
        data=data,
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
