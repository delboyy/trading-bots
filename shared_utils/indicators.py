"""
Advanced Technical Indicators Library
Includes OBV, Session-based indicators, and Candlestick patterns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
import pytz

# ===============================
# VOLUME INDICATORS
# ===============================

def on_balance_volume(df: pd.DataFrame) -> pd.Series:
    """
    On-Balance Volume (OBV) indicator

    OBV = Previous OBV + Volume (if close > previous close)
    OBV = Previous OBV - Volume (if close < previous close)
    OBV = Previous OBV (if close == previous close)
    """
    obv = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + df['Volume'].iloc[i]
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - df['Volume'].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    return obv

def volume_price_trend(df: pd.DataFrame) -> pd.Series:
    """Volume Price Trend (VPT) indicator"""
    vpt = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        price_change = (df['Close'].iloc[i] - df['Close'].iloc[i-1]) / df['Close'].iloc[i-1]
        vpt.iloc[i] = vpt.iloc[i-1] + (price_change * df['Volume'].iloc[i])
    return vpt

# ===============================
# SESSION-BASED INDICATORS
# ===============================

def get_session_indicator(df: pd.DataFrame, timezone: str = 'US/Eastern') -> pd.Series:
    """
    Session-based indicator
    Returns: 0=Off-hours, 1=Asia, 2=London, 3=NY Day, 4=NY After-hours
    """
    # Convert index to specified timezone if not already
    if df.index.tz is None:
        df_idx = df.index.tz_localize('UTC').tz_convert(timezone)
    else:
        df_idx = df.index.tz_convert(timezone)

    session = pd.Series(0, index=df.index)  # Default: off-hours

    # Asia session: 00:00 - 08:00 ET (20:00 - 04:00 UTC previous day to same day)
    asia_mask = (
        ((df_idx.time >= time(20, 0)) & (df_idx.time <= time(23, 59))) |  # Previous day evening
        ((df_idx.time >= time(0, 0)) & (df_idx.time <= time(4, 0)))      # Next day morning
    )
    session[asia_mask] = 1

    # London session: 03:00 - 11:30 ET (07:00 - 15:30 UTC)
    london_mask = (df_idx.time >= time(7, 0)) & (df_idx.time <= time(15, 30))
    session[london_mask] = 2

    # NY Day session: 09:30 - 16:00 ET (13:30 - 20:00 UTC)
    ny_day_mask = (df_idx.time >= time(13, 30)) & (df_idx.time <= time(20, 0))
    session[ny_day_mask] = 3

    # NY After-hours: 16:00 - 20:00 ET (20:00 - 00:00 UTC)
    ny_after_mask = (df_idx.time >= time(20, 0)) & (df_idx.time <= time(23, 59))
    session[ny_after_mask] = 4

    return session

def session_volume_profile(df: pd.DataFrame, session_indicator: pd.Series) -> pd.DataFrame:
    """Calculate volume profile by trading session"""
    sessions = {}
    for session_id in [1, 2, 3, 4]:  # Asia, London, NY Day, NY After
        session_data = df[session_indicator == session_id]
        if not session_data.empty:
            sessions[f'session_{session_id}'] = {
                'avg_volume': session_data['Volume'].mean(),
                'total_volume': session_data['Volume'].sum(),
                'price_range': session_data['High'].max() - session_data['Low'].min(),
                'avg_price': session_data['Close'].mean()
            }
    return pd.DataFrame(sessions).T

# ===============================
# CANDLESTICK PATTERNS
# ===============================

def detect_doji(df: pd.DataFrame, body_threshold: float = 0.05) -> pd.Series:
    """
    Detect Doji candlestick pattern
    Doji: Very small body relative to total range (indecision)
    """
    body_size = abs(df['Close'] - df['Open'])
    total_range = df['High'] - df['Low']
    body_ratio = body_size / (total_range + 0.0001)  # Avoid division by zero
    return body_ratio <= body_threshold

def detect_hammer(df: pd.DataFrame, shadow_ratio: float = 2.0) -> Tuple[pd.Series, pd.Series]:
    """
    Detect Hammer and Shooting Star patterns
    Hammer: Small body, long lower wick (bullish reversal)
    Shooting Star: Small body, long upper wick (bearish reversal)
    """
    body_high = np.maximum(df['Open'], df['Close'])
    body_low = np.minimum(df['Open'], df['Close'])

    upper_wick = df['High'] - body_high
    lower_wick = body_low - df['Low']
    body_size = abs(df['Close'] - df['Open'])

    # Hammer: long lower wick, small upper wick
    hammer = (lower_wick >= shadow_ratio * body_size) & (upper_wick <= body_size)
    hammer = hammer & (body_size > 0)  # Must have some body

    # Shooting Star: long upper wick, small lower wick
    shooting_star = (upper_wick >= shadow_ratio * body_size) & (lower_wick <= body_size)
    shooting_star = shooting_star & (body_size > 0)

    return hammer, shooting_star

def detect_engulfing(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Detect Bullish and Bearish Engulfing patterns
    Bullish Engulfing: Current red candle completely engulfed by previous green candle
    Bearish Engulfing: Current green candle completely engulfed by previous red candle
    """
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    prev_high = df['High'].shift(1)
    prev_low = df['Low'].shift(1)

    # Current candle body
    curr_high = np.maximum(df['Open'], df['Close'])
    curr_low = np.minimum(df['Open'], df['Close'])

    # Previous candle body
    prev_body_high = np.maximum(prev_open, prev_close)
    prev_body_low = np.minimum(prev_open, prev_close)

    # Bullish engulfing: current green candle engulfs previous red candle
    bullish_engulf = (
        (df['Close'] > df['Open']) &  # Current is green
        (prev_close < prev_open) &    # Previous is red
        (curr_high >= prev_body_high) &  # Current high >= prev body high
        (curr_low <= prev_body_low)     # Current low <= prev body low
    )

    # Bearish engulfing: current red candle engulfs previous green candle
    bearish_engulf = (
        (df['Close'] < df['Open']) &  # Current is red
        (prev_close > prev_open) &    # Previous is green
        (curr_high >= prev_body_high) &  # Current high >= prev body high
        (curr_low <= prev_body_low)     # Current low <= prev body low
    )

    return bullish_engulf, bearish_engulf

def detect_morning_star(df: pd.DataFrame) -> pd.Series:
    """
    Detect Morning Star pattern (3-candle bullish reversal)
    1. Large red candle
    2. Small candle (star) with gap down
    3. Large green candle that closes above midpoint of first candle
    """
    # First candle: large red
    first_red = (df['Close'].shift(2) < df['Open'].shift(2)) & \
                (abs(df['Close'].shift(2) - df['Open'].shift(2)) > (df['High'].shift(2) - df['Low'].shift(2)) * 0.6)

    # Second candle: small body (star) with gap down
    star_body = abs(df['Close'].shift(1) - df['Open'].shift(1))
    star_range = df['High'].shift(1) - df['Low'].shift(1)
    small_star = star_body < star_range * 0.3  # Body < 30% of range

    gap_down = df['High'].shift(1) < df['Close'].shift(2)  # Star gaps below first candle

    # Third candle: large green closing above midpoint of first candle
    first_midpoint = (df['Open'].shift(2) + df['Close'].shift(2)) / 2
    third_green = (df['Close'] > df['Open']) & (df['Close'] > first_midpoint)
    large_third = abs(df['Close'] - df['Open']) > (df['High'] - df['Low']) * 0.6

    morning_star = first_red & small_star & gap_down & third_green & large_third

    return morning_star.fillna(False)

def detect_evening_star(df: pd.DataFrame) -> pd.Series:
    """
    Detect Evening Star pattern (3-candle bearish reversal)
    Opposite of morning star
    """
    # First candle: large green
    first_green = (df['Close'].shift(2) > df['Open'].shift(2)) & \
                  (abs(df['Close'].shift(2) - df['Open'].shift(2)) > (df['High'].shift(2) - df['Low'].shift(2)) * 0.6)

    # Second candle: small body (star) with gap up
    star_body = abs(df['Close'].shift(1) - df['Open'].shift(1))
    star_range = df['High'].shift(1) - df['Low'].shift(1)
    small_star = star_body < star_range * 0.3

    gap_up = df['Low'].shift(1) > df['Close'].shift(2)  # Star gaps above first candle

    # Third candle: large red closing below midpoint of first candle
    first_midpoint = (df['Open'].shift(2) + df['Close'].shift(2)) / 2
    third_red = (df['Close'] < df['Open']) & (df['Close'] < first_midpoint)
    large_third = abs(df['Close'] - df['Open']) > (df['High'] - df['Low']) * 0.6

    evening_star = first_green & small_star & gap_up & third_red & large_third

    return evening_star.fillna(False)

# ===============================
# ADVANCED INDICATORS
# ===============================

def keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Keltner Channels: EMA ± ATR bands
    Similar to Bollinger Bands but uses ATR for volatility
    """
    ema = df['Close'].ewm(span=ema_period).mean()

    # Calculate ATR
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(atr_period).mean()

    upper_band = ema + (multiplier * atr)
    lower_band = ema - (multiplier * atr)

    return upper_band, ema, lower_band

def ichimoku_cloud(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Ichimoku Cloud components
    """
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    tenkan_high = df['High'].rolling(9).max()
    tenkan_low = df['Low'].rolling(9).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2

    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    kijun_high = df['High'].rolling(26).max()
    kijun_low = df['Low'].rolling(26).min()
    kijun_sen = (kijun_high + kijun_low) / 2

    # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted forward 26 periods
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

    # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted forward 26 periods
    senkou_b_high = df['High'].rolling(52).max()
    senkou_b_low = df['Low'].rolling(52).min()
    senkou_b = ((senkou_b_high + senkou_b_low) / 2).shift(26)

    # Chikou Span (Lagging Span): Close shifted backward 26 periods
    chikou_span = df['Close'].shift(-26)

    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_a': senkou_a,
        'senkou_b': senkou_b,
        'chikou_span': chikou_span
    }

def stochastic_oscillator(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator
    %K = 100 * ((Close - Lowest Low) / (Highest High - Lowest Low))
    %D = Simple moving average of %K
    """
    lowest_low = df['Low'].rolling(k_period).min()
    highest_high = df['High'].rolling(k_period).max()

    k_percent = 100 * ((df['Close'] - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(d_period).mean()

    return k_percent, d_percent

# ===============================
# UTILITY FUNCTIONS
# ===============================

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all available indicators to dataframe
    """
    df = df.copy()

    # Volume indicators
    df['obv'] = on_balance_volume(df)
    df['vpt'] = volume_price_trend(df)

    # Session indicators
    df['session'] = get_session_indicator(df)

    # Candlestick patterns
    df['doji'] = detect_doji(df)
    df['hammer'], df['shooting_star'] = detect_hammer(df)
    df['bullish_engulfing'], df['bearish_engulfing'] = detect_engulfing(df)
    df['morning_star'] = detect_morning_star(df)
    df['evening_star'] = detect_evening_star(df)

    # Advanced indicators
    df['stoch_k'], df['stoch_d'] = stochastic_oscillator(df)
    df['keltner_upper'], df['keltner_middle'], df['keltner_lower'] = keltner_channels(df)

    # Ichimoku components
    ichimoku = ichimoku_cloud(df)
    df['ichimoku_tenkan'] = ichimoku['tenkan_sen']
    df['ichimoku_kijun'] = ichimoku['kijun_sen']
    df['ichimoku_senkou_a'] = ichimoku['senkou_a']
    df['ichimoku_senkou_b'] = ichimoku['senkou_b']
    df['ichimoku_chikou'] = ichimoku['chikou_span']

    return df
