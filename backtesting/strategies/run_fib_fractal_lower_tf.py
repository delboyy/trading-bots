import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.fib_gold_backtest import backtest_fib_strategy, print_full_report
from backtesting.fib_gold_backtest import backtest_breakout_strategy # Import new function

def run():
    # Realistic Stress Test Asset List
    symbols = [
        # Crypto (High Beta) - 0.02% Fee
        "BTC-USD", "ETH-USD", "DOGE-USD", "SOL-USD", "ADA-USD",
        # Tech Stocks (Growth) - 0.1% Fee (Spread)
        "NVDA", "TSLA", "AMD",
        # Indices / ETFs (Broad Market) - 0.1% Fee
        "SPY", "QQQ", "IWM", "DIA", "MDY",
        # Sector ETFs
        "XLE", "XLF", "TLT", "EEM", "GLD", "SLV", "USO",
        # Commodities Futures - 0.1% Fee
        "GC=F", "CL=F"
    ]
    intervals = ["1h"]
    
    print(f"\n{'='*80}")
    print(f"REALISTIC BREAKOUT STRESS TEST (Dynamic Fees): 1h Timeframe (2 Years)")
    print(f"{'='*80}")
    
    results_summary = []
    
    import yfinance as yf
    from backtesting.fib_gold_backtest import backtest_breakout_strategy
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        
        # Determine Fee
        if "-USD" in symbol:
            fee = 0.0002 # 0.02% for Crypto
        else:
            fee = 0.001  # 0.1% for Stocks/Commodities (Spread/Comm)
            
        for interval in intervals:
            # Download Data
            df = yf.download(symbol, period="2y", interval=interval, progress=False)
            
            if isinstance(df.columns, pd.MultiIndex):
                try: df.columns = df.columns.droplevel("Ticker")
                except: df.columns = df.columns.droplevel(1)
            df = df.dropna()
            
            if df.empty:
                print(f"No data for {symbol}")
                continue
                
            # --- BREAKOUT STRATEGY ---
            # ZigZag 2% | EMA 50 | Break High/Low | Target 2R
            try:
                res = backtest_breakout_strategy(
                    interval=interval,
                    swing_method="zigzag",
                    swing_param=0.02,
                    trend_filter=True,
                    trend_ma_type="EMA",
                    trend_ma_period=50,
                    tp_r_multiple=2.0,
                    fee_pct=fee, 
                    data=df,
                    verbose=False
                )
                if res:
                    results_summary.append({
                        "symbol": symbol,
                        "trades": res["trades_count"],
                        "win_rate": res["win_rate"],
                        "return": res["total_return_pct"],
                        "fee": f"{fee*100:.2f}%",
                        "max_dd": res.get("max_drawdown_pct", 0.0)
                    })
            except Exception as e:
                print(f"Error {symbol}: {e}")

    # Sort and Print
    if results_summary:
        print(f"\n{'Symbol':<10} | {'Fee':<6} | {'Trades':<6} | {'Win Rate':<8} | {'Return':<8} | {'Max DD':<8}")
        print("-" * 70)
        # Sort by Return
        results_summary.sort(key=lambda x: x["return"], reverse=True)
        for r in results_summary:
            print(f"{r['symbol']:<10} | {r['fee']:<6} | {r['trades']:<6} | {r['win_rate']:>6.2f}% | {r['return']:>6.2f}% | {r['max_dd']:>6.2f}%")
    else:
        print("No trades generated.")

if __name__ == "__main__":
    import pandas as pd
    run()
