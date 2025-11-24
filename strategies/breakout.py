import pandas as pd

class Strategy:
    """High/low channel breakout strategy."""

    def __init__(self, data: pd.DataFrame, window: int = 20):
        self.data = data
        self.window = window

    def generate_signals(self) -> pd.Series:
        df = self.data.copy()
        df["high_roll"] = df["High"].rolling(self.window).max()
        df["low_roll"] = df["Low"].rolling(self.window).min()

        df["signal"] = 0
        df.loc[df["Close"] > df["high_roll"], "signal"] = 1
        df.loc[df["Close"] < df["low_roll"], "signal"] = -1

        return df["signal"].fillna(0)
