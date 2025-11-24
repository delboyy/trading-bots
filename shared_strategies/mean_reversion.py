import pandas as pd

class Strategy:
    """Simple mean reversion strategy using rolling z-score."""

    def __init__(self, data: pd.DataFrame, window: int = 20, z_thresh: float = 1.5):
        self.data = data
        self.window = window
        self.z_thresh = z_thresh

    def generate_signals(self) -> pd.Series:
        df = self.data.copy()
        df["ma"] = df["Close"].rolling(self.window).mean()
        df["std"] = df["Close"].rolling(self.window).std()

        df["zscore"] = (df["Close"] - df["ma"]) / df["std"]
        df["signal"] = 0
        df.loc[df["zscore"] > self.z_thresh, "signal"] = -1
        df.loc[df["zscore"] < -self.z_thresh, "signal"] = 1

        return df["signal"].fillna(0)
