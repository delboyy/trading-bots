# 🎯 ALPACA SYMBOL REFERENCE GUIDE

## ✅ VERIFIED CORRECT SYMBOLS FOR ALPACA PAPER TRADING

### 📊 STOCKS & ETFs
| Symbol | Asset | Status | Notes |
|--------|-------|--------|-------|
| `TSLA` | Tesla Inc. | ✅ | Common stock |
| `NVDA` | Nvidia Corp. | ✅ | Common stock |
| `META` | Meta Platforms | ✅ | Common stock |
| `SPY` | SPDR S&P 500 ETF | ✅ | ETF |
| `XLK` | Technology Select Sector SPDR | ✅ | ETF |
| `GLD` | SPDR Gold Shares | ✅ | Gold ETF |
| `SLV` | iShares Silver Trust | ✅ | Silver ETF |

### ₿ CRYPTOCURRENCY
| Symbol | Asset | Status | Notes |
|--------|-------|--------|-------|
| `BTCUSD` | Bitcoin vs USD | ✅ | Alpaca crypto format |
| `ETHUSD` | Ethereum vs USD | ✅ | Alpaca crypto format |

### 📈 FUTURES
| Symbol | Asset | Status | Notes |
|--------|-------|--------|-------|
| `/NQ` | Nasdaq-100 Futures | ✅ | Forward slash prefix required |
| `/ES` | E-mini S&P 500 Futures | ✅ | Forward slash prefix required |
| `/GC` | Gold Futures | ✅ | Forward slash prefix required |
| `/SI` | Silver Futures | ✅ | Forward slash prefix required |
| `/CL` | Crude Oil Futures | ✅ | Forward slash prefix required |

---

## 🚨 COMMON SYMBOL MISTAKES TO AVOID

### ❌ WRONG CRYPTO SYMBOLS:
- `BTC/USDT` → `BTCUSD` (Binance format)
- `ETH/USDT` → `ETHUSD` (Binance format)
- `BTC` → `BTCUSD` (Incomplete)

### ❌ WRONG FUTURES SYMBOLS:
- `NQ=F` → `/NQ` (Yahoo Finance format)
- `NQ` → `/NQ` (CME format, missing slash)
- `ES=F` → `/ES` (Yahoo Finance format)

### ❌ WRONG STOCK SYMBOLS:
- Usually correct, but verify against Alpaca's supported assets

---

## 🧪 SYMBOL TESTING

### Test Symbol Availability:
```bash
# In Python with Alpaca API
from alpaca_trade_api import REST
api = REST(api_key, api_secret, base_url)

# Test a symbol
bars = api.get_bars('BTCUSD', '1D', limit=1)
if bars:
    print("✅ Symbol available")
else:
    print("❌ Symbol not available")
```

### Check Alpaca Asset List:
- Visit: https://alpaca.markets/docs/trading/assets/
- Paper Trading Dashboard: https://app.alpaca.markets/paper/dashboard/overview

---

## 📋 CURRENT BOT SYMBOLS (ALL VERIFIED ✅)

| Bot | Symbol | Asset | Status |
|-----|--------|-------|--------|
| `live_btc_5m_fib_zigzag.py` | `BTCUSD` | Bitcoin | ✅ |
| `live_eth_5m_fib_zigzag.py` | `ETHUSD` | Ethereum | ✅ |
| `live_tsla_4h_fib_local_extrema.py` | `TSLA` | Tesla | ✅ |
| `live_gld_4h_mean_reversion.py` | `GLD` | Gold ETF | ✅ |
| `live_slv_4h_mean_reversion.py` | `SLV` | Silver ETF | ✅ |
| `live_btc_1h_volatility_breakout.py` | `BTCUSD` | Bitcoin | ✅ |
| `live_eth_1h_volatility_breakout.py` | `ETHUSD` | Ethereum | ✅ |
| `live_tsla_4h_volatility_breakout.py` | `TSLA` | Tesla | ✅ |
| `live_nvda_1h_volatility_breakout.py` | `NVDA` | Nvidia | ✅ |
| `live_meta_1h_volatility_breakout.py` | `META` | Meta | ✅ |
| `live_xlk_1h_volatility_breakout.py` | `XLK` | Tech ETF | ✅ |
| `live_nq_4h_volatility_breakout.py` | `/NQ` | Nasdaq Futures | ✅ |
| `live_eth_4h_volatility_breakout.py` | `ETHUSD` | Ethereum | ✅ |
| `live_spy_1d_volatility_breakout.py` | `SPY` | S&P 500 ETF | ✅ |
| `live_nvda_1d_volatility_breakout.py` | `NVDA` | Nvidia | ✅ |
| `live_tsla_1d_volatility_breakout.py` | `TSLA` | Tesla | ✅ |
| `live_eth_1d_volatility_breakout.py` | `ETHUSD` | Ethereum | ✅ |

---

## 🎯 SUMMARY

✅ **ALL SYMBOLS VERIFIED CORRECT FOR ALPACA**
✅ **Futures use forward slash: `/NQ`, `/ES`, etc.**
✅ **Crypto uses USD suffix: `BTCUSD`, `ETHUSD`**
✅ **Stocks/ETFs use standard symbols: `TSLA`, `GLD`, etc.**

**Your bots are now using the correct Alpaca symbols!** 🚀
