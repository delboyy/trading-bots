# 🤖 TRADING BOTS - COMPLETE QUANTITATIVE TRADING SYSTEM

**From Backtesting to Live Trading: A Professional Algorithmic Trading Framework**

## 📁 PROJECT OVERVIEW

This repository contains a complete quantitative trading system with two main components:

```
trading-bots/
├── 📊 backtesting/                 # Strategy Development & Testing
│   ├── strategies/                 # Fibonacci strategy implementations
│   ├── analysis/                   # Backtest results & optimization
│   ├── utils/                      # Data tools & visualization
│   └── README.md                   # Backtesting documentation
│
└── 🎯 grok/                        # Live Trading Implementation
    ├── live_bots/                  # 10 Production-ready trading bots
    ├── analysis/                   # Strategy performance analysis
    ├── strategies/                 # Strategy development files
    ├── utils/                      # Testing & utility scripts
    └── README.md                   # Live trading documentation
```

## 🎯 SYSTEM ARCHITECTURE

### Phase 1: Research & Development (`backtesting/`)
- **Quantitative Strategy Development**
- **Parameter Optimization**
- **Risk Management Testing**
- **Performance Validation**

### Phase 2: Live Implementation (`grok/`)
- **Production Trading Bots**
- **Real-time Execution**
- **Risk Management**
- **Performance Monitoring**

## 🚀 QUICK START

### For Strategy Development
```bash
cd backtesting
# Run Fibonacci backtest
python strategies/run_fib_1h.py
# Analyze results
cat analysis/fib_tuning_results.md
```

### For Live Trading
```bash
cd grok
# Verify setup
python live_bots/check_alpaca_setup.py
# Start a bot
python live_bots/live_gld_4h_mean_reversion.py &
```

## 📊 BACKTESTING FRAMEWORK

### Core Features
- ✅ **Multi-asset support** (stocks, crypto, futures)
- ✅ **Multiple timeframes** (5m to 1d)
- ✅ **Advanced swing detection** (local extrema, zigzag, fractal)
- ✅ **Parameter optimization**
- ✅ **Risk-adjusted performance metrics**

### Key Results
- **200+ parameter combinations tested**
- **24+ winning strategies identified**
- **Timeframes optimized:** 1h, 4h, 1d
- **Best performer:** ETH 1h (180.99% return)

## 🎯 LIVE TRADING SYSTEM

### Production Bots (10 total)
| Strategy | Asset | Timeframe | Return | Risk Level |
|----------|-------|-----------|--------|------------|
| ETH Volatility Breakout | ETH-USD | 1h | 180.99% | HIGH |
| SLV Mean Reversion | SLV | 4h | 69.91% | LOW |
| GLD Mean Reversion | GLD | 4h | 39.38% | VERY LOW |
| NVDA Volatility Breakout | NVDA | 1h | 109.06% | MODERATE |
| And 6 more... | | | | |

### Safety Features
- ✅ **Paper/Live trading support**
- ✅ **Real-time risk management**
- ✅ **Automated stop losses**
- ✅ **Drawdown protection**
- ✅ **Position size limits**

## 🛠️ TECHNICAL STACK

### Languages & Frameworks
- **Python 3.13** - Core implementation
- **VectorBT** - Backtesting engine
- **Alpaca API** - Live trading execution
- **Pandas/NumPy** - Data analysis
- **Plotly** - Visualization

### Data Sources
- **Alpaca** - US markets (paper/live)
- **Binance** - Cryptocurrency
- **Yahoo Finance** - Historical data
- **Interactive Brokers** - Futures/forex

## 📈 PERFORMANCE SUMMARY

### Backtested Results (2-year period)
- **Average Annual Return:** 40-60% across strategies
- **Win Rate:** 35-100% (varies by strategy)
- **Max Drawdown:** 5-41% (GLD safest at 4.7%)
- **Sharpe Ratio:** 0.49-1.68 (excellent risk-adjusted)

### Live Trading Considerations
- **Slippage:** 0.5-2% on live orders
- **Latency:** 50-200ms execution time
- **Market Hours:** Respect exchange schedules
- **Transaction Costs:** 0.1% Alpaca fees included

## 🎯 WORKFLOW

```
1. Strategy Research (backtesting/)
   ├── Parameter optimization
   ├── Risk analysis
   └── Performance validation

2. Strategy Selection
   ├── Top performers identified
   └── Risk-adjusted ranking

3. Live Implementation (grok/)
   ├── Bot development
   ├── Paper trading testing
   └── Live deployment
```

## 🔒 SECURITY & BEST PRACTICES

### Git Safety
- ✅ **Credentials excluded** (.gitignore protection)
- ✅ **Logs not committed** (sensitive data protection)
- ✅ **Clean repository** (only code and documentation)

### Trading Safety
- ✅ **Paper trading first** (risk-free testing)
- ✅ **Position size limits** (maximum exposure control)
- ✅ **Stop loss protection** (automatic loss prevention)
- ✅ **Drawdown limits** (emergency shutdown)

## 📚 DOCUMENTATION

### 📖 Complete Documentation
**All setup guides and instructions are in the [`docs/`](docs/) folder:**

- **[Documentation Index](docs/README.md)** - Complete guide navigation
- **[Setup Guide](docs/setup_guide.md)** - Initial VPS and system setup
- **[Dual Account Setup](docs/DUAL_ACCOUNT_SETUP.md)** - Run long-term and short-term bots separately
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Adding New Bots](docs/adding_new_bots.md)** - How to add new trading strategies
- **[Crypto Order Management](docs/crypto_order_management.md)** - Crypto bot order handling
- **[Alpaca Symbols Guide](docs/alpaca_symbols_guide.md)** - Supported symbols reference

### System Guides
- **[grok/README.md](grok/README.md)** - Live trading system overview
- **[grok/LIVE_BOTS_README.md](grok/LIVE_BOTS_README.md)** - Detailed bot setup
- **[backtesting/README.md](backtesting/README.md)** - Backtesting framework guide

## 🚨 IMPORTANT DISCLAIMERS

### Risk Warnings
- **Past Performance ≠ Future Results**
- **All Trading Involves Substantial Risk**
- **Paper Trading ≠ Live Trading**
- **No Guaranteed Profits**

### Educational Purpose
This system is provided for **educational and research purposes**. The strategies presented are the result of extensive backtesting but:

- Market conditions change
- Past performance doesn't guarantee future results
- Individual results will vary
- Professional advice recommended

## 🤝 CONTRIBUTING

### Development Guidelines
1. **Test thoroughly** on paper trading before live deployment
2. **Document changes** in strategy logic and parameters
3. **Include risk analysis** for any modifications
4. **Follow security practices** (no credentials in code)

### Extension Ideas
- Add new assets/markets
- Implement additional strategies
- Enhance risk management features
- Add portfolio-level optimization

## 📞 SUPPORT

### Getting Help
- **Documentation:** Check README files in each folder
- **Error Logs:** Review bot logs for troubleshooting
- **Setup Issues:** Run `check_alpaca_setup.py` for verification
- **Performance:** Monitor metrics in analysis reports

### Common Issues
- **API Credentials:** Ensure environment variables are set
- **Data Availability:** Check market hours and data permissions
- **Rate Limits:** Respect API call limits (200/minute on Alpaca)

---

## 🎉 CONCLUSION

**This repository represents a complete journey from quantitative research to live trading implementation:**

1. **Research Phase** - Extensive backtesting of Fibonacci strategies
2. **Optimization Phase** - Parameter tuning and risk analysis
3. **Implementation Phase** - Production-ready trading bots
4. **Safety Phase** - Risk management and monitoring systems

**Result: 24+ winning strategies and 10 live trading bots ready for paper or live deployment.**

---

**System Version: 2.0 | Last Updated: November 2025**
**Total Strategies Backtested: 200+ | Live Bots Created: 10**
**Programming Language: Python 3.13 | Backtesting Period: 2022-2024**
