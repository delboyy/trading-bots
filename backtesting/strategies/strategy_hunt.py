import pandas as pd
import yfinance as yf
import numpy as np

# --- Indicators ---
def calculate_donchian(series, window=20):
    upper = series.rolling(window=window).max()
    lower = series.rolling(window=window).min()
    return lower, upper

def calculate_sma(series, window=50):
    return series.rolling(window=window).mean()

def calculate_atr(df, window=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

# --- Helpers ---
def calculate_max_drawdown(trades):
    if not trades: return 0.0
    peak = 1.0
    max_dd = 0.0
    curr_equity = 1.0
    for t in trades:
        curr_equity *= (1.0 + t)
        if curr_equity > peak:
            peak = curr_equity
        dd = (peak - curr_equity) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100.0

# --- Strategies ---
def backtest_donchian_strategy(df, window=20, fee_pct=0.001):
    """
    Turtle Trading Logic:
    Long: Break above 20-period High
    Short: Break below 20-period Low
    Exit: Break below 10-period Low (Long) / Above 10-period High (Short)
    """
    if df.empty: return {}
    df = df.copy()
    df['Lower'], df['Upper'] = calculate_donchian(df['Close'], window)
    df['Exit_Lower'], df['Exit_Upper'] = calculate_donchian(df['Close'], int(window/2))
    
    trades = []
    in_trade = False
    entry_price = 0
    entry_type = None
    equity = 1000.0
    
    for i in range(window, len(df)):
        price = df['Close'].iloc[i]
        upper = df['Upper'].iloc[i-1] # Use previous bar to avoid lookahead
        lower = df['Lower'].iloc[i-1]
        exit_upper = df['Exit_Upper'].iloc[i-1]
        exit_lower = df['Exit_Lower'].iloc[i-1]
        
        if np.isnan(upper): continue
        
        if not in_trade:
            if price > upper:
                entry_price = price
                entry_type = "LONG"
                in_trade = True
            elif price < lower:
                entry_price = price
                entry_type = "SHORT"
                in_trade = True
        else:
            if entry_type == "LONG":
                if price < exit_lower: # Exit
                    res = (price - entry_price) / entry_price
                    res -= (fee_pct * 2)
                    equity *= (1.0 + res)
                    trades.append(res)
                    in_trade = False
            elif entry_type == "SHORT":
                if price > exit_upper: # Exit
                    res = (entry_price - price) / entry_price
                    res -= (fee_pct * 2)
                    equity *= (1.0 + res)
                    trades.append(res)
                    in_trade = False

    return {
        "return": (equity - 1000.0) / 1000.0 * 100,
        "trades": len(trades),
        "win_rate": len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0,
        "max_drawdown": calculate_max_drawdown(trades)
    }

def backtest_sma_cross_strategy(df, fast=50, slow=200, fee_pct=0.001):
    """
    Golden Cross Logic:
    Long: SMA 50 > SMA 200
    Short: SMA 50 < SMA 200
    """
    if df.empty: return {}
    df = df.copy()
    df['Fast'] = calculate_sma(df['Close'], fast)
    df['Slow'] = calculate_sma(df['Close'], slow)
    
    trades = []
    in_trade = False
    entry_price = 0
    entry_type = None
    equity = 1000.0
    
    for i in range(slow, len(df)):
        price = df['Close'].iloc[i]
        f = df['Fast'].iloc[i]
        s = df['Slow'].iloc[i]
        prev_f = df['Fast'].iloc[i-1]
        prev_s = df['Slow'].iloc[i-1]
        
        if np.isnan(f) or np.isnan(s): continue
        
        cross_up = prev_f < prev_s and f > s
        cross_down = prev_f > prev_s and f < s
        
        if not in_trade:
            if cross_up:
                entry_price = price
                entry_type = "LONG"
                in_trade = True
            elif cross_down:
                entry_price = price
                entry_type = "SHORT"
                in_trade = True
        else:
            if entry_type == "LONG" and cross_down:
                res = (price - entry_price) / entry_price
                res -= (fee_pct * 2)
                equity *= (1.0 + res)
                trades.append(res)
                entry_price = price
                entry_type = "SHORT"
            elif entry_type == "SHORT" and cross_up:
                res = (entry_price - price) / entry_price
                res -= (fee_pct * 2)
                equity *= (1.0 + res)
                trades.append(res)
                entry_price = price
                entry_type = "LONG"

    return {
        "return": (equity - 1000.0) / 1000.0 * 100,
        "trades": len(trades),
        "win_rate": len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0,
        "max_drawdown": calculate_max_drawdown(trades)
    }

def backtest_volatility_breakout(df, atr_period=14, k=1.5, fee_pct=0.001):
    """
    Volatility Breakout:
    Long: Close > Open + (k * ATR)
    Short: Close < Open - (k * ATR)
    Exit: End of Bar (Intraday) or Stop Loss
    """
    if df.empty: return {}
    df = df.copy()
    df['ATR'] = calculate_atr(df, atr_period)
    
    trades = []
    equity = 1000.0
    
    for i in range(atr_period, len(df)):
        open_p = df['Open'].iloc[i]
        close_p = df['Close'].iloc[i]
        atr = df['ATR'].iloc[i-1]
        
        if np.isnan(atr): continue
        
        # Long
        if close_p > open_p + (k * atr):
            res = (close_p - (open_p + k*atr)) / (open_p + k*atr) # Simplified entry at breakout level
            # Actually, if we enter at breakout, we capture (Close - BreakoutLevel)
            entry = open_p + (k * atr)
            res = (close_p - entry) / entry
            res -= (fee_pct * 2)
            equity *= (1.0 + res)
            trades.append(res)
            
        # Short
        elif close_p < open_p - (k * atr):
            entry = open_p - (k * atr)
            res = (entry - close_p) / entry
            res -= (fee_pct * 2)
            equity *= (1.0 + res)
            trades.append(res)

    return {
        "return": (equity - 1000.0) / 1000.0 * 100,
        "trades": len(trades),
        "win_rate": len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0,
        "max_drawdown": calculate_max_drawdown(trades)
    }

def run_hunt():
    symbols = ["GC=F", "CL=F", "SPY", "QQQ", "DIA", "IWM"]
    interval = "1h"
    
    print(f"\n{'='*80}")
    print(f"ADVANCED STRATEGY HUNT (1h, 2 Years, 0.1% Fee)")
    print(f"{'='*80}")
    
    results = []
    
    for symbol in symbols:
        print(f"Testing {symbol}...")
        df = yf.download(symbol, period="2y", interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            try: df.columns = df.columns.droplevel("Ticker")
            except: df.columns = df.columns.droplevel(1)
        df = df.dropna()
        
        # Donchian
        res_don = backtest_donchian_strategy(df)
        results.append({"symbol": symbol, "strategy": "Turtle (Donchian)", **res_don})
        
        # SMA Cross
        res_sma = backtest_sma_cross_strategy(df)
        results.append({"symbol": symbol, "strategy": "SMA Cross 50/200", **res_sma})
        
        # Volatility Breakout
        res_vol = backtest_volatility_breakout(df)
        results.append({"symbol": symbol, "strategy": "Vol Breakout", **res_vol})
        
    print(f"\n{'Symbol':<8} | {'Strategy':<20} | {'Return':<8} | {'Win Rate':<8} | {'Trades':<6} | {'Max DD':<8}")
    print("-" * 75)
    results.sort(key=lambda x: x["return"], reverse=True)
    for r in results:
        print(f"{r['symbol']:<8} | {r['strategy']:<20} | {r['return']:>6.2f}% | {r['win_rate']:>6.2f}% | {r['trades']:<6} | {r['max_drawdown']:>6.2f}%")

if __name__ == "__main__":
    run_hunt()
