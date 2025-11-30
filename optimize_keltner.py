#!/usr/bin/env python3
"""
KELTNER CHANNEL OPTIMIZER
Tests multiple ATR multipliers and parameters to find optimal settings
"""

import pandas as pd
import numpy as np
from pathlib import Path
from itertools import product

class KeltnerOptimizer:
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = 10000
        self.fee_rate = 0.0001
        
    def calculate_indicators(self, df, ema_period, atr_period, atr_multiplier):
        """Calculate Keltner Channels"""
        df = df.copy()
        
        # EMA (centerline)
        df['EMA'] = df['close'].ewm(span=ema_period, adjust=False).mean()
        
        # ATR
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].ewm(span=atr_period, adjust=False).mean()
        
        # Keltner Channels
        df['Upper_KC'] = df['EMA'] + (atr_multiplier * df['ATR'])
        df['Lower_KC'] = df['EMA'] - (atr_multiplier * df['ATR'])
        
        # Volume Filter
        df['Vol_MA'] = df['volume'].rolling(20).mean()
        
        # Trend Filter
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        return df
    
    def backtest(self, df, params):
        """Run backtest with given parameters"""
        ema_period = params['ema_period']
        atr_period = params['atr_period']
        atr_multiplier = params['atr_multiplier']
        volume_multiplier = params['volume_multiplier']
        use_trend_filter = params['use_trend_filter']
        stop_loss_pct = params['stop_loss_pct']
        take_profit_pct = params['take_profit_pct']
        
        df = self.calculate_indicators(df, ema_period, atr_period, atr_multiplier)
        
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        
        start_idx = max(ema_period, atr_period, 200 if use_trend_filter else 0) + 10
        
        for i in range(start_idx, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            current_price = current['close']
            
            # Exit logic
            if position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
                
                should_exit = False
                reason = ""
                
                # Stop Loss
                if pnl_pct < -stop_loss_pct:
                    should_exit = True
                    reason = "SL"
                
                # Take Profit
                elif pnl_pct > take_profit_pct:
                    should_exit = True
                    reason = "TP"
                
                # Channel Re-entry
                elif position > 0 and current_price < current['Upper_KC']:
                    should_exit = True
                    reason = "Channel_Reentry"
                elif position < 0 and current_price > current['Lower_KC']:
                    should_exit = True
                    reason = "Channel_Reentry"
                
                if should_exit:
                    size = abs(position)
                    if position > 0:
                        pnl = size * (current_price - entry_price)
                    else:
                        pnl = size * (entry_price - current_price)
                    
                    entry_fee = size * entry_price * self.fee_rate
                    exit_fee = size * current_price * self.fee_rate
                    total_fee = entry_fee + exit_fee
                    
                    capital += pnl - total_fee
                    
                    trades[-1]['exit_price'] = current_price
                    trades[-1]['pnl'] = pnl - total_fee
                    trades[-1]['reason'] = reason
                    
                    position = 0
                    entry_price = 0
            
            # Entry logic
            if position == 0:
                volume_ok = current['volume'] > current['Vol_MA'] * volume_multiplier
                
                # Trend filter
                trend_ok_long = True
                trend_ok_short = True
                if use_trend_filter:
                    trend_ok_long = current_price > current['EMA_200']
                    trend_ok_short = current_price < current['EMA_200']
                
                # Bullish Breakout
                if (prev['close'] <= prev['Upper_KC'] and 
                    current_price > current['Upper_KC'] and 
                    volume_ok and trend_ok_long):
                    
                    position_size = capital / current_price
                    position = position_size
                    entry_price = current_price
                    trades.append({'type': 'buy', 'price': current_price})
                
                # Bearish Breakout
                elif (prev['close'] >= prev['Lower_KC'] and 
                      current_price < current['Lower_KC'] and 
                      volume_ok and trend_ok_short):
                    
                    position_size = capital / current_price
                    position = -position_size
                    entry_price = current_price
                    trades.append({'type': 'sell', 'price': current_price})
        
        # Calculate metrics
        completed_trades = [t for t in trades if 'exit_price' in t]
        
        if not completed_trades:
            return None
        
        df_trades = pd.DataFrame(completed_trades)
        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(df_trades[df_trades['pnl'] > 0]) / len(df_trades) * 100
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': len(df_trades),
            'final_capital': capital,
            'params': params
        }
    
    def optimize(self, data_path):
        """Test multiple parameter combinations"""
        print(f"\n{'='*70}")
        print(f"KELTNER CHANNEL OPTIMIZATION - {self.symbol} {self.timeframe}")
        print(f"{'='*70}\n")
        
        # Load data
        df = pd.read_parquet(data_path)
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"Loaded {len(df)} candles\n")
        
        # Parameter grid
        param_grid = {
            'ema_period': [20, 30],
            'atr_period': [14, 20],
            'atr_multiplier': [2.0, 2.5, 3.0, 3.5],
            'volume_multiplier': [1.2, 1.5, 1.8],
            'use_trend_filter': [False, True],
            'stop_loss_pct': [0.015, 0.02],
            'take_profit_pct': [0.03, 0.04]
        }
        
        # Generate all combinations
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = [dict(zip(keys, v)) for v in product(*values)]
        
        print(f"Testing {len(combinations)} parameter combinations...\n")
        
        results = []
        for i, params in enumerate(combinations):
            if (i + 1) % 50 == 0:
                print(f"Progress: {i+1}/{len(combinations)}")
            
            result = self.backtest(df, params)
            if result:
                results.append(result)
        
        # Sort by total return
        results.sort(key=lambda x: x['total_return'], reverse=True)
        
        # Print top 10
        print(f"\n{'='*70}")
        print(f"TOP 10 PARAMETER COMBINATIONS")
        print(f"{'='*70}\n")
        
        for i, result in enumerate(results[:10], 1):
            print(f"#{i}")
            print(f"  Total Return: {result['total_return']:.2f}%")
            print(f"  Win Rate: {result['win_rate']:.2f}%")
            print(f"  Total Trades: {result['total_trades']}")
            print(f"  Parameters:")
            for key, value in result['params'].items():
                print(f"    {key}: {value}")
            print()
        
        return results

def main():
    """Optimize Keltner Channel on multiple assets"""
    assets = [
        ('BTCUSDT', '1h'),
        ('ETHUSDT', '1h'),
    ]
    
    all_results = {}
    
    for symbol, timeframe in assets:
        data_path = Path(f"data/processed/binance_{symbol}_{timeframe}_combined.parquet")
        
        if not data_path.exists():
            print(f"⏭️  Skipping {symbol} {timeframe} - data not found")
            continue
        
        optimizer = KeltnerOptimizer(symbol, timeframe)
        results = optimizer.optimize(data_path)
        all_results[f"{symbol}_{timeframe}"] = results
        
        print("\n" + "="*70 + "\n")
    
    # Save results
    print("Optimization complete!")

if __name__ == "__main__":
    main()
