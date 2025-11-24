# 📄 Paper Trading Plan: The "Grok" Portfolio

## 🚀 Objective
Launch **8 Parallel Bots** to validate the winning strategies from our massive stress test. Run for 1 week on a paper trading account.

## 🤖 Bot Configuration List

### Group A: The "Daily Trend" Bots (High Quality)
*These bots trade on the Daily (1d) timeframe. Expect few trades but high accuracy.*

1.  **ETH Trend King**
    *   **Symbol**: `ETH-USD`
    *   **Timeframe**: `1d`
    *   **Strategy**: Volatility Breakout (`k=2.0`, `atr=14`)
    *   **Expected Win Rate**: 100% (Historical)

2.  **NVDA AI Trend**
    *   **Symbol**: `NVDA`
    *   **Timeframe**: `1d`
    *   **Strategy**: Volatility Breakout (`k=1.5`, `atr=14`)
    *   **Expected Return**: >140% annualized

### Group B: The "Crypto Degen" Bots (High Growth)
*These bots trade on the Hourly (1h) timeframe. Expect high volatility and massive returns.*

3.  **DOGE Moon Bot**
    *   **Symbol**: `DOGE-USD`
    *   **Timeframe**: `1h`
    *   **Strategy**: Volatility Breakout (`k=2.0`, `atr=14`)
    *   **Target**: Catch the next meme pump.

4.  **SOL Speed Bot**
    *   **Symbol**: `SOL-USD`
    *   **Timeframe**: `1h`
    *   **Strategy**: Volatility Breakout (`k=2.0`, `atr=14`)
    *   **Target**: High beta crypto plays.

### Group C: The "Commodity Swing" Bots (Diversification)
*These bots trade Mean Reversion. They buy dips and sell rips.*

5.  **Oil Baron (4h)**
    *   **Symbol**: `CL=F` (Crude Oil)
    *   **Timeframe**: `4h`
    *   **Strategy**: Mean Reversion (`window=30`, `z=1.5`)
    *   **Logic**: Fade extreme moves.

6.  **Gold Standard (4h)**
    *   **Symbol**: `GC=F` (Gold)
    *   **Timeframe**: `4h`
    *   **Strategy**: Mean Reversion (`window=30`, `z=1.5`)
    *   **Logic**: Safe haven accumulation.

7.  **Silver Surfer (Daily)**
    *   **Symbol**: `SI=F` (Silver)
    *   **Timeframe**: `1d`
    *   **Strategy**: Mean Reversion (`window=30`, `z=1.5`)
    *   **Logic**: 100% historical win rate on daily.

### Group D: The Experimental Scalper
*High frequency test.*

8.  **Silver Scalper (30m)**
    *   **Symbol**: `SI=F` (Silver)
    *   **Timeframe**: `30m`
    *   **Strategy**: Mean Reversion (`window=20`, `z=2.0`)
    *   **Logic**: Quick mean reversion scalps.

### Group E: The "Originals" (Verified Scalpers & Swings)
*Strategies confirmed by recent stress test (Last 60d).*

9.  **ETH Scalper (5m)**
    *   **Symbol**: `ETH-USD`
    *   **Timeframe**: `5m`
    *   **Strategy**: Fib Zigzag (`dev=2%`)
    *   **Expected Win Rate**: >90% (Recent)

10. **BTC Scalper (5m)**
    *   **Symbol**: `BTC-USD`
    *   **Timeframe**: `5m`
    *   **Strategy**: Fib Zigzag (`dev=2%`)
    *   **Expected Win Rate**: >85% (Recent)

11. **TSLA Swing (4h)**
    *   **Symbol**: `TSLA`
    *   **Timeframe**: `4h`
    *   **Strategy**: Fib Local Extrema (`window=5`)
    *   **Expected Return**: >18% (Recent)

## 🛠️ Setup Instructions
1.  **Capital Allocation**: Allocate $10,000 virtual capital per bot ($80,000 total).
2.  **Risk Management**:
    *   **Crypto**: 2% Risk per trade.
    *   **Stocks/Commodities**: 1% Risk per trade.
3.  **Monitoring**: Check bots once daily at market close.
