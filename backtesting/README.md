# 📊 BACKTESTING FRAMEWORK - FIBONACCI STRATEGY ANALYSIS

**Comprehensive Backtesting System for Fibonacci Retracement Trading Strategies**

## 📁 PROJECT STRUCTURE

```
backtesting/
├── 📖 README.md                     # This documentation
├── 🔒 .gitignore                    # Security exclusions
├── 🏗️ __init__.py                   # Python package initialization
│
├── 🧮 backtest.py                   # Core backtesting engine
├── 📈 metrics.py                    # Performance calculation utilities
│
├── 🧪 strategies/                   # Fibonacci Strategy Implementations
│   ├── fib_gold_backtest.py         # Main Fibonacci backtesting logic
│   ├── grok_strategy_test.py        # Grok-developed strategy testing
│   ├── strategy_hunt.py             # Automated strategy discovery
│   └── run_fib_*.py                 # Timeframe-specific run scripts
│
├── 📊 analysis/                     # Backtest Results & Analysis
│   ├── fib_best_setups.md          # Best performing setups
│   ├── fib_equity_breakdown.md     # Equity curve analysis
│   ├── fib_tuning_results.md       # Parameter optimization results
│   └── grok_results.md             # Grok strategy performance
│
└── 🛠️ utils/                        # Development & Data Tools
    ├── visualize_*.py              # Charting and visualization tools
    ├── download_*.py               # Data download utilities
    └── optimize.py                 # Parameter optimization framework
```

## 🎯 FRAMEWORK OVERVIEW

This backtesting framework was developed to systematically test and optimize Fibonacci retracement trading strategies across multiple:

- **Timeframes:** 5m, 15m, 30m, 1h, 4h, 1d
- **Assets:** BTC, ETH, stocks, futures
- **Swing Methods:** Local extrema, Zigzag, Fractal
- **Parameters:** Entry/exit retracements, stop losses, trend filters

## 🚀 QUICK START

### Run a Basic Backtest
```bash
# Test 5-minute BTC Fibonacci strategy
python strategies/run_fib_5m.py

# Test 1-hour strategy
python strategies/run_fib_1h.py

# Test Binance data
python strategies/run_fib_binance.py
```

### Visualize Results
```bash
# Plot equity curves
python utils/visualize_fib_swings.py

# Analyze breakout patterns
python utils/visualize_breakout.py
```

## 📊 CORE COMPONENTS

### 🧮 **backtest.py** - Main Engine
- VectorBT-powered backtesting framework
- Multi-asset support (stocks, crypto, futures)
- Performance metrics calculation
- Risk management integration

### 📈 **metrics.py** - Performance Analysis
- Sharpe ratio, Sortino ratio, Calmar ratio
- Maximum drawdown analysis
- Win/loss ratio calculations
- Risk-adjusted return metrics

### 🧪 **strategies/fib_gold_backtest.py** - Core Logic
- Fibonacci retracement calculations
- Multiple swing detection methods
- Trend filtering options
- Position sizing and risk management

## 🎯 STRATEGY VARIANTS

### Swing Detection Methods
- **Local Extrema:** Rolling window high/low detection
- **Zigzag:** Percentage-based trend reversal detection
- **Fractal:** Fractal dimension-based swing identification

### Timeframe Optimization
- **Scalping:** 5m, 15m, 30m (higher frequency, lower returns)
- **Swing:** 1h, 4h (balanced frequency/return)
- **Position:** 1d (lower frequency, higher quality signals)

## 📈 ANALYSIS RESULTS

### Key Findings (from analysis/ folder)
- **Best Timeframe:** 1h with fractal swing detection
- **Optimal Retracements:** Entry 0.618, Exit 0.236
- **Win Rate:** 35-45% across optimized setups
- **Risk/Reward:** 1:1.5 to 1:2.5 ratio

### Performance Summary
- **Total Strategies Tested:** 50+ parameter combinations
- **Best Setup:** 180.99% return on ETH 1h
- **Average Return:** 25-40% across winning strategies
- **Max Drawdown:** 20-45% (higher for better returns)

## 🔧 DEVELOPMENT WORKFLOW

### 1. Strategy Development
```bash
# Modify parameters in fib_gold_backtest.py
# Test with run_fib_*.py scripts
# Analyze results in analysis/*.md files
```

### 2. Parameter Optimization
```bash
# Use optimize.py for automated parameter tuning
# Compare results across timeframes/assets
# Document findings in analysis/ folder
```

### 3. Visualization & Analysis
```bash
# Generate equity curves with visualize_fib_swings.py
# Plot parameter heatmaps with visualize_breakout.py
# Analyze fractal performance with visualize_fractal_best.py
```

## 📊 DATA SOURCES

### Supported Brokers/Exchanges
- **Alpaca:** US stocks, ETFs, options
- **Binance:** Cryptocurrency markets
- **Interactive Brokers:** Futures, forex, global markets

### Data Download Utilities
```bash
# Download Binance historical data
python utils/download_binance_chunks.py

# Download IB data
python utils/download_ib_chunks.py
```

## 🎯 STRATEGY HUNTING

### Automated Discovery
```bash
# Run comprehensive strategy search
python strategies/strategy_hunt.py

# Tests multiple parameter combinations
# Outputs performance rankings
# Saves results to analysis/ folder
```

### Key Optimization Parameters
- **Swing Window:** 5-30 periods
- **Zigzag Deviation:** 0.5-3.0%
- **Entry Retracement:** 0.236-0.786
- **Exit Retracement:** 0.236-0.618
- **Stop Loss:** 0.5-1.0 (relative to entry)

## 📋 BEST PRACTICES

### Backtesting Guidelines
- **Walk-Forward Analysis:** Test on rolling windows
- **Out-of-Sample Testing:** Reserve data for validation
- **Transaction Costs:** Include fees in calculations
- **Slippage:** Account for real market conditions

### Performance Validation
- **Sharpe Ratio > 1.0:** Good risk-adjusted returns
- **Max Drawdown < 30%:** Reasonable risk tolerance
- **Win Rate > 35%:** Statistically significant
- **Profit Factor > 1.2:** Positive expectancy

## 🔗 INTEGRATION WITH GROK

This backtesting framework feeds into the **Grok live trading system**:

```
Backtesting Results → Strategy Selection → Live Bot Implementation
     ↓                     ↓                    ↓
fib_gold_backtest.py → grok/ folder → live_bots/ folder
```

The top-performing strategies from this backtesting framework were implemented as live trading bots in the `../grok/` directory.

## 📈 ADVANCED FEATURES

### Multi-Asset Backtesting
- Support for simultaneous testing across multiple assets
- Correlation analysis between strategies
- Portfolio-level risk management

### Parameter Heatmaps
- Visual optimization of strategy parameters
- Performance sensitivity analysis
- Optimal parameter range identification

### Walk-Forward Optimization
- Rolling window backtesting
- Forward-looking performance validation
- Overfitting prevention techniques

## 🐛 TROUBLESHOOTING

### Common Issues
- **Data Download Failures:** Check API credentials and rate limits
- **Memory Errors:** Reduce backtest window or increase RAM
- **Parameter Errors:** Validate input ranges in strategy files

### Performance Optimization
- **Large Datasets:** Use data chunking in download utilities
- **Parallel Processing:** Implement multiprocessing for large parameter sweeps
- **Caching:** Save intermediate results to avoid recomputation

---

**This backtesting framework powers the quantitative strategy development that resulted in 24+ winning strategies and 10 live trading bots.**

**See `../grok/` directory for the live implementation of these backtested strategies.**

---

**Framework Version: 2.0 | Last Updated: November 2025**
**Backtested Assets: BTC, ETH, SPY, QQQ, GLD, SLV, futures**
**Total Strategies Tested: 200+ parameter combinations**
