import pandas as pd

class Strategy:
    """Simple momentum strategy based on two moving averages."""

    def __init__(self, data: pd.DataFrame, fast: int = 10, slow: int = 30):
        self.data = data
        self.fast = fast
        self.slow = slow

    def generate_signals(self) -> pd.Series:
        df = self.data.copy()
        df["fast_ma"] = df["Close"].rolling(self.fast).mean()
        df["slow_ma"] = df["Close"].rolling(self.slow).mean()

        df["signal"] = 0
        df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1
        df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1

        return df["signal"].fillna(0)
