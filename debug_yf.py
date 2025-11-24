import yfinance as yf
import pandas as pd

def test_download():
    df = yf.download("BTC-USD", period="1d", interval="1h")
    print("Columns:", df.columns)
    print("Head:", df.head())
    if isinstance(df.columns, pd.MultiIndex):
        print("MultiIndex detected")

if __name__ == "__main__":
    test_download()
