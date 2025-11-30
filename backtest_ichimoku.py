#!/usr/bin/env python3
"""
ICHIMOKU CLOUD FAST SETTINGS STRATEGY
Optimized for intraday scalping with fast settings (6,13,26)

Research shows this works well on 5m-15m timeframes for crypto
"""

import pandas as pd
import numpy as np
from pathlib import Path

class IchimokuCloudFast:
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = 10000
        self.fee_rate = 0.0001
        
        # Ichimoku Fast Settings (optimized for scalping)
        self.tenkan_period = 6   # Conversion Line (vs 9 default)
        self.kijun_period = 13   # Base Line (vs 26 default)
        self.senkou_b_period = 26  # Leading Span B (vs 52 default)
        self.displacement = 26   # Cloud displacement
        
        # Risk Management
        self.stop_loss_pct = 0.012  # 1.2%
        self.take_profit_pct = 0.025  # 2.5%
        
    def calculate_indicators(self, df):
        """Calculate Ichimoku Cloud indicators"""
        df = df.copy()
        
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        high_tenkan = df['high'].rolling(window=self.tenkan_period).max()
        low_tenkan = df['low'].rolling(window=self.tenkan_period).min()
        df['Tenkan'] = (high_tenkan + low_tenkan) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low)/2
        high_kijun = df['high'].rolling(window=self.kijun_period).max()
        low_kijun = df['low'].rolling(window=self.kijun_period).min()
        df['Kijun'] = (high_kijun + low_kijun) / 2
        
        # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
        df['Senkou_A'] = ((df['Tenkan'] + df['Kijun']) / 2).shift(self.displacement)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
        high_senkou = df['high'].rolling(window=self.senkou_b_period).max()
        low_senkou = df['low'].rolling(window=self.senkou_b_period).min()
        df['Senkou_B'] = ((high_senkou + low_senkou) / 2).shift(self.displacement)
        
        # Chikou Span (Lagging Span): Current closing price shifted back 26 periods
        df['Chikou'] = df['close'].shift(-self.displacement)
        
        # Cloud boundaries
        df['Cloud_Top'] = df[['Senkou_A', 'Senkou_B']].max(axis=1)
        df['Cloud_Bottom'] = df[['Senkou_A', 'Senkou_B']].min(axis=1)
        
        # Additional: Price position relative to cloud
        df['Above_Cloud'] = df['close'] > df['Cloud_Top']
        df['Below_Cloud'] = df['close'] < df['Cloud_Bottom']
        df['In_Cloud'] = ~df['Above_Cloud'] & ~df['Below_Cloud']
        
        return df
    
    def get_signal(self, df, i):
        """
        Ichimoku Cloud Entry Signals:
        
        LONG:
        - Price breaks above cloud
        - Tenkan crosses above Kijun
        - Both above cloud
        
        SHORT:
        - Price breaks below cloud
        - Tenkan crosses below Kijun
        - Both below cloud
        """
        if i < 2:
            return 'hold'
        
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Bullish Signal
        if (not prev['Above_Cloud'] and current['Above_Cloud'] and  # Price breaks above cloud
            current['Tenkan'] > current['Kijun'] and  # Tenkan above Kijun
            prev['Tenkan'] <= prev['Kijun']):  # Tenkan just crossed above
            return 'buy'
        
        # Bearish Signal
        elif (not prev['Below_Cloud'] and current['Below_Cloud'] and  # Price breaks below cloud
              current['Tenkan'] < current['Kijun'] and  # Tenkan below Kijun
              prev['Tenkan'] >= prev['Kijun']):  # Tenkan just crossed below
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
        
        # Ichimoku Exit Signals
        if position > 0:
            # Long: exit if price re-enters cloud OR Tenkan crosses below Kijun
            if current['In_Cloud'] or current['Below_Cloud']:
                return True, 'Cloud_Reentry'
            if current['Tenkan'] < current['Kijun']:
                return True, 'TK_Cross'
        
        elif position < 0:
            # Short: exit if price re-enters cloud OR Tenkan crosses above Kijun
            if current['In_Cloud'] or current['Above_Cloud']:
                return True, 'Cloud_Reentry'
            if current['Tenkan'] > current['Kijun']:
                return True, 'TK_Cross'
        
        return False, None
    
    def backtest(self, data_path):
        """Run backtest"""
        print(f"\n{'='*70}")
        print(f"ICHIMOKU CLOUD FAST - {self.symbol} {self.timeframe}")
        print(f"Settings: ({self.tenkan_period},{self.kijun_period},{self.senkou_b_period})")
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
        
        # Start after displacement period
        start_idx = max(self.senkou_b_period, self.displacement) + 10
        
        # Run backtest
        for i in range(start_idx, len(df) - self.displacement):
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
                        'size': position_size
                    })
                    
                elif signal == 'sell':
                    position_size = capital / current_price
                    position = -position_size
                    entry_price = current_price
                    trades.append({
                        'time': current_time,
                        'type': 'sell',
                        'price': current_price,
                        'size': position_size
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
        ('BTCUSDT', '15m'),
        ('ETHUSDT', '15m'),
        ('BTCUSDT', '1h'),
        ('ETHUSDT', '1h'),
    ]
    
    for symbol, timeframe in assets:
        data_path = Path(f"data/processed/binance_{symbol}_{timeframe}_combined.parquet")
        
        if not data_path.exists():
            print(f"⏭️  Skipping {symbol} {timeframe} - data not found")
            continue
        
        bot = IchimokuCloudFast(symbol, timeframe)
        trades, equity = bot.backtest(data_path)
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
