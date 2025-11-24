import sys
import os
import pandas as pd
import mplfinance as mpf
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.fib_gold_backtest import backtest_fib_strategy

def plot_backtest_results(interval: str = "1h"):
    print(f"Running backtest for {interval}...")
    # Best setting from optimization: ZigZag 1% (0.01) with EMA 50
    results = backtest_fib_strategy(
        interval=interval, 
        swing_method="zigzag", 
        swing_param=0.01, 
        trend_ma_type="EMA", 
        trend_ma_period=50
    )
    
    if not results or "trades" not in results or not results["trades"]:
        print("No trades found to visualize.")
        return

    df = results["df"]
    trades = results["trades"]
    
    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.set_index("Time", inplace=True)

    # Filter to last 20 trades for clarity
    if len(trades) > 20:
        print(f"Filtering to last 20 trades (out of {len(trades)}) for visibility...")
        trades = trades[-20:]
        
        # Slice DF to cover the period of these trades
        # Start from the first swing high/low of the first trade
        start_time = pd.to_datetime(trades[0].get("swing_high_time") or trades[0]["entry_time"])
        # Go back a bit for context
        start_idx = df.index.searchsorted(start_time) - 50
        if start_idx < 0: start_idx = 0
        df = df.iloc[start_idx:]

    print(f"Visualizing {len(trades)} trades...")

    # Prepare overlays
    alines = []
    colors = []
    
    # Markers
    swing_highs_idx = []
    swing_highs_val = []
    swing_lows_idx = []
    swing_lows_val = []
    entries_idx = []
    entries_val = []
    exits_idx = []
    exits_val = []
    
    for t in trades:
        # Parse times
        t_entry = pd.to_datetime(t["entry_time"])
        t_exit = pd.to_datetime(t["exit_time"])
        t_swing_high = pd.to_datetime(t.get("swing_high_time")) if t.get("swing_high_time") else None
        t_swing_low = pd.to_datetime(t.get("swing_low_time")) if t.get("swing_low_time") else None
        
        entry_price = float(t["entry_price"])
        exit_price = float(t["exit_price"])
        
        # Collect markers
        entries_idx.append(t_entry)
        entries_val.append(entry_price)
        exits_idx.append(t_exit)
        exits_val.append(exit_price)
        
        if t_swing_high:
            swing_highs_idx.append(t_swing_high)
            # Try to get price from DF if possible, else approximate? 
            # We need exact price for marker. 
            # We can look it up in DF safely now that we have timestamps
            try:
                swing_highs_val.append(df.loc[t_swing_high]["High"])
            except KeyError:
                pass # Might be outside sliced df?
                
        if t_swing_low:
            swing_lows_idx.append(t_swing_low)
            try:
                swing_lows_val.append(df.loc[t_swing_low]["Low"])
            except KeyError:
                pass

        # Reconstruct levels lines
        if t_swing_high and t_swing_low:
            try:
                # Impulse Leg
                if t["type"] == "SHORT":
                    p_h = df.loc[t_swing_high]["High"]
                    p_l = df.loc[t_swing_low]["Low"]
                    alines.append([(t_swing_high, p_h), (t_swing_low, p_l)])
                    colors.append('gray')
                    
                    diff = p_h - p_l
                    sl = p_l + 0.786 * diff
                    tp = p_l + 0.236 * diff
                    
                    # Start levels from Swing Low
                    t_start = t_swing_low
                    
                else: # LONG
                    p_l = df.loc[t_swing_low]["Low"]
                    p_h = df.loc[t_swing_high]["High"]
                    alines.append([(t_swing_low, p_l), (t_swing_high, p_h)])
                    colors.append('gray')
                    
                    diff = p_h - p_l
                    sl = p_h - 0.786 * diff
                    tp = p_h - 0.236 * diff
                    
                    # Start levels from Swing High
                    t_start = t_swing_high

                # Plot Levels
                alines.append([(t_start, entry_price), (t_exit, entry_price)])
                colors.append('blue')
                alines.append([(t_start, sl), (t_exit, sl)])
                colors.append('red')
                alines.append([(t_start, tp), (t_exit, tp)])
                colors.append('green')
                
            except KeyError:
                pass

    # Plot
    s = mpf.make_mpf_style(base_mpf_style='charles', rc={'font.size': 8})
    apds = [
        mpf.make_addplot(df['Trend'], color='orange', width=1.5),
    ]
    
    # Add markers if we have them (need to align with df index)
    # We can use scatter plots with 'make_addplot' but we need a series with NaNs and values at specific points.
    
    def create_marker_series(indices, values, default=np.nan):
        s = pd.Series(default, index=df.index)
        for idx, val in zip(indices, values):
            if idx in s.index:
                s.loc[idx] = val
        return s

    if entries_idx:
        entry_series = create_marker_series(entries_idx, entries_val)
        apds.append(mpf.make_addplot(entry_series, type='scatter', markersize=50, marker='>', color='blue'))
        
    if exits_idx:
        exit_series = create_marker_series(exits_idx, exits_val)
        apds.append(mpf.make_addplot(exit_series, type='scatter', markersize=50, marker='x', color='black'))

    # Swing Highs/Lows markers
    # We might have duplicates if multiple trades share swings, but that's fine.
    if swing_highs_idx:
        sh_series = create_marker_series(swing_highs_idx, swing_highs_val)
        apds.append(mpf.make_addplot(sh_series, type='scatter', markersize=30, marker='v', color='purple'))
        
    if swing_lows_idx:
        sl_series = create_marker_series(swing_lows_idx, swing_lows_val)
        apds.append(mpf.make_addplot(sl_series, type='scatter', markersize=30, marker='^', color='purple'))

    title = (
        f"Gold ({interval}) Last 20 Trades (ZigZag 1% | EMA 50)\n"
        f"Win Rate: {results['win_rate']:.1f}% | Return: {results['total_return_pct']:.1f}%\n"
        f"Blue >: Entry | Black x: Exit | Purple v/^: Swing Points"
    )
    
    fig, axes = mpf.plot(
        df, 
        type='candle', 
        style=s,
        addplot=apds,
        alines=dict(alines=alines, colors=colors, linewidths=1.5, alpha=0.8),
        title=title,
        returnfig=True,
        figsize=(14, 8)
    )
    
    fig.savefig("fib_swings_check.png")
    print("Saved plot to fib_swings_check.png")

if __name__ == "__main__":
    plot_backtest_results()
