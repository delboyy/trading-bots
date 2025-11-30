#!/usr/bin/env python3
"""
MFI + CCI COMBO STRATEGY
Research shows MFI and CCI outperform RSI/MACD

Strategy:
- MFI (Money Flow Index): Volume-weighted RSI
- CCI (Commodity Channel Index): Statistical deviation
- Entry: MFI < 20 + CCI < -100 (oversold) OR MFI > 80 + CCI > 100 (overbought)
- Exit: Mean reversion OR TP/SL
"""

import pandas as pd
import numpy as np
from pathlib import Path

class MFICCICombo:
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = 10000
        self.fee_rate = 0.0001
        
        # MFI Parameters
        self.mfi_period = 14
        self.mfi_oversold = 20
        self.mfi_overbought = 80
        
        # CCI Parameters
        self.cci_period = 20
        self.cci_oversold = -100
        self.cci_overbought = 100
        
        # Trend Filter
        self.sma_period = 50
        self.use_trend_filter = True
        
        # Risk Management
        self.stop_loss_pct = 0.015  # 1.5%
        self.take_profit_pct = 0.03  # 3%
        
    def calculate_mfi(self, df):
        """Calculate Money Flow Index"""
        # Typical Price
        df['TP'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Money Flow
        df['MF'] = df['TP'] * df['volume']
        
        # Positive and Negative Money Flow
        df['MF_Positive'] = 0.0
        df['MF_Negative'] = 0.0
        
        for i in range(1, len(df)):
            if df.iloc[i]['TP'] > df.iloc[i-1]['TP']:
                df.iloc[i, df.columns.get_loc('MF_Positive')] = df.iloc[i]['MF']
            elif df.iloc[i]['TP'] < df.iloc[i-1]['TP']:
                df.iloc[i, df.columns.get_loc('MF_Negative')] = df.iloc[i]['MF']
        
        # Money Flow Ratio
        positive_mf = df['MF_Positive'].rolling(self.mfi_period).sum()
        negative_mf = df['MF_Negative'].rolling(self.mfi_period).sum()
        
        mf_ratio = positive_mf / negative_mf
        
        # MFI
        df['MFI'] = 100 - (100 / (1 + mf_ratio))
        
        return df
    
    def calculate_cci(self, df):
        """Calculate Commodity Channel Index"""
        # Typical Price
        df['TP'] = (df['high'] + df['low'] + df['close']) / 3
        
        # SMA of Typical Price
        df['TP_SMA'] = df['TP'].rolling(self.cci_period).mean()
        
        # Mean Deviation
        df['MD'] = df['TP'].rolling(self.cci_period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        
        # CCI
        df['CCI'] = (df['TP'] - df['TP_SMA']) / (0.015 * df['MD'])
        
        return df
    
    def calculate_indicators(self, df):
        """Calculate all indicators"""
        df = df.copy()
        
        # MFI
        df = self.calculate_mfi(df)
        
        # CCI
        df = self.calculate_cci(df)
        
        # Trend Filter (SMA)
        df['SMA'] = df['close'].rolling(self.sma_period).mean()
        
        return df
    
    def get_signal(self, df, i):
        """Determine trading signal"""
        if i < max(self.mfi_period, self.cci_period, self.sma_period) + 5:
            return 'hold'
        
        current = df.iloc[i]
        
        # Trend filter
        if self.use_trend_filter:
            trend_up = current['close'] > current['SMA']
            trend_down = current['close'] < current['SMA']
        else:
            trend_up = True
            trend_down = True
        
        # Oversold (Buy Signal)
        if (current['MFI'] < self.mfi_oversold and 
            current['CCI'] < self.cci_oversold and 
            trend_up):
            return 'buy'
        
        # Overbought (Sell Signal)
        elif (current['MFI'] > self.mfi_overbought and 
              current['CCI'] > self.cci_overbought and 
              trend_down):
            return 'sell'
        
        return 'hold'
    
    def check_exit(self, df, i, position, entry_price):
        """Check exit conditions"""
        if position == 0:
            return False, None
        
        current = df.iloc[i]
        current_price = current['close']
        
        pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
        
        # Stop Loss
        if pnl_pct < -self.stop_loss_pct:
            return True, 'SL'
        
        # Take Profit
        if pnl_pct > self.take_profit_pct:
            return True, 'TP'
        
        # Mean Reversion Exit
        if position > 0:
            # Exit long when MFI > 50 OR CCI > 0
            if current['MFI'] > 50 or current['CCI'] > 0:
                return True, 'Mean_Revert'
        elif position < 0:
            # Exit short when MFI < 50 OR CCI < 0
            if current['MFI'] < 50 or current['CCI'] < 0:
                return True, 'Mean_Revert'
        
        return False, None
    
    def backtest(self, data_path):
        """Run backtest"""
        print(f"\n{'='*70}")
        print(f"MFI + CCI COMBO - {self.symbol} {self.timeframe}")
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
        start_idx = max(self.mfi_period, self.cci_period, self.sma_period) + 10
        
        for i in range(start_idx, len(df)):
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
                        'mfi': df.iloc[i]['MFI'],
                        'cci': df.iloc[i]['CCI']
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
                        'mfi': df.iloc[i]['MFI'],
                        'cci': df.iloc[i]['CCI']
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
        
        bot = MFICCICombo(symbol, timeframe)
        trades, equity = bot.backtest(data_path)
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
