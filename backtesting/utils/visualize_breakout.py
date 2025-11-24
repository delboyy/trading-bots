import sys
import os
import pandas as pd
import mplfinance as mpf
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.fib_gold_backtest import backtest_breakout_strategy, download_gold

def plot_breakout_setup(symbol="BTC-USD", interval="1h"):
    print(f"Generating visualization for {symbol} on {interval}...")
    
    # Download Data
    import yfinance as yf
    df = yf.download(symbol, period="60d", interval=interval, progress=False) # Last 60 days for clear view
    
    if isinstance(df.columns, pd.MultiIndex):
        try: df.columns = df.columns.droplevel("Ticker")
        except: df.columns = df.columns.droplevel(1)
    df = df.dropna()
    
    if df.empty:
        print("No data found.")
        return

    # Run Backtest
    results = backtest_breakout_strategy(
        interval=interval,
        swing_method="zigzag",
        swing_param=0.02,
        trend_filter=True,
        trend_ma_type="EMA",
        trend_ma_period=50,
        tp_r_multiple=2.0,
        data=df,
        verbose=False
    )
    
    trades = results.get("trades", [])
    if not trades:
        print("No trades found to visualize.")
        return

    # Slice last 100 bars
    plot_df = df.tail(150).copy()
    
    # Prepare ALines
    alines = []
    colors = []
    
    for t in trades:
        try:
            t_entry_time = pd.to_datetime(t["entry_time"])
            t_exit_time = pd.to_datetime(t["exit_time"])
            
            if t_entry_time < plot_df.index[0] or t_exit_time > plot_df.index[-1]:
                continue
            
            entry_price = t["entry_price"]
            exit_price = t["exit_price"]
            
            # Entry Line (Blue)
            alines.append([(t_entry_time, entry_price), (t_exit_time, entry_price)])
            colors.append('blue')
            
            # Outcome Line (Green for Win, Red for Loss)
            color = 'green' if t["result_pct"] > 0 else 'red'
            alines.append([(t_exit_time, entry_price), (t_exit_time, exit_price)])
            colors.append(color)
            
        except Exception as e:
            continue

    # Plot
    title = f"{symbol} {interval} - Breakout Strategy (ZigZag 2%, 2R)"
    filename = f"/Users/a1/.gemini/antigravity/brain/dff93ad5-a586-440e-8ad3-44c4baa0e51e/breakout_viz_{symbol}.png"
    
    s = mpf.make_mpf_style(base_mpf_style='charles', rc={'font.size': 8})
    
    # Add EMA 50
    ema = df['Close'].ewm(span=50, adjust=False).mean().tail(150)
    ap = mpf.make_addplot(ema, color='orange', width=1.0)
    
    mpf.plot(
        plot_df,
        type='candle',
        style=s,
        title=title,
        addplot=ap,
        alines=dict(alines=alines, colors=colors, linewidths=1.5, alpha=0.8) if alines else None,
        volume=False,
        savefig=dict(fname=filename, dpi=100, bbox_inches='tight')
    )
    print(f"Saved chart to {filename}")

if __name__ == "__main__":
    plot_breakout_setup("BTC-USD", "1h")
