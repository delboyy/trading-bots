import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Tuple

# --- Indicators ---
def calculate_ema(series, span=50):
    return series.ewm(span=span, adjust=False).mean()

# --- Swing Detection Methods ---
def detect_swings_zigzag(df, deviation_pct=0.02):
    highs = []
    lows = []
    series = df['Close'].values
    h_series = df['High'].values
    l_series = df['Low'].values
    
    tmp_high = h_series[0]
    tmp_low = l_series[0]
    tmp_high_idx = 0
    tmp_low_idx = 0
    trend = 0 # 1 up, -1 down
    
    for i in range(1, len(df)):
        curr_high = h_series[i]
        curr_low = l_series[i]
        
        if trend == 0:
            if curr_high > tmp_high:
                tmp_high = curr_high
                tmp_high_idx = i
            if curr_low < tmp_low:
                tmp_low = curr_low
                tmp_low_idx = i
            if curr_high >= tmp_low * (1 + deviation_pct):
                lows.append(tmp_low_idx)
                trend = 1
                tmp_high = curr_high
                tmp_high_idx = i
            elif curr_low <= tmp_high * (1 - deviation_pct):
                highs.append(tmp_high_idx)
                trend = -1
                tmp_low = curr_low
                tmp_low_idx = i
        elif trend == 1:
            if curr_high > tmp_high:
                tmp_high = curr_high
                tmp_high_idx = i
            elif curr_low <= tmp_high * (1 - deviation_pct):
                highs.append(tmp_high_idx)
                trend = -1
                tmp_low = curr_low
                tmp_low_idx = i
        elif trend == -1:
            if curr_low < tmp_low:
                tmp_low = curr_low
                tmp_low_idx = i
            elif curr_high >= tmp_low * (1 + deviation_pct):
                lows.append(tmp_low_idx)
                trend = 1
                tmp_high = curr_high
                tmp_high_idx = i
    return highs, lows

def detect_swings_local_extrema(df, window=5):
    highs = []
    lows = []
    for i in range(window, len(df) - window):
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            highs.append(i)
        if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            lows.append(i)
    return highs, lows

def detect_swings_fractal(df):
    highs = []
    lows = []
    # Bill Williams Fractal: High > 2 prev and 2 next
    for i in range(2, len(df) - 2):
        is_high = (df['High'].iloc[i] > df['High'].iloc[i-1]) and \
                  (df['High'].iloc[i] > df['High'].iloc[i-2]) and \
                  (df['High'].iloc[i] > df['High'].iloc[i+1]) and \
                  (df['High'].iloc[i] > df['High'].iloc[i+2])
        if is_high: highs.append(i)
        
        is_low = (df['Low'].iloc[i] < df['Low'].iloc[i-1]) and \
                 (df['Low'].iloc[i] < df['Low'].iloc[i-2]) and \
                 (df['Low'].iloc[i] < df['Low'].iloc[i+1]) and \
                 (df['Low'].iloc[i] < df['Low'].iloc[i+2])
        if is_low: lows.append(i)
    return highs, lows

# --- Backtest Engine ---
def backtest_strategy(df, swing_method="zigzag", swing_param=0.02, fee_pct=0.001):
    if df.empty: return {}
    df = df.copy()
    df['EMA'] = calculate_ema(df['Close'], 50)
    
    if swing_method == "zigzag":
        highs, lows = detect_swings_zigzag(df, deviation_pct=swing_param)
    elif swing_method == "local_extrema":
        highs, lows = detect_swings_local_extrema(df, window=int(swing_param))
    elif swing_method == "fractal":
        highs, lows = detect_swings_fractal(df)
    else:
        return {}
        
    # Combine swings for easy traversal
    swings = []
    for h in highs: swings.append({'idx': h, 'type': 'high', 'price': df['High'].iloc[h]})
    for l in lows: swings.append({'idx': l, 'type': 'low', 'price': df['Low'].iloc[l]})
    swings.sort(key=lambda x: x['idx'])
    
    trades = []
    equity = 1000.0
    
    # Logic:
    # Uptrend (Close > EMA): Buy break of Swing High. SL = Swing Low.
    # Downtrend (Close < EMA): Sell break of Swing Low. SL = Swing High.
    # TP = 2R
    
    for i in range(len(swings) - 1):
        last_swing = swings[i]
        
        # We need to look forward from the swing to see if price breaks it
        start_idx = last_swing['idx'] + 1
        # Look until next swing or end of data
        end_idx = swings[i+1]['idx'] if i+1 < len(swings) else len(df)
        
        # Determine Trend at the moment of the swing (or slightly after)
        # Strictly speaking, we should check trend at entry trigger, but checking at swing formation is a common proxy
        # Let's check trend at start_idx
        if start_idx >= len(df): continue
        trend_ema = df['EMA'].iloc[start_idx]
        trend_price = df['Close'].iloc[start_idx]
        
        in_trade = False
        
        # LONG SETUP
        if last_swing['type'] == 'high' and trend_price > trend_ema:
            entry_price = last_swing['price']
            # Find previous low for SL
            # Iterate backwards from current swing to find last low
            sl_price = None
            for j in range(i-1, -1, -1):
                if swings[j]['type'] == 'low':
                    sl_price = swings[j]['price']
                    break
            if sl_price is None: continue
            
            risk = entry_price - sl_price
            if risk <= 0: continue
            tp_price = entry_price + (risk * 2.0)
            
            # Check for trigger
            for k in range(start_idx, end_idx):
                row = df.iloc[k]
                if not in_trade:
                    if row['High'] > entry_price:
                        in_trade = True
                        # Assume entry at entry_price (stop order)
                else:
                    # Check SL/TP
                    if row['Low'] < sl_price: # SL Hit
                        res = (sl_price - entry_price) / entry_price
                        res -= (fee_pct * 2)
                        equity *= (1.0 + res)
                        trades.append(res)
                        break
                    elif row['High'] > tp_price: # TP Hit
                        res = (tp_price - entry_price) / entry_price
                        res -= (fee_pct * 2)
                        equity *= (1.0 + res)
                        trades.append(res)
                        break
                        
        # SHORT SETUP
        elif last_swing['type'] == 'low' and trend_price < trend_ema:
            entry_price = last_swing['price']
            # Find previous high for SL
            sl_price = None
            for j in range(i-1, -1, -1):
                if swings[j]['type'] == 'high':
                    sl_price = swings[j]['price']
                    break
            if sl_price is None: continue
            
            risk = sl_price - entry_price
            if risk <= 0: continue
            tp_price = entry_price - (risk * 2.0)
            
            for k in range(start_idx, end_idx):
                row = df.iloc[k]
                if not in_trade:
                    if row['Low'] < entry_price:
                        in_trade = True
                else:
                    if row['High'] > sl_price: # SL Hit
                        res = (entry_price - sl_price) / entry_price
                        res -= (fee_pct * 2)
                        equity *= (1.0 + res)
                        trades.append(res)
                        break
                    elif row['Low'] < tp_price: # TP Hit
                        res = (entry_price - tp_price) / entry_price
                        res -= (fee_pct * 2)
                        equity *= (1.0 + res)
                        trades.append(res)
                        break

    return calculate_stats(trades, equity)

def calculate_stats(trades, final_equity):
    if not trades:
        return {"return": 0.0, "trades": 0, "win_rate": 0.0}
    
    wins = len([t for t in trades if t > 0])
    win_rate = (wins / len(trades)) * 100
    total_return = (final_equity - 1000.0) / 1000.0 * 100
    
    return {
        "return": total_return,
        "trades": len(trades),
        "win_rate": win_rate
    }

def run_verification():
    # Assets to test (Crypto, Stocks, Commodities, Indices)
    assets = [
        "ETH-USD", "BTC-USD", "SOL-USD", # Crypto
        "NVDA", "TSLA", "AAPL",          # Stocks
        "GC=F", "CL=F",                  # Commodities
        "SPY", "QQQ"                     # Indices
    ]
    
    # Timeframes from user request
    timeframes = ["5m", "15m", "30m", "1h", "4h", "1d"]
    
    print(f"{'='*120}")
    print(f"{'Asset':<10} | {'Strategy':<20} | {'TF':<4} | {'Return':<8} | {'Win Rate':<8} | {'Trades':<6} | {'Status':<10}")
    print(f"{'-'*120}")
    
    for symbol in assets:
        for tf in timeframes:
            period = "60d" if tf in ["5m", "15m", "30m"] else "1y"
            
            try:
                df = yf.download(symbol, period=period, interval=tf, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    try: df.columns = df.columns.droplevel("Ticker")
                    except: df.columns = df.columns.droplevel(1)
                df = df.dropna()
                
                if df.empty: continue
                
                # Test ZigZag
                res_zz = backtest_strategy(df, swing_method="zigzag", swing_param=0.02)
                status_zz = "✅ PASS" if res_zz['return'] > 0 else "❌ FAIL"
                print(f"{symbol:<10} | {'Fib Zigzag':<20} | {tf:<4} | {res_zz['return']:>6.2f}% | {res_zz['win_rate']:>6.2f}% | {res_zz['trades']:<6} | {status_zz}")
                
                # Test Local Extrema
                res_le = backtest_strategy(df, swing_method="local_extrema", swing_param=5)
                status_le = "✅ PASS" if res_le['return'] > 0 else "❌ FAIL"
                print(f"{symbol:<10} | {'Fib Local Extrema':<20} | {tf:<4} | {res_le['return']:>6.2f}% | {res_le['win_rate']:>6.2f}% | {res_le['trades']:<6} | {status_le}")
                
                # Test Fractal
                res_fr = backtest_strategy(df, swing_method="fractal")
                status_fr = "✅ PASS" if res_fr['return'] > 0 else "❌ FAIL"
                print(f"{symbol:<10} | {'Fib Fractal':<20} | {tf:<4} | {res_fr['return']:>6.2f}% | {res_fr['win_rate']:>6.2f}% | {res_fr['trades']:<6} | {status_fr}")
                
            except Exception as e:
                # print(f"Error {symbol} {tf}: {e}")
                pass

if __name__ == "__main__":
    run_verification()
