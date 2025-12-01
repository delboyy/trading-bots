# EASY POSITION SIZING - Quick Start Guide

## ✅ DONE: Centralized Configuration Created

I've created a **single config file** that controls position sizing for ALL bots.

---

## 📁 File Location

**`config/position_sizing.py`**

This is the ONLY file you need to edit to change risk for all bots!

---

## 🎯 Current Settings (Already Set to 2%)

```python
GLOBAL_RISK_PCT = 0.02          # 2% of equity per trade ✅
MAX_POSITION_PCT = 0.10         # Max 10% of equity in one position
```

**This means:**
- Every bot risks **2% of your account** per trade
- No single position can be larger than **10% of your account**

---

## 🔧 How to Change Risk (Super Easy!)

### To Change Risk for ALL Bots:

1. Open: `config/position_sizing.py`
2. Change this line:
   ```python
   GLOBAL_RISK_PCT = 0.02  # Change this number
   ```

**Examples:**
- `0.01` = 1% risk (conservative)
- `0.02` = 2% risk (moderate) ← **Current**
- `0.03` = 3% risk (aggressive)

### To Change Risk for ONE Specific Bot:

1. Open: `config/position_sizing.py`
2. Add to the `BOT_RISK_OVERRIDES` section:
   ```python
   BOT_RISK_OVERRIDES = {
       'eth_1h': 0.03,      # 3% risk for ETH 1h
       'btc_combo': 0.015,  # 1.5% risk for BTC combo
   }
   ```

---

## 📊 How Bots Use This

**For each bot, add these 2 lines to the imports:**

```python
# At the top of each bot file
from grok.utils.position_sizing import calculate_position_size, get_risk_pct

# In __init__:
self.risk_pct = get_risk_pct(self.bot_id)

# In place_order method:
position_size = calculate_position_size(
    bot_id=self.bot_id,
    account_equity=equity,
    entry_price=entry_price
)
```

---

## 🚀 Quick Implementation

**I can add these 2 lines to all your bots automatically.**

Would you like me to:

**Option A:** Add the import to all bots now (5 minutes)
- All bots will use the centralized config
- You can change risk by editing ONE file

**Option B:** Keep current bot code, use config later
- Bots work as-is with their current sizing
- You can migrate to centralized config when ready

---

## 💡 Benefits of Centralized Config

✅ Change risk for ALL bots by editing ONE file  
✅ Override risk for specific bots easily  
✅ No need to edit 10 different bot files  
✅ Consistent risk management across all strategies  

---

## 📝 Example: Changing Risk

**Before (had to edit 10 files):**
```python
# In bot 1
self.max_position_size = 0.02

# In bot 2
self.max_position_size = 0.02

# In bot 3...
# etc.
```

**After (edit 1 file):**
```python
# In config/position_sizing.py
GLOBAL_RISK_PCT = 0.03  # Changed from 0.02 to 0.03
# Done! All bots now use 3%
```

---

## ❓ What Do You Want?

**A) Add centralized config to all bots now** (Recommended)
- I'll update all 10 bots to use the config file
- Takes 5 minutes
- You can then change risk by editing ONE file

**B) Just use the config file manually**
- Config file is ready
- You add it to bots yourself when needed
- Current bots keep working as-is

**Which option?**
