
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

class ZScoreBacktester:
    def __init__(self, data_path, symbol, timeframe):
        self.data_path = Path(data_path)
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = 10000
        self.fee_rate = 0.0001  # 0.01%
        
    def load_data(self):
        if not self.data_path.exists():
            print(f"Data file not found: {self.data_path}")
            return None
        
        df = pd.read_parquet(self.data_path)
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df
    
    def calculate_indicators(self, df):
        df = df.copy()
        
        # Z-Score Parameters
        window = 20
        df['SMA'] = df['close'].rolling(window).mean()
        df['StdDev'] = df['close'].rolling(window).std()
        df['ZScore'] = (df['close'] - df['SMA']) / df['StdDev']
        
        # ATR for Volatility Filter
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(14).mean()
        df['ATR_MA'] = df['ATR'].rolling(50).mean()
        
        # Volume Filter
        df['Vol_MA'] = df['volume'].rolling(20).mean()
        
        return df
    
    def run_backtest(self, df, params):
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [capital]
        
        z_entry = params.get('z_entry', 2.0)
        z_exit = params.get('z_exit', 0.0)
        use_trend = params.get('use_trend', False)
        use_vol_filter = params.get('use_vol_filter', False)
        use_breakout = params.get('use_breakout', False)
        use_vol_breakout = params.get('use_vol_breakout', False)
        tp_pct = params.get('tp_pct', None)
        sl_pct = params.get('sl_pct', 0.01)
        
        # Pre-calculate Trend Filter
        if use_trend:
            df['SMA_200'] = df['close'].rolling(200).mean()
            
        # Pre-calculate Recent High/Low for Vol Breakout
        if use_vol_breakout:
            df['Recent_High'] = df['high'].rolling(10).max().shift(1)
            df['Recent_Low'] = df['low'].rolling(10).min().shift(1)
            
        for i in range(200 if use_trend else 50, len(df)):
            current_price = df.iloc[i]['close']
            current_time = df.iloc[i]['timestamp']
            z_score = df.iloc[i]['ZScore']
            atr = df.iloc[i]['ATR']
            atr_ma = df.iloc[i]['ATR_MA']
            volume = df.iloc[i]['volume']
            vol_ma = df.iloc[i]['Vol_MA']
            sma = df.iloc[i]['SMA']
            
            # Filters
            trend_ok_long = True
            trend_ok_short = True
            if use_trend:
                trend_ok_long = current_price > df.iloc[i]['SMA_200']
                trend_ok_short = current_price < df.iloc[i]['SMA_200']
                
            is_low_vol = atr < atr_ma
            is_high_vol = atr > atr_ma
            
            # Entry Conditions
            if position == 0:
                # Volume Breakout (Doc Style)
                if use_vol_breakout:
                    recent_high = df.iloc[i]['Recent_High']
                    recent_low = df.iloc[i]['Recent_Low']
                    
                    # Bullish Breakout
                    if volume > vol_ma * 1.8 and current_price > recent_high * 1.005:
                        self._enter_trade(capital, current_price, current_time, 'buy', trades)
                        position = capital / current_price
                        entry_price = current_price
                        capital -= position * current_price * self.fee_rate
                        
                    # Bearish Breakout
                    elif volume > vol_ma * 1.8 and current_price < recent_low * 0.995:
                        self._enter_trade(capital, current_price, current_time, 'sell', trades)
                        position = -capital / current_price
                        entry_price = current_price
                        capital -= abs(position) * current_price * self.fee_rate

                # Mean Reversion (Low Vol)
                elif use_vol_filter and is_low_vol:
                    if z_score < -z_entry and trend_ok_long:
                        self._enter_trade(capital, current_price, current_time, 'buy', trades)
                        position = capital / current_price
                        entry_price = current_price
                        capital -= position * current_price * self.fee_rate
                        
                    elif z_score > z_entry and trend_ok_short:
                        self._enter_trade(capital, current_price, current_time, 'sell', trades)
                        position = -capital / current_price
                        entry_price = current_price
                        capital -= abs(position) * current_price * self.fee_rate
                
                # Breakout (High Vol)
                elif use_breakout and is_high_vol:
                    # Breakout Long: Price > Upper Band (Z > 2)
                    if z_score > 2.0 and trend_ok_long:
                        self._enter_trade(capital, current_price, current_time, 'buy', trades)
                        position = capital / current_price
                        entry_price = current_price
                        capital -= position * current_price * self.fee_rate
                        
                    # Breakout Short: Price < Lower Band (Z < -2)
                    elif z_score < -2.0 and trend_ok_short:
                        self._enter_trade(capital, current_price, current_time, 'sell', trades)
                        position = -capital / current_price
                        entry_price = current_price
                        capital -= abs(position) * current_price * self.fee_rate
                        
                # Baseline (No Vol Filter)
                elif not use_vol_filter and not use_breakout and not use_vol_breakout:
                     if z_score < -z_entry and trend_ok_long:
                        self._enter_trade(capital, current_price, current_time, 'buy', trades)
                        position = capital / current_price
                        entry_price = current_price
                        capital -= position * current_price * self.fee_rate
                        
                     elif z_score > z_entry and trend_ok_short:
                        self._enter_trade(capital, current_price, current_time, 'sell', trades)
                        position = -capital / current_price
                        entry_price = current_price
                        capital -= abs(position) * current_price * self.fee_rate
            
            # Exit Conditions
            elif position != 0:
                pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
                
                exit_signal = False
                reason = ""
                
                # Stop Loss
                if sl_pct and pnl_pct < -sl_pct:
                    exit_signal = True
                    reason = "SL"
                
                # Take Profit
                elif tp_pct and pnl_pct > tp_pct:
                    exit_signal = True
                    reason = "TP"
                
                # Strategy Exit
                if not exit_signal:
                    if use_breakout and is_high_vol:
                        # Breakout Exit: Cross SMA
                        if (position > 0 and current_price < sma) or (position < 0 and current_price > sma):
                            exit_signal = True
                            reason = "TrendRevert"
                    elif not use_vol_breakout:
                        # Mean Reversion Exit: Z-Score Cross 0
                        if (position > 0 and z_score > z_exit) or (position < 0 and z_score < -z_exit):
                            exit_signal = True
                            reason = "MeanRevert"
                
                if exit_signal:
                    # Calculate PnL and Fees
                    size = abs(position)
                    if position > 0:
                        pnl = size * (current_price - entry_price)
                    else:
                        pnl = size * (entry_price - current_price)
                        
                    entry_fee = size * entry_price * self.fee_rate
                    exit_fee = size * current_price * self.fee_rate
                    total_fee = entry_fee + exit_fee
                    
                    capital += pnl - total_fee
                    
                    self._record_exit(trades, current_price, current_time, pnl - total_fee, pnl_pct, reason)
                    position = 0
            
            equity_curve.append(capital)
            
        return trades, equity_curve

    def _enter_trade(self, capital, price, time, type, trades):
        trades.append({'type': type, 'price': price, 'time': time})

    def _record_exit(self, trades, price, time, net_pnl, pnl_pct, reason):
        trades[-1]['exit_price'] = price
        trades[-1]['exit_time'] = time
        trades[-1]['pnl'] = net_pnl
        trades[-1]['pnl_pct'] = pnl_pct
        trades[-1]['reason'] = reason

    def analyze_results(self, trades, equity_curve, name="Strategy"):
        if not trades:
            print(f"\n{name}: No trades executed.")
            return
        
        df_trades = pd.DataFrame(trades)
        total_return = (equity_curve[-1] - self.initial_capital) / self.initial_capital * 100
        win_rate = len(df_trades[df_trades['pnl'] > 0]) / len(df_trades) * 100
        
        print(f"\nResults for {name}:")
        print(f"Total Return: {total_return:.2f}%")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Total Trades: {len(trades)}")
        print(f"Avg PnL per Trade: {df_trades['pnl_pct'].mean() * 100:.2f}%")
        
        days = (df_trades['exit_time'].max() - df_trades['time'].min()).days
        if days > 0:
            daily_return = total_return / days
            print(f"Avg Daily Return: {daily_return:.2f}%")

    def combine_batches(self):
        raw_dir = Path(f"data/raw/{self.symbol.lower()}/{self.timeframe}")
        if not raw_dir.exists():
            print(f"Raw directory not found: {raw_dir}")
            return None
            
        files = sorted(raw_dir.glob("*.parquet"))
        if not files:
            print("No raw files found")
            return None
            
        print(f"Combining {len(files)} raw files...")
        dfs = []
        for f in files:
            try:
                dfs.append(pd.read_parquet(f))
            except Exception as e:
                print(f"Error reading {f}: {e}")
                
        if not dfs:
            return None
            
        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        return combined

def main():
    data_dir = Path("data/processed")
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1h"
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"TESTING {symbol}")
        print(f"{'='*50}")
        
        file_path = data_dir / f"binance_{symbol}_{timeframe}_combined.parquet"
        backtester = ZScoreBacktester(file_path, symbol, timeframe)
        
        df = None
        if file_path.exists():
            print(f"Loading {file_path}...")
            df = backtester.load_data()
        else:
            print(f"Combining raw batches...")
            df = backtester.combine_batches()
            
        if df is not None:
            print(f"Loaded {len(df)} candles.")
            df = backtester.calculate_indicators(df)
            
            variations = [
                {'name': 'Vol Filter (Z=2.0 + Low Vol)', 'z_entry': 2.0, 'use_vol_filter': True, 'sl_pct': 0.01},
                {'name': 'Breakout (High Vol)', 'use_breakout': True, 'sl_pct': 0.01},
                {'name': 'Volume Breakout (Doc Style)', 'use_vol_breakout': True, 'tp_pct': 0.02, 'sl_pct': 0.01},
            ]
            
            for v in variations:
                trades, equity = backtester.run_backtest(df, v)
                backtester.analyze_results(trades, equity, v['name'])
        else:
            print(f"Could not load data for {symbol}.")

if __name__ == "__main__":
    main()
