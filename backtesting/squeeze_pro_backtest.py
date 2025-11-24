#!/usr/bin/env python3
"""
Backtest: Squeeze-Pro Strategy (Bollinger Band Squeeze)
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
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [c.lower() for c in df.columns]
    return df

def apply_indicators(df):
    """Apply Bollinger Bands and Keltner Channels for Squeeze"""
    # Bollinger Bands (20, 2)
    bb = ta.bbands(df['close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    # Rename: BBL_20_2.0 -> lower, BBM_20_2.0 -> middle, BBU_20_2.0 -> upper, BBB_20_2.0 -> bandwidth
    df.rename(columns={'BBL_20_2.0': 'bb_lower', 'BBM_20_2.0': 'bb_middle', 'BBU_20_2.0': 'bb_upper', 'BBB_20_2.0': 'bb_width'}, inplace=True)
    
    # Keltner Channels (20, 1.5) - Squeeze is often defined as BB inside KC
    # But simpler definition: Bandwidth < Threshold (e.g., 1% for stocks, 0.5% for crypto?)
    # Let's use Bandwidth percentile for relative squeeze
    df['bb_width_pct'] = df['bb_width'].rolling(100).rank(pct=True)
    
    return df

def backtest_squeeze_pro(df, symbol, initial_capital=10000):
    """
    Squeeze-Pro Logic:
    Squeeze: BB Width is in lowest 20th percentile (Low Volatility)
    Long Entry: Close breaks above Upper Band
    Short Entry: Close breaks below Lower Band
    Exit: Close returns to Middle Band (Mean Reversion) or Fixed RR
    """
    if df.empty: return None
    
    df = apply_indicators(df)
    df.dropna(inplace=True)
    
    position = 0
    entry_price = 0
    stop_loss = 0
    equity = initial_capital
    trades = []
    
    risk_per_trade = 0.01
    in_squeeze = False
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Check Squeeze Status
        if current['bb_width_pct'] < 0.20:
            in_squeeze = True
        elif current['bb_width_pct'] > 0.50:
            in_squeeze = False # Volatility expanded
            
        # Check Exit
        if position != 0:
            if position == 1:
                # Stop Loss
                if current['low'] <= stop_loss:
                    exit_price = stop_loss
                    qty = (equity * risk_per_trade) / (entry_price - stop_loss)
                    pnl = (exit_price - entry_price) * qty
                    equity += pnl
                    trades.append({'type': 'LONG_SL', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                # Take Profit (Mean Reversion to Middle Band? No, breakout usually rides the band)
                # Let's use trailing stop on the Middle Band
                elif current['close'] < current['bb_middle']:
                    exit_price = current['close']
                    qty = (equity * risk_per_trade) / (entry_price - stop_loss)
                    pnl = (exit_price - entry_price) * qty
                    equity += pnl
                    trades.append({'type': 'LONG_EXIT', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                    
            elif position == -1:
                if current['high'] >= stop_loss:
                    exit_price = stop_loss
                    qty = (equity * risk_per_trade) / (stop_loss - entry_price)
                    pnl = (entry_price - exit_price) * qty
                    equity += pnl
                    trades.append({'type': 'SHORT_SL', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                elif current['close'] > current['bb_middle']:
                    exit_price = current['close']
                    qty = (equity * risk_per_trade) / (stop_loss - entry_price)
                    pnl = (entry_price - exit_price) * qty
                    equity += pnl
                    trades.append({'type': 'SHORT_EXIT', 'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'time': current.name})
                    position = 0
                    
        # Check Entry
        if position == 0 and in_squeeze:
            # Long Breakout
            if current['close'] > current['bb_upper']:
                entry_price = current['close']
                stop_loss = current['bb_middle'] # Stop at mean
                position = 1
                in_squeeze = False # Breakout occurred
                
            # Short Breakout
            elif current['close'] < current['bb_lower']:
                entry_price = current['close']
                stop_loss = current['bb_middle']
                position = -1
                in_squeeze = False

    return {
        'symbol': symbol,
        'final_equity': equity,
        'return': (equity - initial_capital) / initial_capital * 100,
        'trades': len(trades),
        'win_rate': len([t for t in trades if t['pnl'] > 0]) / len(trades) * 100 if trades else 0
    }

def main():
    assets = ['ETH-USD', 'BTC-USD', 'TSLA', 'NVDA']
    
    print("=== Backtesting Squeeze-Pro Strategy (5m) ===")
    for symbol in assets:
        df = download_data(symbol, period='5d', interval='5m')
        res = backtest_squeeze_pro(df, symbol)
        if res:
            print(f"{symbol}: Return={res['return']:.2f}%, Trades={res['trades']}, WinRate={res['win_rate']:.1f}%")
            
    print("\n=== Backtesting Squeeze-Pro Strategy (15m) ===")
    for symbol in assets:
        df = download_data(symbol, period='1mo', interval='15m')
        res = backtest_squeeze_pro(df, symbol)
        if res:
            print(f"{symbol} (15m): Return={res['return']:.2f}%, Trades={res['trades']}, WinRate={res['win_rate']:.1f}%")

if __name__ == "__main__":
    main()
