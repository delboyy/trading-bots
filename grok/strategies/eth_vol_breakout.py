
import pandas as pd
import numpy as np

class ETHVolBreakoutStrategy:
    def __init__(self):
        self.symbol = "ETHUSDT"
        self.timeframe = "1h"
        self.z_entry = 2.0
        self.sl_pct = 0.01
        self.fee_rate = 0.0001
        
    def calculate_indicators(self, df):
        df = df.copy()
        
        # Z-Score
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
        
        return df
        
    def get_signal(self, row, position):
        # row contains: close, ZScore, ATR, ATR_MA, SMA
        
        current_price = row['close']
        z_score = row['ZScore']
        atr = row['ATR']
        atr_ma = row['ATR_MA']
        sma = row['SMA']
        
        is_high_vol = atr > atr_ma
        
        if position == 0:
            if is_high_vol:
                if z_score > self.z_entry:
                    return 'buy'
                elif z_score < -self.z_entry:
                    return 'sell'
        
        elif position > 0: # Long
            # Exit if price crosses below SMA
            if current_price < sma:
                return 'exit'
                
        elif position < 0: # Short
            # Exit if price crosses above SMA
            if current_price > sma:
                return 'exit'
                
        return 'hold'
