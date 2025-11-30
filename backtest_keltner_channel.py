#!/usr/bin/env python3
"""
KELTNER CHANNEL ATR BREAKOUT STRATEGY
Research shows 77% win rate on S&P 500, 126% return on crypto

Strategy:
- Uses Keltner Channels (EMA + ATR bands) for breakout detection
- Enters on breakouts with volume confirmation
- Exits on channel re-entry or profit targets
- Adapts to volatility automatically via ATR
"""

import pandas as pd
import numpy as np
from pathlib import Path

class KeltnerChannelBreakout:
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = 10000
        self.fee_rate = 0.0001
        
        # Keltner Channel Parameters (optimized from research)
        self.ema_period = 20
        self.atr_period = 14
        self.atr_multiplier = 1.5  # 1.3-2.0 range, 1.5 is balanced
        
        # Risk Management
        self.stop_loss_pct = 0.015  # 1.5%
        self.take_profit_pct = 0.03  # 3% (2:1 reward:risk)
        
        # Volume Filter
        self.volume_multiplier = 1.2
        
    def calculate_indicators(self, df):
        """Calculate Keltner Channels and supporting indicators"""
        df = df.copy()
        
        # EMA (centerline)
        df['EMA'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # ATR (volatility measure)
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].ewm(span=self.atr_period, adjust=False).mean()
        
        # Keltner Channels
        df['Upper_KC'] = df['EMA'] + (self.atr_multiplier * df['ATR'])
        df['Lower_KC'] = df['EMA'] - (self.atr_multiplier * df['ATR'])
        
        # Volume Filter
        df['Vol_MA'] = df['volume'].rolling(20).mean()
        
        # Additional: Price position relative to channel
        df['Channel_Width'] = df['Upper_KC'] - df['Lower_KC']
        df['Price_Position'] = (df['close'] - df['Lower_KC']) / df['Channel_Width']
        
        return df
    
    def get_signal(self, df, i):
        """
        Determine trading signal
        
        Breakout Logic:
        - LONG: Price breaks above upper channel + volume confirmation
        - SHORT: Price breaks below lower channel + volume confirmation
        - EXIT: Price re-enters channel
        """
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Volume confirmation
        volume_ok = current['volume'] > current['Vol_MA'] * self.volume_multiplier
        
        # Bullish Breakout
        if (prev['close'] <= prev['Upper_KC'] and 
            current['close'] > current['Upper_KC'] and 
            volume_ok):
            return 'buy'
        
        # Bearish Breakout
        elif (prev['close'] >= prev['Lower_KC'] and 
              current['close'] < current['Lower_KC'] and 
              volume_ok):
            return 'sell'
        
        return 'hold'
    
    def check_exit(self, df, i, position, entry_price):
        """Check exit conditions"""
        current = df.iloc[i]
        
        if position == 0:
            return False
        
        current_price = current['close']
        pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
        
        # Stop Loss
        if pnl_pct < -self.stop_loss_pct:
            return True, 'SL'
        
        # Take Profit
        if pnl_pct > self.take_profit_pct:
            return True, 'TP'
        
        # Channel Re-entry (trend reversal)
        if position > 0:
            # Long: exit if price re-enters channel (crosses below upper band)
            if current_price < current['Upper_KC']:
                return True, 'Channel_Reentry'
        elif position < 0:
            # Short: exit if price re-enters channel (crosses above lower band)
            if current_price > current['Lower_KC']:
                return True, 'Channel_Reentry'
        
        return False, None
    
    def backtest(self, data_path):
        """Run backtest"""
        print(f"\n{'='*70}")
        print(f"KELTNER CHANNEL ATR BREAKOUT - {self.symbol} {self.timeframe}")
        print(f"{'='*70}\n")
        
        # Load data
        df = pd.read_parquet(data_path)
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"Loaded {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Backtest variables
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [capital]
        
        # Run backtest
        for i in range(self.ema_period + self.atr_period, len(df)):
            current_price = df.iloc[i]['close']
            current_time = df.iloc[i]['timestamp']
            
            # Check exit first
            if position != 0:
                should_exit, reason = self.check_exit(df, i, position, entry_price)
                
                if should_exit:
                    # Calculate PnL
                    size = abs(position)
                    if position > 0:
                        pnl = size * (current_price - entry_price)
                    else:
                        pnl = size * (entry_price - current_price)
                    
                    # Fees
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
                    trades[-1]['reason'] = reason
                    
                    position = 0
                    entry_price = 0
            
            # Check entry
            if position == 0:
                signal = self.get_signal(df, i)
                
                if signal == 'buy':
                    position_size = capital / current_price
                    position = position_size
                    entry_price = current_price
                    trades.append({
                        'time': current_time,
                        'type': 'buy',
                        'price': current_price,
                        'size': position_size,
                        'upper_kc': df.iloc[i]['Upper_KC'],
                        'lower_kc': df.iloc[i]['Lower_KC']
                    })
                    
                elif signal == 'sell':
                    position_size = capital / current_price
                    position = -position_size
                    entry_price = current_price
                    trades.append({
                        'time': current_time,
                        'type': 'sell',
                        'price': current_price,
                        'size': position_size,
                        'upper_kc': df.iloc[i]['Upper_KC'],
                        'lower_kc': df.iloc[i]['Lower_KC']
                    })
            
            equity_curve.append(capital)
        
        # Print results
        self._print_results(trades, equity_curve, df)
        
        return trades, equity_curve
    
    def _print_results(self, trades, equity_curve, df):
        """Print backtest results"""
        if not trades:
            print("❌ No trades executed")
            return
        
        completed_trades = [t for t in trades if 'exit_time' in t]
        
        if not completed_trades:
            print("❌ No completed trades")
            return
        
        df_trades = pd.DataFrame(completed_trades)
        
        # Calculate metrics
        total_return = (equity_curve[-1] - self.initial_capital) / self.initial_capital * 100
        winning_trades = df_trades[df_trades['pnl'] > 0]
        losing_trades = df_trades[df_trades['pnl'] <= 0]
        win_rate = len(winning_trades) / len(df_trades) * 100
        
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else 0
        
        # Time metrics
        start_date = df['timestamp'].min()
        end_date = df['timestamp'].max()
        total_days = (end_date - start_date).days
        daily_return = total_return / total_days if total_days > 0 else 0
        
        # Exit reason breakdown
        exit_reasons = df_trades['reason'].value_counts()
        
        # Print results
        print(f"\n{'='*70}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*70}\n")
        
        print(f"📊 Performance:")
        print(f"   Total Return:        {total_return:>10.2f}%")
        print(f"   Daily Return (avg):  {daily_return:>10.3f}%")
        print(f"   Annual Return (est): {daily_return * 365:>10.2f}%")
        print(f"   Final Capital:       ${equity_curve[-1]:>10.2f}")
        print(f"   Profit Factor:       {profit_factor:>10.2f}")
        
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
        
        print(f"\n🚪 Exit Reasons:")
        for reason, count in exit_reasons.items():
            pct = count / len(df_trades) * 100
            print(f"   {reason:<20} {count:>5} ({pct:>5.1f}%)")
        
        print(f"\n📅 Time Period:")
        print(f"   Start Date:          {start_date}")
        print(f"   End Date:            {end_date}")
        print(f"   Total Days:          {total_days}")
        
        print(f"\n{'='*70}\n")

def main():
    """Test on multiple assets"""
    assets = [
        ('BTCUSDT', '1h'),
        ('ETHUSDT', '1h'),
        ('BTCUSDT', '15m'),
        ('ETHUSDT', '15m'),
    ]
    
    for symbol, timeframe in assets:
        data_path = Path(f"data/processed/binance_{symbol}_{timeframe}_combined.parquet")
        
        if not data_path.exists():
            print(f"⏭️  Skipping {symbol} {timeframe} - data not found")
            continue
        
        bot = KeltnerChannelBreakout(symbol, timeframe)
        trades, equity = bot.backtest(data_path)
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
