# Backtesting Tests Folder

This folder contains all backtesting scripts, analysis tools, and results from strategy testing.

## 📁 File Organization

### Core Testing Scripts
- `advanced_scalping_test.py` - Tests advanced scalping strategies with multiple indicators
- `comprehensive_scalping_backtest.py` - Comprehensive multi-asset, multi-timeframe scalping tests
- `focused_scalping_test.py` - Focused testing of specific scalping combinations
- `simple_scalping_test.py` - Basic scalping strategy demonstration
- `quick_scalping_test.py` - Quick scalping tests for rapid iteration

### Analysis & Audit Scripts
- `strategy_audit.py` - Audits existing strategies for profitability
- `test_original_strategies.py` - Tests original Fibonacci and other legacy strategies
- `quick_audit.py` - Quick strategy performance audit
- `add_stop_logging.py` - Adds stop loss logging to strategies

### Data & Debugging
- `debug_yf.py` - Yahoo Finance data debugging and validation
- `paper_trading_plan.md` - Paper trading setup and risk management guidelines

## 📊 Results Files

### Scalping Results
- `advanced_scalping_results.csv` - Results from advanced scalping test runs
- `COMPREHENSIVE_ANALYSIS_REPORT.md` - Detailed analysis of all scalping strategy results

### Strategy Audit Results
- `strategy_audit_results.csv` - Results from strategy performance audits
- `original_strategies_audit.csv` - Audit results of original strategies

## 🚀 Quick Start

```bash
# Run comprehensive scalping backtest
python comprehensive_scalping_backtest.py

# Audit existing strategies
python strategy_audit.py

# Test specific scalping strategy
python focused_scalping_test.py
```

## 📈 Key Findings Summary

- **Advanced Scalping:** ❌ Complete failure (0 signals generated)
- **OBV Scalping:** ⚠️ Mixed results, QQQ 15m shows promise (+0.55%)
- **Candlestick Scalping:** 🔄 Needs optimization (39.9% avg win rate, -3.16% avg return)
- **Original Strategies:** ✅ Volatility Breakout and Momentum strategies perform well

## 🔧 Technical Notes

- Many tests failed due to broken pipe errors (need better error handling)
- 30m timeframe unavailable due to Yahoo Finance data limitations
- Focus on 5m/15m timeframes for scalping strategies
- Data is stored locally in `../data/processed/` folder

## 📋 Next Steps

1. **Fix Technical Issues:** Resolve broken pipe errors and data limitations
2. **Strategy Optimization:** Combine OBV + Candlestick patterns
3. **Risk Management:** Implement ATR-based stops and position sizing
4. **Live Testing:** Deploy promising strategies (OBV QQQ 15m, Candlestick SPY 15m)

