# Adding New Trading Bots to the System

This guide explains how to add new trading bots to the live trading system, ensuring they work seamlessly with the dashboard, monitoring, and master controller.

## Prerequisites

- Python 3.8+
- Alpaca API credentials configured
- Existing bot template or strategy logic

---

## Step 1: Create the Bot File

### File Location
```
grok/live_bots/live_{symbol}_{timeframe}_{strategy}.py
```

**Example:** `live_gld_5m_atr_range_scalping.py`

### Required Imports
```python
#!/usr/bin/env python3
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np  # If needed

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit
from grok.utils.status_tracker import StatusTracker
```

### Setup Logging
```python
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/{bot_name}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BOT_NAME')
```

---

## Step 2: Bot Class Structure

### Required Components

```python
class YourBotClass:
    def __init__(self):
        # 1. Status Tracker (REQUIRED for dashboard)
        self.tracker = StatusTracker()
        self.bot_id = "unique_bot_id"  # e.g., "gld_5m_atr"
        
        # 2. Alpaca API credentials
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        
        # 3. Initialize API
        self.api = REST(self.api_key, self.api_secret, self.base_url)
        
        # 4. Trading parameters
        self.symbol = 'SYMBOL'  # e.g., 'GLD', 'BTC/USD', 'ETHUSD'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)  # CORRECT syntax
        
        # 5. Position tracking
        self.position = 0
        self.entry_price = 0
        self.entry_time = None
```

### Critical: Dashboard Status Updates

**MUST include this in your main loop:**

```python
# Update Dashboard (REQUIRED)
try:
    account = self.api.get_account()
    positions = self.api.list_positions()
    pos = next((p for p in positions if p.symbol == self.symbol), None)
    
    self.tracker.update_status(self.bot_id, {
        'equity': float(account.equity),
        'cash': float(account.cash),
        'position': float(pos.qty) if pos else 0,
        'entry_price': float(pos.avg_entry_price) if pos else 0,
        'unrealized_pl': float(pos.unrealized_pl) if pos else 0,
        'error': None
    })
except Exception as e:
    logger.error(f"Status update failed: {e}")
    self.tracker.update_status(self.bot_id, {'error': str(e)})
```

---

## Step 3: Data Fetching (Alpaca API)

### For Stocks/ETFs (GLD, NVDA, TSLA, etc.)
```python
def get_historical_data(self, limit: int = 200) -> Optional[pd.DataFrame]:
    try:
        bars = self.api.get_bars(
            self.symbol,
            self.timeframe,
            limit=limit
        ).df  # .df returns DataFrame directly
        
        if bars.empty:
            return None
            
        # Rename columns (Alpaca uses lowercase)
        bars = bars.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        bars.index = pd.to_datetime(bars.index)
        return bars
        
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None
```

### For Crypto (BTC/USD, ETH/USD)
```python
def get_historical_data(self, limit: int = 200) -> Optional[pd.DataFrame]:
    try:
        # Use get_crypto_bars for crypto pairs
        bars = self.api.get_crypto_bars(
            self.symbol,  # Must be 'BTC/USD' format
            self.timeframe,
            limit=limit
        ).df
        
        # Same column renaming as above
        ...
```

---

## Step 4: Main Trading Loop

### Required Structure

```python
def run(self):
    """Main trading loop"""
    logger.info("Starting bot...")
    
    while True:
        try:
            # 1. Update Dashboard Status (REQUIRED)
            # ... (see Step 2)
            
            # 2. Get market data
            df = self.get_historical_data(limit=100)
            if df is None:
                time.sleep(60)
                continue
            
            # 3. Check exit conditions (if in position)
            if self.position != 0:
                current_price = df['Close'].iloc[-1]
                if self.check_exit_conditions(current_price):
                    self.close_position()
            
            # 4. Generate signals (if no position)
            elif self.position == 0:
                signal = self.generate_signal(df)
                if signal != 0:
                    # Calculate position size
                    account = self.api.get_account()
                    equity = float(account.equity)
                    # ... execute trade
            
            # 5. Sleep before next iteration
            time.sleep(60)  # 1 minute
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            if self.position != 0:
                self.close_position()
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            self.tracker.update_status(self.bot_id, {'error': f"CRASH: {str(e)}"})
            time.sleep(60)

if __name__ == "__main__":
    bot = YourBotClass()
    bot.run()
```

---

## Step 5: Add to Master Controller

### Edit: `grok/live_bots/run_all_live_bots.py`

**1. Add to `bot_scripts` dictionary (line ~40):**
```python
self.bot_scripts = {
    # ... existing bots ...
    'your_bot_key': 'live_your_bot_file.py',
}
```

**2. Add to `bot_info` dictionary (line ~69):**
```python
self.bot_info = {
    # ... existing bots ...
    'your_bot_key': {
        'name': 'Your Bot Display Name',
        'description': 'Strategy description - X% return, Y% win rate'
    },
}
```

---

## Step 6: Verify Symbol Compatibility

### Check if your symbol works with Alpaca:

```python
python3 -c "
from alpaca_trade_api import REST
import os

api = REST(
    os.getenv('APCA_API_KEY_ID'),
    os.getenv('APCA_API_SECRET_KEY'),
    'https://paper-api.alpaca.markets'
)

# Test your symbol
quote = api.get_latest_quote('YOUR_SYMBOL')
print(f'✅ Symbol works: \${quote.askprice}')
"
```

### Common Symbol Formats:
- **Stocks/ETFs:** `GLD`, `NVDA`, `TSLA`, `SPY`
- **Crypto:** `BTC/USD`, `ETH/USD` (with slash!)
- **Futures:** `/NQ`, `/ES` (with leading slash)

---

## Step 7: Common Pitfalls to Avoid

### ❌ WRONG: Old TimeFrame API
```python
self.timeframe = TimeFrame.Hour * 4  # DEPRECATED
```

### ✅ CORRECT: New TimeFrame API
```python
self.timeframe = TimeFrame(4, TimeFrameUnit.Hour)
```

---

### ❌ WRONG: Missing Dashboard Updates
```python
# Bot runs but doesn't show on dashboard
def run(self):
    while True:
        # ... trading logic ...
        time.sleep(60)
```

### ✅ CORRECT: Include Status Updates
```python
def run(self):
    while True:
        # Update dashboard
        self.tracker.update_status(self.bot_id, {...})
        # ... trading logic ...
```

---

### ❌ WRONG: Crypto Symbol Format
```python
self.symbol = 'BTCUSD'  # Missing slash
```

### ✅ CORRECT: Crypto Symbol Format
```python
self.symbol = 'BTC/USD'  # With slash
```

---

### ❌ WRONG: No Error Tracking
```python
except Exception as e:
    logger.error(f"Error: {e}")
    # Dashboard shows "running" but bot is broken
```

### ✅ CORRECT: Error Tracking
```python
except Exception as e:
    logger.error(f"Error: {e}")
    self.tracker.update_status(self.bot_id, {'error': str(e)})
```

---

## Step 8: Testing Checklist

Before deploying, verify:

- [ ] Bot file is in `grok/live_bots/`
- [ ] Logging configured with unique log file
- [ ] `bot_id` is unique
- [ ] Symbol format is correct for asset type
- [ ] TimeFrame uses new API syntax
- [ ] StatusTracker is initialized
- [ ] Dashboard status updates in main loop
- [ ] Error handling includes status updates
- [ ] Bot added to `run_all_live_bots.py`
- [ ] Bot info added with description
- [ ] Tested symbol with Alpaca API

---

## Step 9: Deploy

```bash
# Local machine
git add grok/live_bots/live_your_bot.py
git add grok/live_bots/run_all_live_bots.py
git commit -m "Add new bot: Your Bot Name"
git push

# VPS
git pull
python grok/live_bots/run_all_live_bots.py
# Select "start_all" or "start your_bot_key"
```

---

## Step 10: Monitor

### Check Bot Status
```bash
# In controller
> status

# Or use filtered monitoring
> monitor_errors    # See only errors
> monitor_trades    # See only trades
> monitor_info      # See only info logs
```

### Check Dashboard
```bash
streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
```

Visit: `http://your-vps-ip:8501`

---

## Quick Reference: Bot Template

```python
#!/usr/bin/env python3
import os, sys, time, logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from alpaca_trade_api import REST, TimeFrame, TimeFrameUnit

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))
from grok.utils.status_tracker import StatusTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot_name.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BOT_NAME')

class YourBot:
    def __init__(self):
        self.tracker = StatusTracker()
        self.bot_id = "unique_id"
        self.api = REST(
            os.getenv('APCA_API_KEY_ID'),
            os.getenv('APCA_API_SECRET_KEY'),
            os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        self.symbol = 'SYMBOL'
        self.timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        self.position = 0
    
    def get_historical_data(self, limit=200):
        bars = self.api.get_bars(self.symbol, self.timeframe, limit=limit).df
        return bars.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    
    def run(self):
        while True:
            try:
                # Update dashboard
                account = self.api.get_account()
                positions = self.api.list_positions()
                pos = next((p for p in positions if p.symbol == self.symbol), None)
                self.tracker.update_status(self.bot_id, {
                    'equity': float(account.equity),
                    'cash': float(account.cash),
                    'position': float(pos.qty) if pos else 0,
                    'entry_price': float(pos.avg_entry_price) if pos else 0,
                    'unrealized_pl': float(pos.unrealized_pl) if pos else 0
                })
                
                # Trading logic here
                df = self.get_historical_data()
                # ... your strategy ...
                
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error: {e}")
                self.tracker.update_status(self.bot_id, {'error': str(e)})
                time.sleep(60)

if __name__ == "__main__":
    YourBot().run()
```

---

## Troubleshooting

### Bot shows as STOPPED on dashboard
- Check logs: `cat logs/your_bot.log`
- Verify symbol format
- Check API credentials

### Bot shows as RUNNING but no trades
- Check `monitor_info` for data fetching
- Verify strategy logic
- Check market hours

### Dashboard shows same P&L for all bots
- Ensure each bot has unique `bot_id`
- StatusTracker auto-captures start_equity

### Timestamp errors
- Use `.df` method: `api.get_bars(...).df`
- Don't manually format timestamps

---

**Last Updated:** 2025-11-26
