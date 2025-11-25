#!/usr/bin/env python3
"""
Backtest: Scalp-Z Strategy (Stochastic + EMA)
Timeframes: 5m, 15m
Assets: ETH, BTC, TSLA, NVDA
"""

import os
import sys
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def download_data(symbol, period='5d', interval='5m'):
    """Download data from yfinance"""
    print(f"Downloading {symbol} data...")
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty:
        return df
    
    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Standardize column names
    df.columns = [c.lower() for c in df.columns]
    return df

def apply_indicators(df):
    """Apply Stochastic and EMA indicators"""
    # EMA 50 for Trend
    df['ema_50'] = ta.ema(df['close'], length=50)
    
    # Stochastic (14, 3, 3)
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
    df = pd.concat([df, stoch], axis=1)
    # Rename columns for clarity (pandas_ta names them STOCHk_14_3_3, STOCHd_14_3_3)
    df.rename(columns={'STOCHk_14_3_3': 'stoch_k', 'STOCHd_14_3_3': 'stoch_d'}, inplace=True)
    
    return df

def backtest_scalp_z(df, symbol, initial_capital=10000):
    """
    Scalp-Z Logic:
    Long Entry: Close > EMA 50 AND Stoch K < 20 AND Stoch K crosses above Stoch D
    Short Entry: Close < EMA 50 AND Stoch K > 80 AND Stoch K crosses below Stoch D
    Exit: Fixed RR (1:1.5) or Stoch Reversal (Long: K > 80, Short: K < 20)
    """
    if df.empty: return None
    
    df = apply_indicators(df)
    df.dropna(inplace=True)
    
    equity = initial_capital
    equity_curve = [initial_capital]
    trades = []
    
    position = 0 # 0: Flat, 1: Long, -1: Short
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0
    
    # Risk Management
    risk_per_trade = 0.01 # 1% risk
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Check Exit
        if position != 0:
            if position == 1:
                # Stop Loss
                if current['low'] <= stop_loss:
                    exit_price = stop_loss
                    pnl = (exit_price - entry_price) / entry_price * equity * risk_per_trade / abs(entry_price - stop_loss) * entry_price # Simplified PnL calc based on risk
                    # More accurate: qty = (equity * risk) / (entry - sl)
                    qty = (equity * risk_per_trade) / (entry_price - stop_loss)
                    pnl = (exit_price - entry_price) * qty
                    equity += pnl
                    trades.append({'type': 'LONG_SL', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                # Take Profit
                elif current['high'] >= take_profit:
                    exit_price = take_profit
                    qty = (equity * risk_per_trade) / (entry_price - stop_loss)
                    pnl = (exit_price - entry_price) * qty
                    equity += pnl
                    trades.append({'type': 'LONG_TP', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                # Stoch Reversal Exit (Optional - let's stick to TP/SL for pure scalping first, or maybe add as secondary)
                
            elif position == -1:
                # Stop Loss
                if current['high'] >= stop_loss:
                    exit_price = stop_loss
                    qty = (equity * risk_per_trade) / (stop_loss - entry_price)
                    pnl = (entry_price - exit_price) * qty
                    equity += pnl
                    trades.append({'type': 'SHORT_SL', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                # Take Profit
                elif current['low'] <= take_profit:
                    exit_price = take_profit
                    qty = (equity * risk_per_trade) / (stop_loss - entry_price)
                    pnl = (entry_price - exit_price) * qty
                    equity += pnl
                    trades.append({'type': 'SHORT_TP', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                    
        # Check Entry
        if position == 0:
            # Long: Uptrend + Oversold Crossover
            if current['close'] > current['ema_50'] and prev['stoch_k'] < 20 and current['stoch_k'] > current['stoch_d'] and prev['stoch_k'] <= prev['stoch_d']:
                entry_price = current['close']
                # SL at recent low or fixed %? Let's use recent low (last 5 candles)
                sl_price = df['low'].iloc[i-5:i].min()
                if sl_price >= entry_price: sl_price = entry_price * 0.995 # Fallback
                
                risk = entry_price - sl_price
                if risk == 0: continue
                
                stop_loss = sl_price
                take_profit = entry_price + (risk * 1.5) # 1:1.5 RR
                position = 1
                
            # Short: Downtrend + Overbought Crossover
            elif current['close'] < current['ema_50'] and prev['stoch_k'] > 80 and current['stoch_k'] < current['stoch_d'] and prev['stoch_k'] >= prev['stoch_d']:
                entry_price = current['close']
                sl_price = df['high'].iloc[i-5:i].max()
                if sl_price <= entry_price: sl_price = entry_price * 1.005 # Fallback
                
                risk = sl_price - entry_price
                if risk == 0: continue
                
                stop_loss = sl_price
                take_profit = entry_price - (risk * 1.5)
                position = -1
        
        equity_curve.append(equity) # Append equity at each step

    # Calculate performance metrics
    total_return = (equity - initial_capital) / initial_capital
    win_rate = len([t for t in trades if t['pnl'] > 0]) / len(trades) if trades else 0

    # Calculate Max Drawdown
    equity_series = pd.Series(equity_curve)
    if len(equity_series) > 1:
        returns = equity_series.pct_change().dropna()
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.cummax()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = drawdown.min() * 100
    else:
        max_drawdown = 0.0 # No trades or only initial capital

    return {
        'symbol': symbol,
        'final_equity': equity,
        'return': total_return * 100,
        'trades': len(trades),
        'win_rate': win_rate * 100,
        'max_drawdown': max_drawdown
    }

def main():
    assets = ['ETH-USD', 'BTC-USD', 'TSLA', 'NVDA']
    results = []
    
    print("=== Backtesting Scalp-Z Strategy (5m) ===")
    for symbol in assets:
        df = download_data(symbol, period='60d', interval='5m') # 60 days of 5m data
        res = backtest_scalp_z(df, symbol)
        if res:
            results.append(res)
            print(f"{symbol}: Return={res['return']:.2f}%, Trades={res['trades']}, WinRate={res['win_rate']:.1f}%, MaxDD={res['max_drawdown']:.2f}%")
            
    print("\n=== Backtesting Scalp-Z Strategy (15m) ===")
    for symbol in assets:
        df = download_data(symbol, period='60d', interval='15m') # 60 days of 15m data
        res = backtest_scalp_z(df, symbol)
        if res:
            print(f"{symbol} (15m): Return={res['return']:.2f}%, Trades={res['trades']}, WinRate={res['win_rate']:.1f}%, MaxDD={res['max_drawdown']:.2f}%")

if __name__ == "__main__":
    main()
