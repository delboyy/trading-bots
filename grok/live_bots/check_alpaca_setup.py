#!/usr/bin/env python3
"""
Alpaca Environment Setup Checker
Verifies your Alpaca API credentials and connection
"""

import os
import sys
from alpaca_trade_api import REST

def check_environment():
    """Check if Alpaca environment is properly configured"""
    print("🔍 Checking Alpaca Environment Setup")
    print("=" * 50)

    # Check environment variables
    api_key = os.getenv('APCA_API_KEY_ID')
    api_secret = os.getenv('APCA_API_SECRET_KEY')
    base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

    print(f"API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"API Secret: {'✅ Set' if api_secret else '❌ Missing'}")
    print(f"Base URL: {base_url}")

    if not api_key or not api_secret:
        print("\n❌ Missing credentials!")
        print("\nTo set credentials, run:")
        print("export APCA_API_KEY_ID='your_key_here'")
        print("export APCA_API_SECRET_KEY='your_secret_here'")
        if 'paper' in base_url:
            print("export APCA_API_BASE_URL='https://paper-api.alpaca.markets'  # Paper trading")
        else:
            print("export APCA_API_BASE_URL='https://api.alpaca.markets'  # Live trading")
        return False

    print("\n🔌 Testing API Connection...")

    try:
        # Test API connection
        api = REST(api_key, api_secret, base_url)

        # Test account access
        account = api.get_account()
        print("✅ API Connection: Successful")
        print(f"✅ Account Status: {account.status}")
        print(".2f")
        print(".2f")
        print(".2f")

        # Test market data access
        print("\n📊 Testing Market Data Access...")
        bars = api.get_bars('SPY', '1D', limit=1)
        if bars:
            print("✅ Market Data: Available")
            print(f"   Latest SPY price: ${bars[0].c:.2f}")
        else:
            print("⚠️  Market Data: Limited")

        # Check if paper or live
        if 'paper' in base_url:
            print("\n🧪 PAPER TRADING MODE")
            print("   This is a SIMULATED account - no real money at risk")
            print("   Perfect for testing your bots safely")
        else:
            print("\n💰 LIVE TRADING MODE")
            print("   ⚠️  WARNING: This is a REAL money account!")
            print("   Make sure you understand the risks before running bots")

        print("\n✅ Alpaca Setup Complete!")
        print("   You can now run your live trading bots")

        return True

    except Exception as e:
        print(f"❌ API Connection Failed: {e}")
        print("\nPossible issues:")
        print("- Invalid API credentials")
        print("- Network connectivity issues")
        print("- Alpaca account restrictions")
        print("- Wrong environment variables")
        return False

def show_next_steps():
    """Show what to do next"""
    print("\n" + "=" * 50)
    print("🚀 NEXT STEPS")
    print("=" * 50)

    base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

    if 'paper' in base_url:
        print("1. 📚 Read the LIVE_BOTS_README.md for detailed instructions")
        print("2. 🧪 Test your bots on paper trading (recommended)")
        print("3. 💻 Start individual bots:")
        print("   python live_gld_4h_mean_reversion.py &")
        print("4. 📊 Monitor performance:")
        print("   tail -f logs/gld_4h_mean_reversion.log")
        print("5. 🎯 Gradually add more bots as confidence grows")
    else:
        print("⚠️  LIVE TRADING DETECTED - EXTREME CAUTION REQUIRED!")
        print()
        print("1. 📚 Read ALL warnings in LIVE_BOTS_README.md")
        print("2. 🧪 Test extensively on paper trading first")
        print("3. 💰 Ensure adequate account funding (see calculator)")
        print("4. 📏 Start with SMALL position sizes (25-50% of calculated)")
        print("5. 👀 Monitor CONSTANTLY during market hours")
        print("6. 🛑 Know your emergency stop procedures")

    print("\n📋 Useful Commands:")
    print("• Check bot status: python run_all_live_bots.py")
    print("• View all logs: tail -f logs/*.log")
    print("• Stop all bots: pkill -f 'live_.*\.py'")

if __name__ == "__main__":
    success = check_environment()
    show_next_steps()

    if not success:
        sys.exit(1)
