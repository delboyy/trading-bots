# Bot System Update Summary

## 📊 New Bot Structure

### Total Bots: 11 (down from 30)

**Long-Term Bots: 8**
- Located in: `grok/live_bots/long_term/`
- Timeframes: 1h, 4h, 1d

**Scalping Bots: 3**
- Located in: `grok/live_bots/scalping/`
- Timeframes: 15m

---

## 📁 Bot Inventory

### Long-Term Bots (8)

| Bot Key | File | Asset | Timeframe | Type |
|---------|------|-------|-----------|------|
| eth_1h | live_eth_1h_volatility_breakout_claude.py | ETH | 1h | Claude |
| eth_4h | live_eth_4h_volatility_breakout_claude.py | ETH | 4h | Claude |
| eth_1d | live_eth_1d_volatility_breakout.py | ETH | 1d | Standard |
| nvda_1h | live_nvda_1h_volatility_breakout_claude.py | NVDA | 1h | Claude |
| nvda_1d | live_nvda_1d_volatility_breakout.py | NVDA | 1d | Standard |
| tsla_4h_le | live_tsla_4h_fib_local_extrema.py | TSLA | 4h | Fib |
| tsla_1d | live_tsla_1d_volatility_breakout.py | TSLA | 1d | Standard |
| spy_1d | live_spy_1d_volatility_breakout.py | SPY | 1d | Standard |

### Scalping Bots (3)

| Bot Key | File | Asset | Timeframe | Type |
|---------|------|-------|-----------|------|
| btc_combo | live_btc_combo_claude.py | BTC | 15m | Claude |
| btc_combo_momentum | live_btc_combo_momentum_claude.py | BTC | 15m | Claude |
| tsla_15m_time | live_tsla_15m_time_based_scalping.py | TSLA | 15m | Standard |

---

## 🔧 Controllers Updated

### 1. run_all_live_bots.py
- **Total Bots:** 11
- **Long-term:** 8 bots
- **Scalping:** 3 bots
- **Use Case:** Run all bots together

### 2. run_longterm_bots.py
- **Total Bots:** 8
- **Bots:** All from `long_term/` folder
- **Use Case:** Separate long-term account

### 3. run_shortterm_bots.py
- **Total Bots:** 3
- **Bots:** All from `scalping/` folder
- **Use Case:** Separate scalping account

---

## 🗑️ Deleted Bots (28)

### Removed Long-Term:
- slv_4h, gld_4h, nq_4h, btc_1h, meta_1h, xlk_1h, tsla_4h
- gld_4h_mean_reversion_MARGIN

### Removed Scalping:
- eth_5m, btc_5m, nvda_5m_squeeze, btc_15m_squeeze
- btc_5m_scalp_z, nvda_15m_squeeze, amd_5m_vol
- googl_15m_rsi, msft_5m_rsi, msft_5m_winner
- gld_5m_atr, gld_5m_fib, gld_5m_session
- btc_5m_vwap

---

## 📊 Dashboard Compatibility

The dashboard (`dashboard/app.py`) will automatically work with the new bot structure because it reads from `bot_status.json` which is updated by the `StatusTracker` in each bot.

**No dashboard changes needed** - it dynamically displays whatever bots are running.

---

## 🚀 Usage

### Start All Bots
```bash
python grok/live_bots/run_all_live_bots.py
> start_all
```

### Start Long-Term Only
```bash
python grok/live_bots/run_longterm_bots.py
> start_all
```

### Start Scalping Only
```bash
python grok/live_bots/run_shortterm_bots.py
> start_all
```

### Dual-Account Setup
```bash
./start_dual_account_system.sh
```

---

## ✅ What Was Updated

1. ✅ **run_all_live_bots.py** - Updated to 11 bots (8 long-term + 3 scalping)
2. ✅ **run_longterm_bots.py** - Updated to 8 long-term bots from `long_term/`
3. ✅ **run_shortterm_bots.py** - Updated to 3 scalping bots from `scalping/`
4. ✅ **Bot paths** - All paths now include subdirectory (`long_term/` or `scalping/`)
5. ✅ **Bot info** - Updated descriptions and names

---

## 📝 Notes

- Dashboard will automatically show only active bots
- StatusTracker works the same way
- Logs will be created for each bot in `logs/` directory
- All bot keys are unique across controllers

---

**Updated:** 2025-11-30
**Total Active Bots:** 11 (8 long-term + 3 scalping)
