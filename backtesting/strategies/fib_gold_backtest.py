import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

# from strategies.fib_fractal_live import generate_fib_trade_plan

GOLD_SYMBOL = "GC=F"  # Gold Futures on Yahoo Finance


def download_gold(interval: str, period: str = "30d") -> pd.DataFrame:
    """
    Download intraday gold data from Yahoo.
    interval: "5m", "15m", "30m"
    period:   max 60d for <60m intervals, keep it sane at 30d.
    """
    df = yf.download(GOLD_SYMBOL, period=period, interval=interval)
    
    # Fix for yfinance returning MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.droplevel("Ticker")
        except ValueError:
            # Fallback if level name is different or index structure varies
            df.columns = df.columns.droplevel(1)
            
    df = df.dropna()
    return df


def resample_data(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    Resample 1h data to higher timeframes (e.g. 4h).
    """
    if interval == "4h":
        # Ensure Time is index
        if "Time" in df.columns:
            df = df.set_index("Time")
            
        agg_dict = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }
        
        df_resampled = df.resample("4h").agg(agg_dict).dropna()
        return df_resampled
        
    return df


def print_full_report(results: Dict):
    """
    Print a detailed breakdown of backtest results.
    """
    if not results or "trades" not in results:
        print("No results to report.")
        return

    trades = results["trades"]
    df = results["df"]
    
    print(f"\n{'='*60}")
    print(f"FULL BREAKDOWN: {results['interval']} Timeframe")
    print(f"{'='*60}")
    
    print(f"Total Trades:      {results['trades_count']}")
    print(f"Win Rate:          {results['win_rate']:.2f}%")
    print(f"Total Return:      {results['total_return_pct']:.2f}%")
    
    if not trades:
        return

    # Calculate additional stats
    wins = [t for t in trades if t["result_pct"] > 0]
    losses = [t for t in trades if t["result_pct"] <= 0]
    
    avg_win = np.mean([t["result_pct"] for t in wins]) * 100 if wins else 0
    avg_loss = np.mean([t["result_pct"] for t in losses]) * 100 if losses else 0
    max_drawdown = 0 # TODO: Calculate properly if needed, but return is enough for now
    
    print(f"Winning Trades:    {len(wins)}")
    print(f"Losing Trades:     {len(losses)}")
    print(f"Avg Win:           {avg_win:.2f}%")
    print(f"Avg Loss:          {avg_loss:.2f}%")
    
    print(f"\n{'Type':<6} | {'Entry Time':<20} | {'Exit Time':<20} | {'Return':<8}")
    print("-" * 65)
    for t in trades[:10]: # Show first 10
        print(f"{t['type']:<6} | {t['entry_time']:<20} | {t['exit_time']:<20} | {t['result_pct']*100:>6.2f}%")
    if len(trades) > 10:
        print(f"... and {len(trades)-10} more trades.")
    print(f"{'='*60}\n")


def detect_swings(df: pd.DataFrame, lookback: int = 5) -> Tuple[List[int], List[int]]:
    """
    Detect swing highs and swing lows using a simple local-extrema approach.
    A swing high is the highest high within a window of size (2*lookback+1).
    A swing low is the lowest low within the same type of window.
    Returns:
        swing_high_indices, swing_low_indices
    """
    highs = []
    lows = []

    for i in range(lookback, len(df) - lookback):
        window = df.iloc[i - lookback : i + lookback + 1]

        if df["High"].iloc[i] == window["High"].max():
            highs.append(i)
        if df["Low"].iloc[i] == window["Low"].min():
            lows.append(i)

    return highs, lows


def detect_swings_zigzag(df: pd.DataFrame, deviation_pct: float = 0.01) -> Tuple[List[int], List[int]]:
    """
    Detect swings using a ZigZag-like algorithm based on percentage deviation.
    deviation_pct: 0.01 = 1%
    """
    highs = []
    lows = []
    
    if df.empty:
        return highs, lows
        
    # Initial state
    last_high_idx = 0
    last_high_val = df["High"].iloc[0]
    last_low_idx = 0
    last_low_val = df["Low"].iloc[0]
    
    # 1 = Up, -1 = Down. Assume Up initially if close > open, else Down?
    # Or just wait for first move. Let's assume Up.
    trend = 1 
    
    for i in range(1, len(df)):
        high = df["High"].iloc[i]
        low = df["Low"].iloc[i]
        
        if trend == 1: # Up Trend
            if high > last_high_val:
                # New high in current up leg
                last_high_val = high
                last_high_idx = i
            elif low < last_high_val * (1 - deviation_pct):
                # Reversal to Down
                highs.append(last_high_idx)
                trend = -1
                last_low_val = low
                last_low_idx = i
                
        else: # Down Trend
            if low < last_low_val:
                # New low in current down leg
                last_low_val = low
                last_low_idx = i
            elif high > last_low_val * (1 + deviation_pct):
                # Reversal to Up
                lows.append(last_low_idx)
                trend = 1
                last_high_val = high
                last_high_idx = i
                
    return highs, lows


def detect_swings_fractal(df: pd.DataFrame, window: int = 2) -> Tuple[List[int], List[int]]:
    """
    Detect swings using a simple fractal logic:
    - A swing high is higher than `window` bars on both sides.
    - A swing low is lower than `window` bars on both sides.
    """
    highs = []
    lows = []
    for i in range(window, len(df) - window):
        high_slice = df["High"].iloc[i - window : i + window + 1]
        low_slice = df["Low"].iloc[i - window : i + window + 1]
        if df["High"].iloc[i] == high_slice.max():
            highs.append(i)
        if df["Low"].iloc[i] == low_slice.min():
            lows.append(i)
    return highs, lows


def build_swing_sequence(df: pd.DataFrame, highs: List[int], lows: List[int]) -> List[Dict]:
    """
    Combine swing highs and lows into a single time-ordered sequence.
    Each element: {"idx": int, "type": "high" or "low", "price": float}
    """
    points = []

    for i in highs:
        points.append({"idx": i, "type": "high", "price": df["High"].iloc[i]})
    for i in lows:
        points.append({"idx": i, "type": "low", "price": df["Low"].iloc[i]})

    points.sort(key=lambda x: x["idx"])
    return points


def backtest_fib_strategy(
    interval: str,
    swing_method: str = "local_extrema", # "local_extrema", "zigzag", or "fractal"
    swing_param: float = 5, # lookback (int) for local_extrema/fractal, deviation (float) for zigzag
    trend_ma_period: int = 200,
    trend_ma_type: str = "SMA",
    trend_filter: bool = True,
    entry_retrace: float = 0.618,
    sl_retrace: float = 0.5,
    tp_retrace: float = 0.236,
    tp1_retrace: float | None = None,
    tp1_frac: float = 0.5,
    tp1_new_sl_retrace: float | None = None,
    move_stop_to_be: bool = True,
    data: pd.DataFrame | None = None,
    verbose: bool = True
) -> Dict:
    """
    Backtest Gold Fib Strategy with Trend Filter:
    - Trend defined by SMA or EMA (can be disabled).
    - Swings defined by Local Extrema, ZigZag, or Fractal.
    - Optional custom retrace levels for entry/SL/TP.
    - Optional partial TP with stop-to-BE or custom level.
    """
    # Use provided data if given, else download
    if data is not None:
        df = data.copy()
    else:
        download_interval = "1h" if interval == "4h" else interval
        period = "2y" if download_interval == "1h" else "60d"
        df = download_gold(interval=download_interval, period=period) 
        if df.empty:
            if verbose: print(f"[{interval}] No data downloaded for gold.")
            return {}

    df = df.copy()
    df.reset_index(inplace=True)
    if "Time" not in df.columns:
        if "Datetime" in df.columns:
             df.rename(columns={"Datetime": "Time"}, inplace=True)
        elif "Date" in df.columns:
             df.rename(columns={"Date": "Time"}, inplace=True)

    # Resample if needed
    if interval == "4h" and data is None:
        df = resample_data(df, "4h")
        df.reset_index(inplace=True) # Reset index to get Time column back

    # Calculate Trend (optional)
    if trend_filter:
        if trend_ma_type == "SMA":
            df["Trend"] = df["Close"].rolling(trend_ma_period).mean()
        elif trend_ma_type == "EMA":
            df["Trend"] = df["Close"].ewm(span=trend_ma_period, adjust=False).mean()
        else:
            df["Trend"] = df["Close"].rolling(trend_ma_period).mean() # Default to SMA
    else:
        df["Trend"] = np.nan
    
    if swing_method == "zigzag":
        highs, lows = detect_swings_zigzag(df, deviation_pct=swing_param)
    elif swing_method == "fractal":
        highs, lows = detect_swings_fractal(df, window=int(swing_param))
    else:
        highs, lows = detect_swings(df, lookback=int(swing_param))
        
    points = build_swing_sequence(df, highs, lows)

    trades = []
    equity = 1.0
    initial_equity = equity

    total_pairs = len(points) - 1
    for i in range(total_pairs):
        a = points[i]
        b = points[i + 1]
        if verbose and i > 0 and i % 500 == 0:
            print(f"[{interval}] processed {i}/{total_pairs} swing pairs")
        
        # Check Trend at the time of the second swing point (b) unless disabled
        if trend_filter:
            trend_val = df["Trend"].iloc[b["idx"]]
            if pd.isna(trend_val):
                continue
                
            current_close = df["Close"].iloc[b["idx"]]
            is_uptrend = current_close > trend_val
            is_downtrend = current_close < trend_val
        else:
            # Allow both directions when no trend filter
            is_uptrend = True
            is_downtrend = True
        
        # --- SHORT SETUP (Downtrend) ---
        if is_downtrend and a["type"] == "high" and b["type"] == "low" and b["price"] < a["price"]:
            hi = a["price"]
            lo = b["price"]
            diff = hi - lo
            
            entry_level = lo + entry_retrace * diff
            sl_level = lo + sl_retrace * diff
            tp_level = lo + tp_retrace * diff
            tp1_level = lo + tp1_retrace * diff if tp1_retrace is not None else None
            
            # Logic for Short Trade
            start_bar = b["idx"] + 1
            if start_bar >= len(df): continue
            
            # Find end of window (next swing or end of data)
            if i + 2 < len(points):
                end_bar = points[i + 2]["idx"]
            else:
                end_bar = len(df) - 1
                
            in_trade = False
            entry_price = None
            entry_time = None
            hit_tp1 = False
            
            for j in range(start_bar, end_bar + 1):
                row = df.iloc[j]
                if not in_trade:
                    # Limit fill if price goes UP to entry
                    if row["High"] >= entry_level:
                        in_trade = True
                        entry_price = entry_level
                        entry_time = row["Time"]
                else:
                    # Check TP1 (partial) if enabled
                    exit_price = None
                    if tp1_level is not None and not hit_tp1 and row["Low"] <= tp1_level:
                        # Realize partial profit
                        res_tp1 = (entry_price - tp1_level) / entry_price
                        equity *= (1.0 + tp1_frac * res_tp1)
                        hit_tp1 = True
                        
                        # Move SL
                        if tp1_new_sl_retrace is not None:
                            sl_level = lo + tp1_new_sl_retrace * diff
                        elif move_stop_to_be:
                            sl_level = entry_price
                        # Continue trade for remaining size
                    
                    hit_sl = row["High"] >= sl_level
                    hit_tp = row["Low"] <= tp_level
                    
                    if hit_sl and hit_tp:
                        exit_price = sl_level
                    elif hit_sl:
                        exit_price = sl_level
                    elif hit_tp:
                        exit_price = tp_level
                    
                    if exit_price:
                        size = 1.0 if not hit_tp1 else (1.0 - tp1_frac)
                        res = (entry_price - exit_price) / entry_price
                        equity *= (1.0 + size * res)
                        trades.append({
                            "type": "SHORT",
                            "entry_time": str(entry_time),
                            "exit_time": str(row["Time"]),
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "result_pct": res * size if hit_tp1 else res,
                            "interval": interval,
                            "swing_high_time": str(df.iloc[a["idx"]]["Time"]),
                            "swing_low_time": str(df.iloc[b["idx"]]["Time"]),
                        })
                        in_trade = False
                        break
            
            # Close at end of window if still open
            if in_trade:
                exit_price = df["Close"].iloc[end_bar]
                size = 1.0 if not hit_tp1 else (1.0 - tp1_frac)
                res = (entry_price - exit_price) / entry_price
                equity *= (1.0 + size * res)
                trades.append({
                    "type": "SHORT",
                    "entry_time": str(entry_time),
                    "exit_time": str(df["Time"].iloc[end_bar]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "result_pct": res,
                    "interval": interval,
                    "swing_high_time": str(df.iloc[a["idx"]]["Time"]),
                    "swing_low_time": str(df.iloc[b["idx"]]["Time"]),
                })

        # --- LONG SETUP (Uptrend) ---
        elif is_uptrend and a["type"] == "low" and b["type"] == "high" and b["price"] > a["price"]:
            lo = a["price"]
            hi = b["price"]
            diff = hi - lo
            
            # Retrace down from High
            entry_level = hi - entry_retrace * diff
            sl_level = hi - sl_retrace * diff
            tp_level = hi - tp_retrace * diff
            tp1_level = hi - tp1_retrace * diff if tp1_retrace is not None else None
            
            # Logic for Long Trade
            start_bar = b["idx"] + 1
            if start_bar >= len(df): continue
            
            if i + 2 < len(points):
                end_bar = points[i + 2]["idx"]
            else:
                end_bar = len(df) - 1
                
            in_trade = False
            entry_price = None
            entry_time = None
            hit_tp1 = False
            
            for j in range(start_bar, end_bar + 1):
                row = df.iloc[j]
                if not in_trade:
                    # Limit fill if price goes DOWN to entry
                    if row["Low"] <= entry_level:
                        in_trade = True
                        entry_price = entry_level
                        entry_time = row["Time"]
                else:
                    # TP1 partial
                    exit_price = None
                    if tp1_level is not None and not hit_tp1 and row["High"] >= tp1_level:
                        res_tp1 = (tp1_level - entry_price) / entry_price
                        equity *= (1.0 + tp1_frac * res_tp1)
                        hit_tp1 = True
                        
                        # Move SL
                        if tp1_new_sl_retrace is not None:
                            sl_level = hi - tp1_new_sl_retrace * diff
                        elif move_stop_to_be:
                            sl_level = entry_price
                        # continue
                    
                    hit_sl = row["Low"] <= sl_level
                    hit_tp = row["High"] >= tp_level
                    
                    if hit_sl and hit_tp:
                        exit_price = sl_level
                    elif hit_sl:
                        exit_price = sl_level
                    elif hit_tp:
                        exit_price = tp_level
                    
                    if exit_price:
                        size = 1.0 if not hit_tp1 else (1.0 - tp1_frac)
                        res = (exit_price - entry_price) / entry_price
                        equity *= (1.0 + size * res)
                        trades.append({
                            "type": "SHORT",
                            "entry_time": str(entry_time),
                            "exit_time": str(row["Time"]),
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "result_pct": res * size if hit_tp1 else res,
                            "interval": interval,
                            "swing_high_time": str(df.iloc[a["idx"]]["Time"]),
                            "swing_low_time": str(df.iloc[b["idx"]]["Time"]),
                        })
                        in_trade = False
                        break
            
            # Close at end of window if still open
            if in_trade:
                exit_price = df["Close"].iloc[end_bar]
                size = 1.0 if not hit_tp1 else (1.0 - tp1_frac)
                res = (entry_price - exit_price) / entry_price
                equity *= (1.0 + size * res)
                trades.append({
                    "type": "SHORT",
                    "entry_time": str(entry_time),
                    "exit_time": str(df["Time"].iloc[end_bar]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "result_pct": res,
                    "interval": interval,
                    "swing_high_time": str(df.iloc[a["idx"]]["Time"]),
                    "swing_low_time": str(df.iloc[b["idx"]]["Time"]),
                })

        # --- LONG SETUP (Uptrend) ---
        elif is_uptrend and a["type"] == "low" and b["type"] == "high" and b["price"] > a["price"]:
            lo = a["price"]
            hi = b["price"]
            diff = hi - lo
            
            # Retrace down from High
            entry_level = hi - entry_retrace * diff
            sl_level = hi - sl_retrace * diff
            tp_level = hi - tp_retrace * diff
            tp1_level = hi - tp1_retrace * diff if tp1_retrace is not None else None
            
            # Logic for Long Trade
            start_bar = b["idx"] + 1
            if start_bar >= len(df): continue
            
            if i + 2 < len(points):
                end_bar = points[i + 2]["idx"]
            else:
                end_bar = len(df) - 1
                
            in_trade = False
            entry_price = None
            entry_time = None
            hit_tp1 = False
            
            for j in range(start_bar, end_bar + 1):
                row = df.iloc[j]
                if not in_trade:
                    # Limit fill if price goes DOWN to entry
                    if row["Low"] <= entry_level:
                        in_trade = True
                        entry_price = entry_level
                        entry_time = row["Time"]
                else:
                    # TP1 partial
                    exit_price = None
                    if tp1_level is not None and not hit_tp1 and row["High"] >= tp1_level:
                        res_tp1 = (tp1_level - entry_price) / entry_price
                        equity *= (1.0 + tp1_frac * res_tp1)
                        hit_tp1 = True
                        if move_stop_to_be:
                            sl_level = entry_price
                        # continue
                    
                    hit_sl = row["Low"] <= sl_level
                    hit_tp = row["High"] >= tp_level
                    
                    if hit_sl and hit_tp:
                        exit_price = sl_level
                    elif hit_sl:
                        exit_price = sl_level
                    elif hit_tp:
                        exit_price = tp_level
                    
                    if exit_price:
                        size = 1.0 if not hit_tp1 else (1.0 - tp1_frac)
                        res = (exit_price - entry_price) / entry_price
                        equity *= (1.0 + size * res)
                        trades.append({
                            "type": "LONG",
                            "entry_time": str(entry_time),
                            "exit_time": str(row["Time"]),
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "result_pct": res * size if hit_tp1 else res,
                            "interval": interval,
                            "swing_low_time": str(df.iloc[a["idx"]]["Time"]),
                            "swing_high_time": str(df.iloc[b["idx"]]["Time"]),
                        })
                        in_trade = False
                        break
            
            if in_trade:
                exit_price = df["Close"].iloc[end_bar]
                size = 1.0 if not hit_tp1 else (1.0 - tp1_frac)
                res = (exit_price - entry_price) / entry_price
                equity *= (1.0 + size * res)
                trades.append({
                    "type": "LONG",
                    "entry_time": str(entry_time),
                    "exit_time": str(df["Time"].iloc[end_bar]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "result_pct": res * size if hit_tp1 else res,
                    "interval": interval,
                    "swing_low_time": str(df.iloc[a["idx"]]["Time"]),
                    "swing_high_time": str(df.iloc[b["idx"]]["Time"]),
                })

    # Stats
    if not trades:
        if verbose: print(f"[{interval}] No trades generated.")
        return {"interval": interval, "trades_count": 0, "win_rate": 0.0, "total_return_pct": 0.0, "trades": [], "df": df}

    wins = sum(1 for t in trades if t["result_pct"] > 0)
    win_rate = wins / len(trades) * 100.0
    total_return = (equity - initial_equity) * 100.0
    
    if verbose:
        print(f"\n=== {interval} BACKTEST (TREND FILTERED) ===")
        print(f"Trades: {len(trades)} | Win Rate: {win_rate:.2f}% | Return: {total_return:.2f}%")
        print("Sample Trades:")
        for t in trades[:5]:
            print(f"  {t['type']} {t['entry_time']} -> {t['exit_time']} | Ret: {t['result_pct']*100:.2f}%")
        
    return {
        "interval": interval, 
        "trades_count": len(trades), 
        "win_rate": win_rate, 
        "total_return_pct": total_return,
        "trades": trades,
        "df": df
    }

def optimize_swing_logic():
    print("\n=== OPTIMIZING SWING LOGIC (1h, 2 Years) ===")
    # Use best trend filter from previous step: EMA 50
    trend_type = "EMA"
    trend_period = 50
    interval = "1h"
    
    configs = [
        {"method": "local_extrema", "param": 5},
        {"method": "local_extrema", "param": 10},
        {"method": "local_extrema", "param": 20},
        {"method": "zigzag", "param": 0.005}, # 0.5%
        {"method": "zigzag", "param": 0.01},  # 1.0%
        {"method": "zigzag", "param": 0.02},  # 2.0%
        {"method": "zigzag", "param": 0.03},  # 3.0%
    ]
    
    results = []
    
    for cfg in configs:
        method = cfg["method"]
        param = cfg["param"]
        print(f"Testing {method} with param={param}...")
        
        res = backtest_fib_strategy(
            interval=interval, 
            swing_method=method, 
            swing_param=param,
            trend_ma_type=trend_type, 
            trend_ma_period=trend_period, 
            verbose=False
        )
        
        if res:
            results.append({
                "method": method,
                "param": param,
                "win_rate": res["win_rate"],
                "return": res["total_return_pct"],
                "trades": res["trades_count"]
            })
    
    # Sort by Win Rate
    results.sort(key=lambda x: x["win_rate"], reverse=True)
    
    print("\n=== SWING OPTIMIZATION RESULTS (Sorted by Win Rate) ===")
    print(f"{'Method':<15} | {'Param':<6} | {'Trades':<6} | {'Win Rate':<8} | {'Return':<8}")
    print("-" * 60)
    for r in results:
        print(f"{r['method']:<15} | {r['param']:<6} | {r['trades']:<6} | {r['win_rate']:>6.2f}% | {r['return']:>6.2f}%")


def backtest_breakout_strategy(
    interval: str = "1h",
    swing_method: str = "zigzag",
    swing_param: float | int = 0.01,
    trend_filter: bool = True,
    trend_ma_type: str = "EMA",
    trend_ma_period: int = 50,
    tp_r_multiple: float = 2.0, # Target 2R
    move_stop_to_be: bool = True,
    fee_pct: float = 0.001, # 0.1% per trade (0.2% round trip)
    data: pd.DataFrame | None = None,
    verbose: bool = True
) -> Dict:
    """
    Backtest Breakout Strategy:
    - Long: Break above Swing High. SL at Swing Low.
    - Short: Break below Swing Low. SL at Swing High.
    - Trend Filter: Optional.
    """
    # Use provided data if given, else download
    if data is not None:
        df = data.copy()
    else:
        download_interval = "1h" if interval == "4h" else interval
        period = "2y" if download_interval == "1h" else "60d"
        df = download_gold(interval=download_interval, period=period) 
        if df.empty:
            if verbose: print(f"[{interval}] No data downloaded.")
            return {}

    df = df.copy()
    df.reset_index(inplace=True)
    if "Time" not in df.columns:
        if "Datetime" in df.columns:
             df.rename(columns={"Datetime": "Time"}, inplace=True)
        elif "Date" in df.columns:
             df.rename(columns={"Date": "Time"}, inplace=True)

    # Resample if needed
    if interval == "4h" and data is None:
        df = resample_data(df, "4h")
        df.reset_index(inplace=True)

    # Calculate Trend (optional)
    if trend_filter:
        if trend_ma_type == "SMA":
            df["Trend"] = df["Close"].rolling(trend_ma_period).mean()
        elif trend_ma_type == "EMA":
            df["Trend"] = df["Close"].ewm(span=trend_ma_period, adjust=False).mean()
        else:
            df["Trend"] = df["Close"].rolling(trend_ma_period).mean()
    else:
        df["Trend"] = np.nan
    
    if swing_method == "zigzag":
        highs, lows = detect_swings_zigzag(df, deviation_pct=swing_param)
    elif swing_method == "fractal":
        highs, lows = detect_swings_fractal(df, window=int(swing_param))
    else:
        highs, lows = detect_swings(df, lookback=int(swing_param))
        
    points = build_swing_sequence(df, highs, lows)

    trades = []
    equity = 1.0
    initial_equity = equity

    total_pairs = len(points) - 1
    for i in range(total_pairs):
        a = points[i]
        b = points[i + 1]
        
        # Check Trend at the time of the second swing point (b)
        if trend_filter:
            trend_val = df["Trend"].iloc[b["idx"]]
            if pd.isna(trend_val): continue
            current_close = df["Close"].iloc[b["idx"]]
            is_uptrend = current_close > trend_val
            is_downtrend = current_close < trend_val
        else:
            is_uptrend = True
            is_downtrend = True
        
        # --- BREAKOUT LONG (Break of Swing High) ---
        # We need a High (A) followed by a Low (B). Breakout is above A.
        if is_uptrend and a["type"] == "high" and b["type"] == "low":
            breakout_level = a["price"]
            sl_level = b["price"]
            risk = breakout_level - sl_level
            if risk <= 0: continue
            
            tp_level = breakout_level + (risk * tp_r_multiple)
            
            start_bar = b["idx"] + 1
            if start_bar >= len(df): continue
            
            # Find end of window (next swing pair or end of data)
            # Actually for breakout, we might hold longer. Let's just look forward until hit or next swing structure invalidates?
            # For simplicity, let's look forward until next swing pair starts (i+2)
            if i + 2 < len(points):
                end_bar = points[i + 2]["idx"]
            else:
                end_bar = len(df) - 1
                
            in_trade = False
            entry_price = None
            entry_time = None
            
            for j in range(start_bar, end_bar + 1):
                row = df.iloc[j]
                if not in_trade:
                    if row["High"] > breakout_level:
                        in_trade = True
                        entry_price = breakout_level # Assume stop entry fill
                        entry_time = row["Time"]
                else:
                    hit_sl = row["Low"] <= sl_level
                    hit_tp = row["High"] >= tp_level
                    
                    exit_price = None
                    if hit_sl and hit_tp:
                        exit_price = sl_level # Worst case
                    elif hit_sl:
                        exit_price = sl_level
                    elif hit_tp:
                        exit_price = tp_level
                    
                    if exit_price:
                        res = (exit_price - entry_price) / entry_price
                        res -= (fee_pct * 2) # Entry + Exit Fee
                        equity *= (1.0 + res)
                        trades.append({
                            "type": "LONG_BREAKOUT",
                            "entry_time": str(entry_time),
                            "exit_time": str(row["Time"]),
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "result_pct": res,
                            "interval": interval
                        })
                        in_trade = False
                        break
            
            if in_trade:
                exit_price = df["Close"].iloc[end_bar]
                res = (exit_price - entry_price) / entry_price
                res -= (fee_pct * 2) # Entry + Exit Fee
                equity *= (1.0 + res)
                trades.append({
                    "type": "LONG_BREAKOUT",
                    "entry_time": str(entry_time),
                    "exit_time": str(df["Time"].iloc[end_bar]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "result_pct": res,
                    "interval": interval
                })

        # --- BREAKOUT SHORT (Break of Swing Low) ---
        # We need a Low (A) followed by a High (B). Breakout is below A.
        elif is_downtrend and a["type"] == "low" and b["type"] == "high":
            breakout_level = a["price"]
            sl_level = b["price"]
            risk = sl_level - breakout_level
            if risk <= 0: continue
            
            tp_level = breakout_level - (risk * tp_r_multiple)
            
            start_bar = b["idx"] + 1
            if start_bar >= len(df): continue
            
            if i + 2 < len(points):
                end_bar = points[i + 2]["idx"]
            else:
                end_bar = len(df) - 1
                
            in_trade = False
            entry_price = None
            entry_time = None
            
            for j in range(start_bar, end_bar + 1):
                row = df.iloc[j]
                if not in_trade:
                    if row["Low"] < breakout_level:
                        in_trade = True
                        entry_price = breakout_level
                        entry_time = row["Time"]
                else:
                    hit_sl = row["High"] >= sl_level
                    hit_tp = row["Low"] <= tp_level
                    
                    exit_price = None
                    if hit_sl and hit_tp:
                        exit_price = sl_level
                    elif hit_sl:
                        exit_price = sl_level
                    elif hit_tp:
                        exit_price = tp_level
                    
                    if exit_price:
                        res = (entry_price - exit_price) / entry_price
                        res -= (fee_pct * 2) # Entry + Exit Fee
                        equity *= (1.0 + res)
                        trades.append({
                            "type": "SHORT_BREAKOUT",
                            "entry_time": str(entry_time),
                            "exit_time": str(row["Time"]),
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "result_pct": res,
                            "interval": interval
                        })
                        in_trade = False
                        break
            
            if in_trade:
                exit_price = df["Close"].iloc[end_bar]
                res = (entry_price - exit_price) / entry_price
                res -= (fee_pct * 2) # Entry + Exit Fee
                equity *= (1.0 + res)
                trades.append({
                    "type": "SHORT_BREAKOUT",
                    "entry_time": str(entry_time),
                    "exit_time": str(df["Time"].iloc[end_bar]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "result_pct": res,
                    "interval": interval
                })

    # Stats
    if not trades:
        if verbose: print(f"[{interval}] No trades generated.")
        return {"interval": interval, "trades_count": 0, "win_rate": 0.0, "total_return_pct": 0.0, "max_drawdown_pct": 0.0, "trades": [], "df": df}

    wins = sum(1 for t in trades if t["result_pct"] > 0)
    win_rate = wins / len(trades) * 100.0
    total_return = (equity - initial_equity) * 100.0
    
    # Calculate Max Drawdown
    peak = 1.0
    max_dd = 0.0
    curr_equity = 1.0
    for t in trades:
        curr_equity *= (1.0 + t["result_pct"])
        if curr_equity > peak:
            peak = curr_equity
        dd = (peak - curr_equity) / peak
        if dd > max_dd:
            max_dd = dd
            
    max_drawdown_pct = max_dd * 100.0
    
    if verbose:
        print(f"\n=== {interval} BREAKOUT BACKTEST ===")
        print(f"Trades: {len(trades)} | Win Rate: {win_rate:.2f}% | Return: {total_return:.2f}% | Max DD: {max_drawdown_pct:.2f}%")
        
    return {
        "interval": interval, 
        "trades_count": len(trades), 
        "win_rate": win_rate, 
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown_pct,
        "trades": trades,
        "df": df
    }

if __name__ == "__main__":
    # run_all_timeframes()
    # optimize_trend_filter()
    optimize_swing_logic()
