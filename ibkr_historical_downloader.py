#!/usr/bin/env python3
"""
IBKR Historical Data Downloader
Fetches 2+ years of historical data from Interactive Brokers with auto-chunking
"""

from ib_insync import *
import pandas as pd
from datetime import datetime, timedelta
import time
import os


def stock(symbol):
    """Create a US stock contract for IBKR"""
    return Stock(symbol, "SMART", "USD")


def get_max_duration_for_bar_size(bar_size):
    """
    Get maximum allowed duration for each bar size per IBKR limits
    Returns: (max_duration_str, chunk_size_days)
    """
    bar_size_limits = {
        "1 day": ("30 Y", 365*30),     # 30 years max
        "1 hour": ("1 M", 30),         # 1 month max, chunk monthly
        "30 mins": ("2 W", 14),        # 2 weeks max, chunk bi-weekly
        "15 mins": ("2 W", 14),        # 2 weeks max, chunk bi-weekly
        "5 mins": ("2 W", 14),         # 2 weeks max, chunk bi-weekly
        "1 min": ("1 W", 7),           # 1 week max, chunk weekly
    }

    return bar_size_limits.get(bar_size, ("1 M", 30))


def fetch_in_chunks(contract, end_datetime, total_years, bar_size, whatToShow="TRADES"):
    """
    Fetch historical data in chunks to respect IBKR limits

    Args:
        contract: IBKR contract object
        end_datetime: End date for data (datetime)
        total_years: Total years of data to fetch
        bar_size: Bar size (e.g., "5 mins", "1 hour", "1 day")
        whatToShow: Data type ("TRADES" for stocks)

    Returns:
        pd.DataFrame: Combined historical data
    """

    print(f"Fetching {total_years} years of {bar_size} data for {contract.symbol}")

    # Get IBKR limits for this bar size
    max_duration, chunk_days = get_max_duration_for_bar_size(bar_size)

    # Calculate start date
    start_datetime = end_datetime - timedelta(days=int(total_years * 365.25))

    print(f"Date range: {start_datetime.date()} to {end_datetime.date()}")
    print(f"Chunk size: {chunk_days} days (IBKR limit for {bar_size})")

    all_bars = []
    current_end = end_datetime
    chunks_fetched = 0

    while current_end > start_datetime:
        # Calculate chunk start
        chunk_start = current_end - timedelta(days=chunk_days)
        if chunk_start < start_datetime:
            chunk_start = start_datetime

        # Format for IBKR
        duration_str = f"{chunk_days} D"

        print(f"Fetching chunk {chunks_fetched + 1}: {chunk_start.date()} to {current_end.date()}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Request historical data
                bars = ib.reqHistoricalData(
                    contract,
                    endDateTime=current_end,
                    durationStr=duration_str,
                    barSizeSetting=bar_size,
                    whatToShow=whatToShow,
                    useRTH=True,
                    formatDate=1,
                    keepUpToDate=False,
                )

                if bars:
                    # Convert to DataFrame
                    df_chunk = pd.DataFrame(bars)
                    df_chunk['date'] = pd.to_datetime(df_chunk['date'])
                    df_chunk.set_index('date', inplace=True)

                    all_bars.append(df_chunk)
                    chunks_fetched += 1
                    print(f"  ✅ Got {len(df_chunk)} bars")
                    break
                else:
                    print(f"  ⚠️  No data in chunk (attempt {attempt + 1}/{max_retries})")

            except Exception as e:
                error_msg = str(e)
                if "162" in error_msg:  # Historical Market Data Service error
                    print(f"  ❌ Timeout error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
                        continue
                elif "326" in error_msg:  # Client ID in use
                    print(f"  ❌ Client ID conflict: {error_msg}")
                    print("  Please ensure no other connections are using client ID 99")
                    return pd.DataFrame()
                else:
                    print(f"  ❌ Error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue

                if attempt == max_retries - 1:
                    print(f"  ❌ Failed to fetch chunk after {max_retries} attempts")
                    return pd.DataFrame()

        # Move to next chunk
        current_end = chunk_start

        # Small delay between chunks to be respectful
        time.sleep(0.5)

    # Combine all chunks
    if all_bars:
        combined_df = pd.concat(all_bars)

        # Remove duplicates and sort
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
        combined_df = combined_df.sort_index()

        print(f"✅ Total combined data: {len(combined_df)} bars")
        return combined_df
    else:
        print("❌ No data retrieved")
        return pd.DataFrame()


def main():
    """Main execution function"""
    import sys

    # Get command line arguments or use defaults
    if len(sys.argv) >= 4:
        symbol = sys.argv[1].strip().upper()
        bar_size = sys.argv[2].strip()
        years = int(sys.argv[3].strip())
    else:
        # Default values for testing
        symbol = "GOOGL"
        bar_size = "15 mins"
        years = 2

    print("IBKR Historical Data Downloader")
    print("=" * 40)
    print(f"Symbol: {symbol}")
    print(f"Bar Size: {bar_size}")
    print(f"Years: {years}")
    print("=" * 40)

    # Validate inputs
    valid_bar_sizes = ["1 day", "1 hour", "30 mins", "15 mins", "5 mins", "1 min"]
    if bar_size not in valid_bar_sizes:
        print(f"❌ Invalid bar size. Must be one of: {', '.join(valid_bar_sizes)}")
        return

    if years < 1 or years > 30:
        print("❌ Years must be between 1 and 30")
        return

    # Connect to IBKR
    print("\nConnecting to IBKR TWS...")

    try:
        # Try different client IDs starting from 97 (skip 99 which times out)
        client_ids = [97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86]
        connected = False

        for client_id in client_ids:
            try:
                print(f"Trying client ID {client_id}...")
                ib.connect("127.0.0.1", 7496, clientId=client_id, readonly=True, timeout=15)
                print(f"✅ Connected to IBKR TWS with client ID {client_id}")
                connected = True
                break
            except Exception as e:
                print(f"❌ Client ID {client_id} failed: {str(e)[:80]}...")
                continue

        if not connected:
            print("❌ Could not connect to IBKR - all client IDs in use")
            return

        # Create contract
        contract = stock(symbol)
        ib.qualifyContracts(contract)
        print(f"✅ Contract qualified: {contract}")

        # Set end date to now
        end_datetime = datetime.now()

        # Fetch data with chunking
        df = fetch_in_chunks(contract, end_datetime, years, bar_size, "TRADES")

        if not df.empty:
            # Create output directory
            os.makedirs("data", exist_ok=True)

            # Clean bar size for filename
            bar_size_clean = bar_size.replace(" ", "")
            filename = f"data/{symbol}_{bar_size_clean}_{years}y.csv"

            # Save to CSV
            df.to_csv(filename)
            print(f"✅ Saved {len(df)} rows to {filename}")

            # Print summary
            print("\n📊 SUMMARY:")
            print(f"Symbol: {symbol}")
            print(f"Bar Size: {bar_size}")
            print(f"Years: {years}")
            print(f"Total Rows: {len(df)}")
            print(f"Date Range: {df.index[0].date()} to {df.index[-1].date()}")
            print(f"Duration: {(df.index[-1] - df.index[0]).days} days")
        else:
            print("❌ No data to save")

    except Exception as e:
        print(f"❌ Connection or execution error: {e}")

    finally:
        # Always disconnect safely
        try:
            ib.disconnect()
            print("✅ Disconnected from IBKR")
        except:
            pass


if __name__ == "__main__":
    # Initialize IBKR
    ib = IB()

    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        try:
            ib.disconnect()
        except:
            pass
