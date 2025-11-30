#!/usr/bin/env python3
"""
VALIDATE ALL 1D BOTS - COMPREHENSIVE 2-YEAR ANALYSIS
- ETH 1d, NVDA 1d, SPY 1d, TSLA 1d (from IBKR)
- BTC Combo Momentum (from Binance)
- TSLA 4h Fib (from IBKR)

Provides: Daily, Monthly, and Annual returns analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ib_insync import *
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time
import requests
from calendar import monthrange

class ComprehensiveValidator:
    def __init__(self, port=7496):
        self.ib = IB()
        self.port = port
        self.fee_rate = 0.0001  # 0.01% limit orders
        self.initial_capital = 10000
        self.data_dir = Path('data/raw/ibkr/')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
    
    # =================================================================
    # DATA DOWNLOAD
    # =================================================================
    
    def connect_ibkr(self):
        """Connect to IBKR"""
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=3)
            print(f"✅ Connected to IBKR on port {self.port}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect_ibkr(self):
        """Disconnect from IBKR"""
        if self.ib.isConnected():
            self.ib.disconnect()
    
    def download_stock_1d(self, symbol):
        """Download 1d bars from IBKR"""
        print(f"\n📊 Downloading {symbol} 1d bars for 2 years...")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='2 Y',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if not bars:
                print(f"❌ No data for {symbol}")
                return None
            
            df = util.df(bars)
            df = df.rename(columns={
                'date': 'Time',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            df = df[['Time', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Save
            output_file = self.data_dir / f'{symbol}_1d.parquet'
            df.to_parquet(output_file, index=False)
            
            print(f"✅ {len(df)} bars ({df['Time'].min()} to {df['Time'].max()})")
            return df
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def download_stock_4h(self, symbol):
        """Download 4h bars from IBKR"""
        print(f"\n📊 Downloading {symbol} 4h bars for 2 years...")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='2 Y',
                barSizeSetting='4 hours',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if not bars:
                print(f"❌ No data for {symbol}")
                return None
            
            df = util.df(bars)
            df = df.rename(columns={
                'date': 'Time',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            df = df[['Time', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Save
            output_file = self.data_dir / f'{symbol}_4h.parquet'
            df.to_parquet(output_file, index=False)
            
            print(f"✅ {len(df)} bars ({df['Time'].min()} to {df['Time'].max()})")
            return df
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def download_btc_1d_binance(self):
        """Download BTC 1d from Binance"""
        print(f"\n📊 Downloading BTC 1d from Binance for 2 years...")
        
        try:
            # Use existing 5m data and resample to 1d
            btc_5m_path = Path('data/raw/binance_BTCUSDT_5m/')
            
            if not btc_5m_path.exists():
                print(f"❌ No BTC 5m data found")
                return None
            
            # Load all 5m files
            all_files = sorted(btc_5m_path.glob('*.parquet'))
            dfs = []
            
            for file in all_files:
                try:
                    df_chunk = pd.read_parquet(file)
                    dfs.append(df_chunk)
                except:
                    continue
            
            if not dfs:
                return None
            
            df = pd.concat(dfs, ignore_index=True)
            df['Time'] = pd.to_datetime(df['Time'])
            df = df.sort_values('Time').reset_index(drop=True)
            df = df[['Time', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            
            # Resample to 1d
            df = df.set_index('Time')
            df_1d = df.resample('1D').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            df_1d = df_1d.reset_index()
            
            # Take last 2 years
            cutoff = df_1d['Time'].max() - timedelta(days=730)
            df_1d = df_1d[df_1d['Time'] >= cutoff]
            
            print(f"✅ {len(df_1d)} bars ({df_1d['Time'].min()} to {df_1d['Time'].max()})")
            return df_1d
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    # =================================================================
    # STRATEGY TESTS
    # =================================================================
    
    def test_volatility_breakout_1d(self, df, symbol):
        """Generic Volatility Breakout for 1d"""
        print(f"\n{'='*80}")
        print(f"Testing: {symbol} 1d Volatility Breakout")
        print(f"{'='*80}")
        
        df = df.copy()
        
        # Volatility breakout indicators
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        df['Price_MA'] = df['Close'].rolling(20).mean()
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        
        for i in range(30, len(df)):
            current_price = df.iloc[i]['Close']
            
            if position == 0:
                # Entry: Price breaks above MA + High volume + High ATR
                if (current_price > df.iloc[i]['Price_MA'] * 1.02 and
                    df.iloc[i]['Volume'] > df.iloc[i]['Volume_MA'] * 1.5 and
                    df.iloc[i]['ATR'] > df.iloc[i-20:i]['ATR'].mean() * 1.2):
                    
                    position_size = capital / current_price
                    fee = position_size * current_price * self.fee_rate
                    capital -= fee
                    total_fees += fee
                    
                    position = position_size
                    entry_price = current_price
                    
            else:
                pnl_pct = (current_price - entry_price) / entry_price
                
                exit_signal = False
                
                # TP: 5% (daily bars need larger targets)
                if pnl_pct >= 0.05:
                    exit_signal = True
                # SL: -2%
                elif pnl_pct <= -0.02:
                    exit_signal = True
                # Price falls below MA
                elif current_price < df.iloc[i]['Price_MA']:
                    exit_signal = True
                
                if exit_signal:
                    pnl = position * (current_price - entry_price)
                    fee = position * current_price * self.fee_rate
                    capital += pnl - fee
                    total_fees += fee
                    
                    trades.append({
                        'date': df.iloc[i]['Time'],
                        'pnl': pnl - fee,
                        'pnl_pct': pnl_pct
                    })
                    
                    position = 0
        
        return self._calculate_comprehensive_metrics(f'{symbol} 1d Volatility', capital, trades, df, total_fees)
    
    def test_btc_combo_momentum_1d(self, df):
        """BTC Combo Momentum on 1d"""
        print(f"\n{'='*80}")
        print(f"Testing: BTC Combo Momentum 1d")
        print(f"{'='*80}")
        
        df = df.copy()
        
        # Momentum + Volume
        df['Momentum'] = df['Close'].pct_change(5) * 100
        df['EMA_Fast'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_Slow'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        
        for i in range(30, len(df)):
            current_price = df.iloc[i]['Close']
            
            if position == 0:
                # Entry: Strong momentum + EMA cross + Volume
                if (df.iloc[i]['Momentum'] > 2.0 and
                    df.iloc[i]['EMA_Fast'] > df.iloc[i]['EMA_Slow'] and
                    df.iloc[i]['Volume'] > df.iloc[i]['Volume_MA'] * 1.3):
                    
                    position_size = capital / current_price
                    fee = position_size * current_price * self.fee_rate
                    capital -= fee
                    total_fees += fee
                    
                    position = position_size
                    entry_price = current_price
                    
            else:
                pnl_pct = (current_price - entry_price) / entry_price
                
                exit_signal = False
                
                if pnl_pct >= 0.08:  # 8% TP
                    exit_signal = True
                elif pnl_pct <= -0.03:  # 3% SL
                    exit_signal = True
                elif df.iloc[i]['EMA_Fast'] < df.iloc[i]['EMA_Slow']:
                    exit_signal = True
                
                if exit_signal:
                    pnl = position * (current_price - entry_price)
                    fee = position * current_price * self.fee_rate
                    capital += pnl - fee
                    total_fees += fee
                    
                    trades.append({
                        'date': df.iloc[i]['Time'],
                        'pnl': pnl - fee,
                        'pnl_pct': pnl_pct
                    })
                    
                    position = 0
        
        return self._calculate_comprehensive_metrics('BTC Combo Momentum 1d', capital, trades, df, total_fees)
    
    def test_tsla_fib_4h(self, df):
        """TSLA Fibonacci 4h"""
        print(f"\n{'='*80}")
        print(f"Testing: TSLA Fibonacci 4h")
        print(f"{'='*80}")
        
        df = df.copy()
        
        # Fibonacci retracement levels
        lookback = 20
        df['High_20'] = df['High'].rolling(lookback).max()
        df['Low_20'] = df['Low'].rolling(lookback).min()
        df['Range'] = df['High_20'] - df['Low_20']
        df['Fib_382'] = df['Low_20'] + (df['Range'] * 0.382)
        df['Fib_618'] = df['Low_20'] + (df['Range'] * 0.618)
        
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        total_fees = 0
        
        for i in range(30, len(df)):
            current_price = df.iloc[i]['Close']
            
            if position == 0:
                # Entry: Price near Fib 382 or 618 (support)
                fib_382 = df.iloc[i]['Fib_382']
                fib_618 = df.iloc[i]['Fib_618']
                
                if (abs(current_price - fib_382) / fib_382 < 0.01 or
                    abs(current_price - fib_618) / fib_618 < 0.01):
                    
                    position_size = capital / current_price
                    fee = position_size * current_price * self.fee_rate
                    capital -= fee
                    total_fees += fee
                    
                    position = position_size
                    entry_price = current_price
                    
            else:
                pnl_pct = (current_price - entry_price) / entry_price
                
                exit_signal = False
                
                if pnl_pct >= 0.03:  # 3% TP
                    exit_signal = True
                elif pnl_pct <= -0.015:  # 1.5% SL
                    exit_signal = True
                
                if exit_signal:
                    pnl = position * (current_price - entry_price)
                    fee = position * current_price * self.fee_rate
                    capital += pnl - fee
                    total_fees += fee
                    
                    trades.append({
                        'date': df.iloc[i]['Time'],
                        'pnl': pnl - fee,
                        'pnl_pct': pnl_pct
                    })
                    
                    position = 0
        
        return self._calculate_comprehensive_metrics('TSLA Fib 4h', capital, trades, df, total_fees)
    
    # =================================================================
    # COMPREHENSIVE METRICS
    # =================================================================
    
    def _calculate_comprehensive_metrics(self, name, final_capital, trades, df, total_fees):
        """Calculate daily, monthly, and annual metrics"""
        if not trades:
            print(f"❌ NO TRADES for {name}")
            return None
        
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(trades)
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # Basic metrics
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        win_rate = len(winning_trades) / len(trades) * 100 if len(trades) > 0 else 0
        
        # Time metrics
        start_date = pd.to_datetime(df['Time']).min()
        end_date = pd.to_datetime(df['Time']).max()
        total_days = (end_date - start_date).days
        
        # Daily returns
        daily_return = total_return / total_days if total_days > 0 else 0
        
        # Monthly returns
        trades_df['year_month'] = trades_df['date'].dt.to_period('M')
        monthly_pnl = trades_df.groupby('year_month')['pnl'].sum()
        
        # Calculate monthly return percentages
        monthly_returns = []
        capital_tracker = self.initial_capital
        
        for month, pnl in monthly_pnl.items():
            monthly_return_pct = (pnl / capital_tracker) * 100
            monthly_returns.append({
                'month': str(month),
                'pnl': pnl,
                'return_pct': monthly_return_pct
            })
            capital_tracker += pnl
        
        avg_monthly_return = np.mean([m['return_pct'] for m in monthly_returns]) if monthly_returns else 0
        
        # Annual return
        years = total_days / 365
        annual_return = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        result = {
            'Strategy': name,
            'Total_Return': total_return,
            'Daily_Return': daily_return,
            'Monthly_Return_Avg': avg_monthly_return,
            'Annual_Return': annual_return,
            'Win_Rate': win_rate,
            'Total_Trades': len(trades),
            'Winning_Trades': len(winning_trades),
            'Losing_Trades': len(losing_trades),
            'Avg_Trade_Return': trades_df['pnl_pct'].mean() * 100,
            'Days_Tested': total_days,
            'Months_Tested': len(monthly_returns),
            'Total_Fees': total_fees,
            'Monthly_Details': monthly_returns
        }
        
        print(f"\n📊 COMPREHENSIVE RESULTS:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Daily Return: {daily_return:.3f}%")
        print(f"   Monthly Return (avg): {avg_monthly_return:.2f}%")
        print(f"   Annual Return: {annual_return:.1f}%")
        print(f"   Win Rate: {win_rate:.1f}% ({len(winning_trades)}W / {len(losing_trades)}L)")
        print(f"   Trades: {len(trades)} over {total_days} days ({len(monthly_returns)} months)")
        print(f"   Avg Trade: {trades_df['pnl_pct'].mean()*100:.2f}%")
        
        return result
    
    # =================================================================
    # MAIN VALIDATION
    # =================================================================
    
    def run_validation(self):
        """Run comprehensive validation"""
        print("="*80)
        print("🔍 VALIDATING ALL 1D/4H BOTS - COMPREHENSIVE 2-YEAR ANALYSIS")
        print("="*80)
        
        if not self.connect_ibkr():
            print("\n❌ Cannot connect to IBKR")
            return
        
        try:
            # Download all data
            print("\n📥 DOWNLOADING DATA FROM IBKR...")
            
            df_eth_1d = self.download_stock_1d('ETH')
            time.sleep(11)
            
            df_nvda_1d = self.download_stock_1d('NVDA')
            time.sleep(11)
            
            df_spy_1d = self.download_stock_1d('SPY')
            time.sleep(11)
            
            df_tsla_1d = self.download_stock_1d('TSLA')
            time.sleep(11)
            
            df_tsla_4h = self.download_stock_4h('TSLA')
            
            # Disconnect IBKR
            self.disconnect_ibkr()
            
            # Download BTC from Binance (resample from 5m)
            print("\n📥 PROCESSING BTC DATA FROM BINANCE...")
            df_btc_1d = self.download_btc_1d_binance()
            
            # Run tests
            print("\n\n" + "="*80)
            print("🧪 RUNNING STRATEGY TESTS")
            print("="*80)
            
            if df_eth_1d is not None:
                r1 = self.test_volatility_breakout_1d(df_eth_1d, 'ETH')
                if r1: self.results.append(r1)
            
            if df_nvda_1d is not None:
                r2 = self.test_volatility_breakout_1d(df_nvda_1d, 'NVDA')
                if r2: self.results.append(r2)
            
            if df_spy_1d is not None:
                r3 = self.test_volatility_breakout_1d(df_spy_1d, 'SPY')
                if r3: self.results.append(r3)
            
            if df_tsla_1d is not None:
                r4 = self.test_volatility_breakout_1d(df_tsla_1d, 'TSLA')
                if r4: self.results.append(r4)
            
            if df_btc_1d is not None:
                r5 = self.test_btc_combo_momentum_1d(df_btc_1d)
                if r5: self.results.append(r5)
            
            if df_tsla_4h is not None:
                r6 = self.test_tsla_fib_4h(df_tsla_4h)
                if r6: self.results.append(r6)
            
            # Print final report
            self._print_comprehensive_report()
            
        finally:
            self.disconnect_ibkr()
    
    def _print_comprehensive_report(self):
        """Print comprehensive final report"""
        print("\n\n" + "="*80)
        print("📊 COMPREHENSIVE RETURNS ANALYSIS - ALL 1D/4H BOTS")
        print("="*80)
        
        if not self.results:
            print("❌ NO RESULTS")
            return
        
        df = pd.DataFrame(self.results)
        df = df.sort_values('Annual_Return', ascending=False)
        
        print(f"\n{'Strategy':<30} {'Daily%':<10} {'Monthly%':<12} {'Annual%':<12} {'Win%':<8} {'Trades':<10} {'Status'}")
        print("-"*80)
        
        for _, row in df.iterrows():
            if row['Annual_Return'] >= 15:
                status = "✅ KEEP"
            elif row['Annual_Return'] > 0:
                status = "⚠️ MARGINAL"
            else:
                status = "❌ REMOVE"
            
            print(f"{row['Strategy']:<30} {row['Daily_Return']:>8.3f}% {row['Monthly_Return_Avg']:>10.2f}% {row['Annual_Return']:>10.1f}% {row['Win_Rate']:>6.1f}% {row['Total_Trades']:>8} {status}")
        
        # Monthly details for top performers
        print("\n" + "="*80)
        print("📅 MONTHLY BREAKDOWN (Top 3 Performers)")
        print("="*80)
        
        top_3 = df.head(3)
        for idx, row in top_3.iterrows():
            print(f"\n{row['Strategy']}:")
            print(f"{'Month':<15} {'PnL':<15} {'Return %'}")
            print("-"*50)
            
            for month_data in row['Monthly_Details'][-12:]:  # Last 12 months
                print(f"{month_data['month']:<15} ${month_data['pnl']:>12.2f} {month_data['return_pct']:>10.2f}%")
        
        # Summary
        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS:")
        print("="*80)
        
        keep = df[df['Annual_Return'] >= 15]
        if len(keep) > 0:
            print(f"\n✅ KEEP THESE ({len(keep)} bots >= 15% annual):")
            for _, row in keep.iterrows():
                print(f"   {row['Strategy']:<30} {row['Daily_Return']:.3f}%/day, {row['Annual_Return']:.0f}% annual")
        
        remove = df[df['Annual_Return'] < 15]
        if len(remove) > 0:
            print(f"\n❌ REMOVE THESE ({len(remove)} bots < 15% annual):")
            for _, row in remove.iterrows():
                print(f"   {row['Strategy']:<30} {row['Daily_Return']:.3f}%/day, {row['Annual_Return']:.0f}% annual")

def main():
    validator = ComprehensiveValidator(port=7496)
    validator.run_validation()

if __name__ == "__main__":
    main()

