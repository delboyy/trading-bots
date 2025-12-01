# URGENT: VPS Fixes Required - 2025-12-01

## 🚨 Critical Action Required

**Your VPS has NOT pulled the latest fixes yet!**

All the fixes we made are in your local repo but not on the VPS.

---

## Step 1: Pull Latest Changes

```bash
# SSH into your VPS
ssh trader@your-vps-ip

# Navigate to project
cd ~/trading-bots

# Pull latest fixes
git pull origin main

# You should see these files updated:
# - grok/live_bots/scalping/live_eth_vol_breakout.py
# - grok/live_bots/scalping/live_btc_combo_momentum_claude.py
# - grok/live_bots/scalping/live_btc_combo_claude.py
```

---

## Step 2: Restart All Bots

```bash
# Stop the controller
# (Press Ctrl+C if it's running in foreground, or kill the process)

# Restart
python grok/live_bots/run_all_live_bots.py

# Or use tmux
tmux attach -t bots
# Ctrl+C to stop
# Then restart: python grok/live_bots/run_all_live_bots.py
```

---

## Step 3: Verify Fixes

After restarting, you should see:

✅ **eth_vol** - Starts without "No module named 'grok'" error  
✅ **btc_combo_momentum** - No more "'close'" errors  
✅ **btc_combo** - Fetches data successfully  

---

## Remaining Issues to Fix

### Issue 1: eth_1h and nvda_1h - DateTime Format

**Error:**
```
Invalid format for parameter start: error parsing '2025-11-29T14:54:23' as RFC3339
```

**These bots need the same datetime fix as btc_combo.**

I'll create fixes for these now...

### Issue 2: gld_5m_fib - Position Sizing Errors

**Errors:**
```
'super' object has no attribute 'askprice'
name 'current_price' is not defined
```

**This bot has bugs in position sizing logic.**

I'll fix this now...

### Issue 3: tsla_15m_time - False Errors

**Not actually an error!** The controller is showing INFO logs as errors.

```
2025-12-01 14:54:42,396 - MASTER_BOT_CONTROLLER - ERROR - Bot tsla_15m_time ERROR: 2025-12-01 14:54:42,395 - TSLA_TIME_SCALPING - INFO - Fetched 23 bars of historical data
```

This is just informational - the bot is working fine.

---

## What I'm Fixing Now

1. ✅ Position Sizing Guide - DONE
2. ⏳ eth_1h datetime format - FIXING
3. ⏳ nvda_1h datetime format - FIXING  
4. ⏳ gld_5m_fib position sizing - FIXING

---

## After Git Pull, Expected Status

| Bot | Status | Notes |
|-----|--------|-------|
| eth_1h | ⚠️ Needs datetime fix | Will fix now |
| eth_4h | ✅ Should work | After git pull |
| nvda_1h | ⚠️ Needs datetime fix | Will fix now |
| btc_combo | ✅ Should work | After git pull |
| btc_combo_momentum | ✅ Should work | After git pull |
| eth_vol | ✅ Should work | After git pull |
| gld_5m_candlestick | ✅ Working | No changes needed |
| gld_5m_fib | ⚠️ Has bugs | Will fix now |
| googl_15m_rsi | ✅ Working | No changes needed |
| tsla_15m_time | ✅ Working | INFO logs are normal |

---

## DO THIS NOW:

```bash
# 1. Pull changes
git pull origin main

# 2. Restart bots
# (Stop current controller with Ctrl+C)
python grok/live_bots/run_all_live_bots.py

# 3. Monitor
> monitor_errors

# 4. Wait for my next fixes for eth_1h, nvda_1h, gld_5m_fib
```

---

**I'm creating the remaining fixes now...**
