#!/usr/bin/env python3
"""
Backtest: Momentum-X Strategy (MACD + RSI)
Timeframes: 15m, 30m
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

def download_data(symbol, period='1mo', interval='15m'):
    """Download data from yfinance"""
    print(f"Downloading {symbol} data...")
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty:
        return df
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [c.lower() for c in df.columns]
    return df

def apply_indicators(df):
    """Apply MACD and RSI indicators"""
    # MACD (12, 26, 9)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)
    # Rename columns: MACD_12_26_9 -> macd, MACDs_12_26_9 -> signal, MACDh_12_26_9 -> hist
    df.rename(columns={'MACD_12_26_9': 'macd', 'MACDs_12_26_9': 'signal', 'MACDh_12_26_9': 'hist'}, inplace=True)
    
    # RSI (14)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    return df

def backtest_momentum_x(df, symbol, initial_capital=10000):
    """
    Momentum-X Logic:
    Long Entry: MACD crosses above Signal AND RSI > 50 AND RSI < 70
    Short Entry: MACD crosses below Signal AND RSI < 50 AND RSI > 30
    Exit: MACD Cross reversal or Trailing Stop (ATR based)
    """
    if df.empty: return None
    
    df = apply_indicators(df)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df.dropna(inplace=True)
    
    position = 0
    entry_price = 0
    stop_loss = 0
    equity = initial_capital
    trades = []
    
    risk_per_trade = 0.01
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Check Exit
        if position != 0:
            if position == 1:
                # Trailing Stop
                new_sl = current['close'] - (2 * current['atr'])
                stop_loss = max(stop_loss, new_sl)
                
                if current['low'] <= stop_loss:
                    exit_price = stop_loss
                    qty = (equity * risk_per_trade) / (entry_price * 0.02) # Assumed risk for qty calc if SL dynamic
                    pnl = (exit_price - entry_price) * qty
                    equity += pnl
                    trades.append({'type': 'LONG_EXIT', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                # MACD Reversal Exit
                elif current['macd'] < current['signal']:
                    exit_price = current['close']
                    qty = (equity * risk_per_trade) / (entry_price * 0.02)
                    pnl = (exit_price - entry_price) * qty
                    equity += pnl
                    trades.append({'type': 'LONG_MACD_EXIT', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                    
            elif position == -1:
                new_sl = current['close'] + (2 * current['atr'])
                stop_loss = min(stop_loss, new_sl)
                
                if current['high'] >= stop_loss:
                    exit_price = stop_loss
                    qty = (equity * risk_per_trade) / (entry_price * 0.02)
                    pnl = (entry_price - exit_price) * qty
                    equity += pnl
                    trades.append({'type': 'SHORT_EXIT', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                elif current['macd'] > current['signal']:
                    exit_price = current['close']
                    qty = (equity * risk_per_trade) / (entry_price * 0.02)
                    pnl = (entry_price - exit_price) * qty
                    equity += pnl
                    trades.append({'type': 'SHORT_MACD_EXIT', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                    
        # Check Entry
        if position == 0:
            # Long: MACD Crossover + RSI Bullish
            if current['macd'] > current['signal'] and prev['macd'] <= prev['signal'] and current['rsi'] > 50 and current['rsi'] < 70:
                entry_price = current['close']
                stop_loss = current['close'] - (2 * current['atr'])
                position = 1
                
            # Short: MACD Crossunder + RSI Bearish
            elif current['macd'] < current['signal'] and prev['macd'] >= prev['signal'] and current['rsi'] < 50 and current['rsi'] > 30:
                entry_price = current['close']
                stop_loss = current['close'] + (2 * current['atr'])
                position = -1

    return {
        'symbol': symbol,
        'final_equity': equity,
        'return': (equity - initial_capital) / initial_capital * 100,
        'trades': len(trades),
        'win_rate': len([t for t in trades if t['pnl'] > 0]) / len(trades) * 100 if trades else 0
    }

def main():
    assets = ['ETH-USD', 'BTC-USD', 'TSLA', 'NVDA']
    
    print("=== Backtesting Momentum-X Strategy (15m) ===")
    for symbol in assets:
        df = download_data(symbol, period='60d', interval='15m')
        res = backtest_momentum_x(df, symbol)
        if res:
            print(f"{symbol}: Return={res['return']:.2f}%, Trades={res['trades']}, WinRate={res['win_rate']:.1f}%")
            
    print("\n=== Backtesting Momentum-X Strategy (30m) ===")
    for symbol in assets:
        df = download_data(symbol, period='60d', interval='30m')
        res = backtest_momentum_x(df, symbol)
        if res:
            print(f"{symbol} (30m): Return={res['return']:.2f}%, Trades={res['trades']}, WinRate={res['win_rate']:.1f}%")

if __name__ == "__main__":
    main()
