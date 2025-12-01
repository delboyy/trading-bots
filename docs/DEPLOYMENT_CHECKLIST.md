# 🚀 DEPLOYMENT CHECKLIST

## ✅ Pre-Deployment Verification (COMPLETED)

- [x] All 10 bots pass syntax check
- [x] All imports working correctly  
- [x] Position sizing utility tested
- [x] No `ModuleNotFoundError: No module named 'grok'` errors
- [x] GLD bot bugs fixed
- [x] Path resolution corrected

## 📋 Deployment Steps

### 1. Commit Changes Locally

```bash
cd /Users/a1/Projects/Trading/trading-bots

# Check what's changed
git status

# Add all changes
git add .

# Commit with descriptive message
git commit -m "Fix: Implement centralized position sizing (2% risk) and resolve import errors

- Created config/position_sizing.py for centralized risk management
- Created grok/utils/position_sizing.py utility
- Updated all 10 bots to use centralized position sizing
- Fixed import path resolution (parents[2] -> parents[3])
- Fixed GLD bot bugs (undefined current_price)
- All bots tested and verified working
"

# Push to remote
git push origin main
```

### 2. Deploy to VPS

```bash
# SSH into VPS
ssh trader@your-vps

# Navigate to project
cd ~/trading-bots

# Pull latest changes
git pull origin main

# Verify files updated
ls -la config/position_sizing.py
ls -la grok/utils/position_sizing.py

# Stop current bots (if running)
pkill -f "python.*live_.*"

# Start bot controller
python grok/live_bots/run_all_live_bots.py
```

### 3. Monitor Logs

```bash
# Watch the main log
tail -f logs/master_bot_controller.log

# Check for errors
grep "ERROR" logs/master_bot_controller.log

# Verify no ModuleNotFoundError
grep "ModuleNotFoundError" logs/master_bot_controller.log
```

### 4. Verify Bot Status

Expected output:
```
✅ Bot Status: 10/10 running
✅ No "ModuleNotFoundError: No module named 'grok'" errors
✅ All bots fetching data successfully
```

## 🔍 What to Watch For

### ✅ Good Signs:
- All bots start without import errors
- Position sizing calculations appear in logs
- Bots fetch market data successfully
- No crashes in first 5 minutes

### ❌ Red Flags:
- `ModuleNotFoundError` errors
- `ImportError` errors  
- Bots immediately crashing
- "No module named 'grok'" messages

## 🛠️ Troubleshooting

### If bots fail with import errors:

```bash
# Verify Python path on VPS
cd ~/trading-bots
python3 -c "import sys; print('\n'.join(sys.path))"

# Test imports manually
python3 -c "from grok.utils.position_sizing import calculate_position_size; print('OK')"

# Check file permissions
ls -la grok/utils/position_sizing.py
ls -la config/position_sizing.py
```

### If position sizing seems wrong:

```bash
# Check config
cat config/position_sizing.py | grep GLOBAL_RISK_PCT

# Should show: GLOBAL_RISK_PCT = 0.02
```

## 📊 Expected Behavior

With $10,000 equity and 2% risk:
- Each trade risks $200 (2% of $10,000)
- Position size varies by asset price
- Example: BTC at $50k = 0.004 BTC ($200)
- Example: ETH at $3k = 0.0667 ETH ($200)

## ✅ Success Criteria

- [ ] All 10 bots running
- [ ] No import errors in logs
- [ ] Position sizes calculated correctly
- [ ] Bots can fetch market data
- [ ] Dashboard shows all bots active

---

**Ready to deploy!** 🚀
