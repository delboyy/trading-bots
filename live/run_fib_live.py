import json
import os
import time
from pathlib import Path
from typing import Dict, Optional
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from live.bybit_demo_client import BybitDemoClient
from strategies.fib_fractal_live import generate_fib_trade_plan


INTERVAL_MAP = {
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
}

DEFAULT_SLEEP = {
    "5m": 30,
    "15m": 60,
    "30m": 90,
    "1h": 120,
}

TP1_FRAC = 0.5


def load_state(path: Path) -> Dict:
    if path.exists():
        raw = json.loads(path.read_text())
        pending = raw.get("pending_plan")
        if pending and isinstance(pending.get("valid_after"), str):
            pending["valid_after"] = pd.to_datetime(pending["valid_after"])
        position = raw.get("position")
        if position and isinstance(position.get("entry_time"), str):
            position["entry_time"] = pd.to_datetime(position["entry_time"])
        return raw
    return {
        "status": "idle",
        "pending_plan": None,
        "position": None,
    }


def save_state(path: Path, state: Dict):
    serializable = json.loads(json.dumps(state, default=str))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serializable, indent=2))


def candle_triggers_entry(plan: Dict, candle: pd.Series) -> bool:
    valid_after = plan.get("valid_after")
    if valid_after is not None and candle["Time"] <= valid_after:
        return False
    if plan["side"] == "long":
        return candle["Low"] <= plan["entry"]
    return candle["High"] >= plan["entry"]


def enter_trade(
    client: BybitDemoClient,
    symbol: str,
    plan: Dict,
    qty: float,
    candle: pd.Series,
) -> Dict:
    order_side = "Buy" if plan["side"] == "long" else "Sell"
    order = client.place_market_order(symbol, order_side, qty)
    fill_price = order.get("price")
    fill_price = float(fill_price) if fill_price else candle["Close"]
    return {
        "status": plan["side"],
        "entry_price": fill_price,
        "qty": qty,
        "qty_remaining": qty,
        "tp1": plan["tp1"],
        "tp2": plan["tp2"],
        "sl": plan["sl"],
        "entry_time": candle["Time"],
        "tp1_hit": False,
    }


def close_position(client: BybitDemoClient, symbol: str, side: str, qty: float):
    if qty <= 0:
        return
    exit_side = "Sell" if side == "long" else "Buy"
    client.place_market_order(symbol, exit_side, qty)


def manage_position(
    client: BybitDemoClient,
    symbol: str,
    state: Dict,
    candle: pd.Series,
):
    position = state.get("position")
    if not position:
        return state

    entry_time = position.get("entry_time")
    if entry_time is not None and candle["Time"] <= entry_time:
        return state

    side = position["status"]
    high = candle["High"]
    low = candle["Low"]

    if side == "long":
        if not position["tp1_hit"] and high >= position["tp1"]:
            close_qty = position["qty"] * TP1_FRAC
            close_position(client, symbol, side, close_qty)
            position["qty_remaining"] -= close_qty
            position["tp1_hit"] = True
            position["sl"] = max(position["sl"], position["entry_price"])
        if low <= position["sl"]:
            close_position(client, symbol, side, position["qty_remaining"])
            state["position"] = None
            state["status"] = "idle"
            return state
        if high >= position["tp2"]:
            close_position(client, symbol, side, position["qty_remaining"])
            state["position"] = None
            state["status"] = "idle"
            return state
    else:
        if not position["tp1_hit"] and low <= position["tp1"]:
            close_qty = position["qty"] * TP1_FRAC
            close_position(client, symbol, side, close_qty)
            position["qty_remaining"] -= close_qty
            position["tp1_hit"] = True
            position["sl"] = min(position["sl"], position["entry_price"])
        if high >= position["sl"]:
            close_position(client, symbol, side, position["qty_remaining"])
            state["position"] = None
            state["status"] = "idle"
            return state
        if low <= position["tp2"]:
            close_position(client, symbol, side, position["qty_remaining"])
            state["position"] = None
            state["status"] = "idle"
            return state

    if position["qty_remaining"] <= 0:
        state["position"] = None
        state["status"] = "idle"
    return state


def main():
    timeframe = os.getenv("TIMEFRAME", "5m")
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    qty = float(os.getenv("TRADE_QTY", "0.001"))
    limit = int(os.getenv("DATA_LIMIT", "500"))
    loop_sleep = int(os.getenv("LOOP_SLEEP", str(DEFAULT_SLEEP.get(timeframe, 60))))
    run_once = os.getenv("RUN_ONCE", "false").lower() == "true"

    if timeframe not in INTERVAL_MAP:
        raise RuntimeError(f"Unsupported timeframe {timeframe}")

    interval_code = INTERVAL_MAP[timeframe]
    state_path = Path("state") / f"fib_{symbol}_{timeframe}.json"
    client = BybitDemoClient()
    state = load_state(state_path)

    while True:
        try:
            df = client.fetch_candles(symbol, interval_code, limit=limit)
            if df.empty:
                time.sleep(loop_sleep)
                continue

            # Use the last fully closed candle for signal generation; use the most recent (live) for triggers.
            if len(df) < 2:
                time.sleep(loop_sleep)
                continue
            last_live = df.iloc[-1]
            last_closed = df.iloc[-2]

            state = manage_position(client, symbol, state, last_live)

            plan = generate_fib_trade_plan(df.iloc[:-1])
            if plan:
                plan_id = f"{plan['impulse_start_idx']}-{plan['impulse_end_idx']}"
                pending = state.get("pending_plan")
                if not pending or pending.get("plan_id") != plan_id:
                    plan["plan_id"] = plan_id
                    plan["valid_after"] = last_closed["Time"]
                    state["pending_plan"] = plan
            else:
                state["pending_plan"] = None

            if state.get("status") == "idle" and state.get("pending_plan"):
                pending = state["pending_plan"]
                if candle_triggers_entry(pending, last_live):
                    position = enter_trade(client, symbol, pending, qty, last_live)
                    state["position"] = position
                    state["status"] = pending["side"]
                    state["pending_plan"] = None

            save_state(state_path, state)
        except Exception as exc:
            print(f"[{timeframe}] Error: {exc}")
        finally:
            if run_once:
                break
            time.sleep(loop_sleep)


if __name__ == "__main__":
    main()
