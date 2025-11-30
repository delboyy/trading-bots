
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

# Add current directory to path to import binance_data_downloader
sys.path.append(os.getcwd())
from binance_data_downloader import BinanceDataDownloader

class MultiAssetDownloader(BinanceDataDownloader):
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        
    def download_history(self, interval, years=2):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
        
        print(f"Downloading {years} years of {self.symbol} {interval} data...")
        
        # Create directory structure
        interval_dir = self.raw_data_dir / self.symbol.lower() / interval
        interval_dir.mkdir(parents=True, exist_ok=True)
        
        # Download in batches
        self.download_date_range(interval, start_date, end_date, batch_days=5) # Increased batch size slightly
        
        # Combine
        self.combine_and_save(interval, start_date, end_date)

def main():
    assets = ['BTCUSDT', 'ETHUSDT']
    intervals = ['15m', '1h']
    
    for asset in assets:
        downloader = MultiAssetDownloader(asset)
        for interval in intervals:
            print(f"\nProcessing {asset} {interval}...")
            downloader.download_history(interval, years=2)

if __name__ == "__main__":
    main()
