#!/usr/bin/env python3
"""
ETH 1H HIGH VOLATILITY BREAKOUT BOT
Backtest-only version - DO NOT deploy live until paper trading validates results

Strategy:
- Trades ETH on 1h timeframe
- Enters on Z-Score breakouts during high volatility periods
- Exits on SMA trend reversals
- Target: 0.07% daily return (51% over 2 years backtested)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import time

class ETHVolBreakoutBot:
    def __init__(self, backtest_mode=True):
        self.symbol = "ETHUSDT"
        self.timeframe = "1h"
        self.backtest_mode = backtest_mode
        
        # Strategy Parameters (from backtest)
        self.z_entry_threshold = 2.0  # Z-Score breakout level
        self.stop_loss_pct = 0.01     # 1% stop loss
        self.fee_rate = 0.0001        # 0.01% for limit orders on HyperLiquid
        
        # Indicator Parameters
        self.z_window = 20            # Z-Score lookback
        self.atr_period = 14          # ATR calculation
        self.atr_ma_period = 50       # ATR moving average
        
        # State
        self.position = 0             # 0 = no position, >0 = long, <0 = short
        self.entry_price = 0
        self.capital = 10000          # Starting capital for backtest
        
    def calculate_indicators(self, df):
        """Calculate all required indicators"""
        df = df.copy()
        
        # Z-Score for breakout detection
        df['SMA'] = df['close'].rolling(self.z_window).mean()
        df['StdDev'] = df['close'].rolling(self.z_window).std()
        df['ZScore'] = (df['close'] - df['SMA']) / df['StdDev']
        
        # ATR for volatility regime detection
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(self.atr_period).mean()
        df['ATR_MA'] = df['ATR'].rolling(self.atr_ma_period).mean()
        
        return df
    
    def get_signal(self, row):
        """
        Determine trading signal based on current market conditions
        
        Returns: 'buy', 'sell', 'exit', or 'hold'
        """
        current_price = row['close']
        z_score = row['ZScore']
        atr = row['ATR']
        atr_ma = row['ATR_MA']
        sma = row['SMA']
        
        # Check if we're in high volatility regime
        is_high_vol = atr > atr_ma
        
        # Entry Logic
        if self.position == 0:
            if is_high_vol:
                # Bullish breakout - price breaking above upper band
                if z_score > self.z_entry_threshold:
                    return 'buy'
                # Bearish breakout - price breaking below lower band
                elif z_score < -self.z_entry_threshold:
                    return 'sell'
        
        # Exit Logic
        elif self.position > 0:  # Long position
            # Exit if price crosses below SMA (trend reversal)
            if current_price < sma:
                return 'exit'
                
        elif self.position < 0:  # Short position
            # Exit if price crosses above SMA (trend reversal)
            if current_price > sma:
                return 'exit'
        
        return 'hold'
    
    def backtest(self, data_path):
        """
        Run backtest on historical data
        
        Args:
            data_path: Path to parquet file with OHLCV data
        """
        print(f"\n{'='*60}")
        print(f"ETH 1H HIGH VOLATILITY BREAKOUT - BACKTEST")
        print(f"{'='*60}\n")
        
        # Load data
        df = pd.read_parquet(data_path)
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"Loaded {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Backtest variables
        capital = self.capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [capital]
        
        # Run through historical data
        for i in range(self.atr_ma_period, len(df)):
            row = df.iloc[i]
            current_price = row['close']
            current_time = row['timestamp']
            
            signal = self.get_signal(row)
            
            # Execute trades
            if signal == 'buy' and position == 0:
                # Enter long
                position_size = capital / current_price
                fee = position_size * current_price * self.fee_rate
                position = position_size
                entry_price = current_price
                trades.append({
                    'time': current_time,
                    'type': 'buy',
                    'price': current_price,
                    'size': position_size
                })
                
            elif signal == 'sell' and position == 0:
                # Enter short
                position_size = capital / current_price
                fee = position_size * current_price * self.fee_rate
                position = -position_size
                entry_price = current_price
                trades.append({
                    'time': current_time,
                    'type': 'sell',
                    'price': current_price,
                    'size': position_size
                })
                
            elif signal == 'exit' and position != 0:
                # Exit position
                size = abs(position)
                
                # Calculate PnL
                if position > 0:
                    pnl = size * (current_price - entry_price)
                else:
                    pnl = size * (entry_price - current_price)
                
                # Calculate fees
                entry_fee = size * entry_price * self.fee_rate
                exit_fee = size * current_price * self.fee_rate
                total_fee = entry_fee + exit_fee
                
                # Update capital
                capital += pnl - total_fee
                
                # Record trade
                trades[-1]['exit_time'] = current_time
                trades[-1]['exit_price'] = current_price
                trades[-1]['pnl'] = pnl - total_fee
                trades[-1]['pnl_pct'] = (pnl - total_fee) / (size * entry_price) * 100
                
                position = 0
                entry_price = 0
            
            # Check stop loss
            if position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
                if pnl_pct < -self.stop_loss_pct:
                    # Stop loss hit
                    size = abs(position)
                    if position > 0:
                        pnl = size * (current_price - entry_price)
                    else:
                        pnl = size * (entry_price - current_price)
                    
                    entry_fee = size * entry_price * self.fee_rate
                    exit_fee = size * current_price * self.fee_rate
                    total_fee = entry_fee + exit_fee
                    
                    capital += pnl - total_fee
                    
                    trades[-1]['exit_time'] = current_time
                    trades[-1]['exit_price'] = current_price
                    trades[-1]['pnl'] = pnl - total_fee
                    trades[-1]['pnl_pct'] = (pnl - total_fee) / (size * entry_price) * 100
                    trades[-1]['reason'] = 'stop_loss'
                    
                    position = 0
                    entry_price = 0
            
            equity_curve.append(capital)
        
        # Calculate results
        self._print_results(trades, equity_curve, df)
        
        return trades, equity_curve
    
    def _print_results(self, trades, equity_curve, df):
        """Print backtest results"""
        if not trades:
            print("❌ No trades executed")
            return
        
        # Filter completed trades
        completed_trades = [t for t in trades if 'exit_time' in t]
        
        if not completed_trades:
            print("❌ No completed trades")
            return
        
        df_trades = pd.DataFrame(completed_trades)
        
        # Calculate metrics
        total_return = (equity_curve[-1] - self.capital) / self.capital * 100
        winning_trades = df_trades[df_trades['pnl'] > 0]
        losing_trades = df_trades[df_trades['pnl'] <= 0]
        win_rate = len(winning_trades) / len(df_trades) * 100
        
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Time metrics
        start_date = df['timestamp'].min()
        end_date = df['timestamp'].max()
        total_days = (end_date - start_date).days
        daily_return = total_return / total_days if total_days > 0 else 0
        
        # Print results
        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*60}\n")
        
        print(f"📊 Performance:")
        print(f"   Total Return:        {total_return:>10.2f}%")
        print(f"   Daily Return (avg):  {daily_return:>10.3f}%")
        print(f"   Final Capital:       ${equity_curve[-1]:>10.2f}")
        print(f"   Starting Capital:    ${self.capital:>10.2f}")
        
        print(f"\n📈 Trade Statistics:")
        print(f"   Total Trades:        {len(df_trades):>10}")
        print(f"   Winning Trades:      {len(winning_trades):>10}")
        print(f"   Losing Trades:       {len(losing_trades):>10}")
        print(f"   Win Rate:            {win_rate:>10.2f}%")
        
        print(f"\n💰 P&L Analysis:")
        print(f"   Avg Win:             ${avg_win:>10.2f}")
        print(f"   Avg Loss:            ${avg_loss:>10.2f}")
        print(f"   Avg Trade:           ${df_trades['pnl'].mean():>10.2f}")
        print(f"   Best Trade:          ${df_trades['pnl'].max():>10.2f}")
        print(f"   Worst Trade:         ${df_trades['pnl'].min():>10.2f}")
        
        print(f"\n📅 Time Period:")
        print(f"   Start Date:          {start_date}")
        print(f"   End Date:            {end_date}")
        print(f"   Total Days:          {total_days}")
        
        print(f"\n{'='*60}\n")

def main():
    """Run backtest"""
    bot = ETHVolBreakoutBot(backtest_mode=True)
    
    # Path to historical data
    data_path = Path("data/processed/binance_ETHUSDT_1h_combined.parquet")
    
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        print("Please run the data downloader first.")
        return
    
    # Run backtest
    trades, equity = bot.backtest(data_path)
    
    print("\n✅ Backtest complete!")
    print("\n⚠️  IMPORTANT: This is a backtest only.")
    print("    Paper trade for 2 weeks before going live.")
    print("    Past performance does not guarantee future results.")

if __name__ == "__main__":
    main()
