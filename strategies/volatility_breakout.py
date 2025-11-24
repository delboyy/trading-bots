import pandas as pd

class Strategy:
    """Volatility breakout using ATR as band width."""

    def __init__(self, data: pd.DataFrame, atr_window: int = 14, k: float = 1.5):
        self.data = data
        self.atr_window = atr_window
        self.k = k

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        high_low = (df["High"] - df["Low"]).abs()
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(self.atr_window).mean()

    def generate_signals(self) -> pd.Series:
        df = self.data.copy()
        df["atr"] = self._atr(df)
        df["upper"] = df["Close"].shift() + self.k * df["atr"]
        df["lower"] = df["Close"].shift() - self.k * df["atr"]

        df["signal"] = 0
        df.loc[df["Close"] > df["upper"], "signal"] = 1
        df.loc[df["Close"] < df["lower"], "signal"] = -1

        return df["signal"].fillna(0)
