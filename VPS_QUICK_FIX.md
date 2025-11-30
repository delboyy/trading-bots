# 🔧 VPS QUICK FIX GUIDE

## Problem
Bots failing to start with:
- `ModuleNotFoundError: No module named 'loguru'`
- `ModuleNotFoundError: No module named 'grok'`

## Solution

### **Option 1: Quick Fix (Recommended)**

Run these commands on your VPS:

```bash
cd /home/trader/trading-bots

# 1. Pull latest code (with fixes)
git pull

# 2. Install missing package (if needed)
pip install loguru

# 3. Set PYTHONPATH
export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"
echo 'export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"' >> ~/.bashrc

# 4. Create logs directory
mkdir -p logs

# 5. Restart bots
python grok/live_bots/run_all_live_bots.py
> start_all
```

---

### **Option 2: Manual Fix (If git pull doesn't work)**

If you can't pull the latest code, run this on VPS:

```bash
cd /home/trader/trading-bots

# Install loguru
pip install loguru

# Set PYTHONPATH permanently
echo 'export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"' >> ~/.bashrc
source ~/.bashrc

# Create logs directory
mkdir -p logs

# Restart bots
python grok/live_bots/run_all_live_bots.py
> start_all
```

---

## What I Fixed (Already in Latest Code)

### ✅ Fixed Import Statements
- Changed `from loguru import logger` → `import logging` + setup
- Fixed `from grok.utils.status_tracker import StatusTracker` path
- Added fallback dummy StatusTracker if import fails

### ✅ Files Updated
1. `grok/live_bots/scalping/live_btc_combo_claude.py`
2. `grok/live_bots/scalping/live_btc_combo_momentum_claude.py`

(Other 4 bots already had correct imports)

---

## Verify It's Working

After restarting, you should see:

```
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Started bot: ETH 1h Volatility (Claude)
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Started bot: ETH 4h Volatility (Claude)
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Started bot: NVDA 1h Volatility (Claude)
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Started bot: BTC Combo 15m (Claude)
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Started bot: BTC Combo Momentum 1d (Claude)
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Started bot: TSLA 15m Time-Based
2025-11-30 16:45:00 - MASTER_BOT_CONTROLLER - INFO - Bot Status: 6/6 running ✅
```

No more `ModuleNotFoundError`!

---

## Troubleshooting

### Still getting "No module named 'grok'"?

```bash
# Check your current directory
pwd  # Should be /home/trader/trading-bots

# Check PYTHONPATH
echo $PYTHONPATH  # Should include /home/trader/trading-bots

# If not set:
export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"
```

### Still getting "No module named 'loguru'"?

```bash
# Install it
pip install loguru

# Or use venv
source venv/bin/activate
pip install loguru
```

### Bots crash immediately?

```bash
# Check individual bot logs
tail -f logs/*.log

# Look for actual error messages
cat logs/btc_combo_15m_claude.log
```

---

## Expected Output When Working

```bash
$ python grok/live_bots/run_all_live_bots.py

🎯 LIVE TRADING BOT CONTROLLER
================================================================================
Available bots:
  eth_1h: ETH 1h Volatility (Claude) - 🔴 STOPPED
  eth_4h: ETH 4h Volatility (Claude) - 🔴 STOPPED
  nvda_1h: NVDA 1h Volatility (Claude) - 🔴 STOPPED
  btc_combo_15m: BTC Combo 15m (Claude) - 🔴 STOPPED
  btc_combo_1d: BTC Combo Momentum 1d (Claude) - 🔴 STOPPED
  tsla_15m: TSLA 15m Time-Based - 🔴 STOPPED

Commands:
  start_all          - Start all bots
  stop_all           - Stop all bots
  status             - Show detailed status
  monitor            - Monitor all logs (verbose)
  exit               - Exit controller

Enter command: start_all

Started 6/6 bots ✅
```

---

## Once Fixed

Your 6 bots will be running and making money! 💰

Monitor with:
```bash
> status
> monitor_errors  # Only show errors
```

---

**Need more help? Check the logs for specific errors!**

