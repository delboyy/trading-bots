import sys
import os
import pandas as pd
import mplfinance as mpf
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.fib_gold_backtest import backtest_fib_strategy, download_gold

def plot_best_fractal_setup(interval="5m", symbol="GC=F"):
    print(f"Generating visualization for {symbol} on {interval}...")
    
    # User Best Settings
    swing_method = "fractal"
    swing_param = 3
    trend_filter = False
    entry_retrace = 0.618
    sl_retrace = 0.5
    tp_retrace = 0.236
    tp1_retrace = 0.382
    tp1_frac = 0.5
    move_stop_to_be = True
    
    # Download Data
    import yfinance as yf
    period = "5d" if interval == "5m" else "60d" # Short period for 5m to see details, longer for 1h
    if interval == "1h": period = "1y"
    
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    
    # Fix MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.droplevel("Ticker")
        except ValueError:
            df.columns = df.columns.droplevel(1)
    df = df.dropna()
    
    if df.empty:
        print("No data found.")
        return

    # Run Backtest to get trades
    results = backtest_fib_strategy(
        interval=interval,
        swing_method=swing_method,
        swing_param=swing_param,
        trend_filter=trend_filter,
        entry_retrace=entry_retrace,
        sl_retrace=sl_retrace,
        tp_retrace=tp_retrace,
        tp1_retrace=tp1_retrace,
        tp1_frac=tp1_frac,
        move_stop_to_be=move_stop_to_be,
        data=df,
        verbose=False
    )
    
    trades = results.get("trades", [])
    if not trades:
        print("No trades found to visualize.")
        return

    # Slice last 50 bars or so for a clear view, or find a section with trades
    # Let's find the last few trades
    last_trades = trades[-5:] if len(trades) >= 5 else trades
    if not last_trades:
        return

    # Get the time range for these trades
    start_time = pd.to_datetime(last_trades[0]["swing_low_time"]) # Approximate start
    end_time = pd.to_datetime(last_trades[-1]["exit_time"])
    
    # Add some buffer
    buffer = pd.Timedelta(hours=4 if interval == "5m" else 48)
    mask = (df.index >= start_time - buffer) & (df.index <= end_time + buffer)
    plot_df = df.loc[mask].copy()
    
    if plot_df.empty:
        plot_df = df.tail(100) # Fallback

    # Prepare ALines for Swings and Levels
    alines = []
    colors = []
    
    # We need to reconstruct the swings for this plot_df
    # Or just plot the trade levels for the trades in this window
    
    for t in last_trades:
        # Entry
        try:
            t_entry = pd.to_datetime(t["entry_time"])
            t_exit = pd.to_datetime(t["exit_time"])
            
            if t_entry < plot_df.index[0] or t_exit > plot_df.index[-1]:
                continue
                
            # Entry Line
            alines.append([(t_entry, t["entry_price"]), (t_exit, t["entry_price"])])
            colors.append('blue')
            
            # Exit Line (Price)
            alines.append([(t_exit, t["entry_price"]), (t_exit, t["exit_price"])])
            colors.append('black')
            
            # TP/SL levels (approximate visualization)
            # We don't have the exact SL/TP levels in the trade dict unless we added them.
            # But we can infer from entry price and direction.
            # Actually, let's just plot Entry and Exit for clarity.
            
        except Exception as e:
            print(f"Error processing trade for plot: {e}")
            continue

    # Plot
    title = f"{symbol} {interval} - Fractal Win 3 - No Trend Filter (Last 5 Trades)"
    filename = f"/Users/a1/.gemini/antigravity/brain/dff93ad5-a586-440e-8ad3-44c4baa0e51e/fractal_best_{interval}.png"
    
    # Custom Style
    s = mpf.make_mpf_style(base_mpf_style='charles', rc={'font.size': 8})
    
    mpf.plot(
        plot_df,
        type='candle',
        style=s,
        title=title,
        alines=dict(alines=alines, colors=colors, linewidths=1.5, alpha=0.7) if alines else None,
        volume=False,
        savefig=dict(fname=filename, dpi=100, bbox_inches='tight')
    )
    print(f"Saved chart to {filename}")

if __name__ == "__main__":
    plot_best_fractal_setup("5m", "GC=F")
    plot_best_fractal_setup("1h", "GC=F")
