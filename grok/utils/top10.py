"""
TOP 10 STRATEGIES - Balanced Risk/Reward Selection
Comprehensive analysis of the best 10 strategies with optimal balance of returns vs drawdown
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Ensure project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.backtest import run_backtest


def analyze_strategy_detailed(strategy_name: str, symbol: str, timeframe: str,
                            strategy_params: Dict[str, Any]) -> Dict[str, Any]:
    """Run detailed analysis on a strategy and return comprehensive metrics"""

    try:
        pf = run_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            interval=timeframe,
            strategy_params=strategy_params
        )

        stats = pf.stats()

        # Basic metrics
        total_return = stats['Total Return [%]']
        win_rate = stats.get('Win Rate [%]', 0)
        total_trades = stats['Total Trades']
        max_dd = stats.get('Max Drawdown [%]', 0)

        # Calculate additional metrics
        trades_df = pf.trades
        if not trades_df.empty:
            wins = trades_df[trades_df['ReturnPct'] > 0]
            losses = trades_df[trades_df['ReturnPct'] <= 0]

            avg_win = wins['ReturnPct'].mean() if not wins.empty else 0
            avg_loss = losses['ReturnPct'].mean() if not losses.empty else 0
            num_wins = len(wins)
            num_losses = len(losses)

            # Profit factor
            total_win_amount = wins['PnL'].sum() if not wins.empty else 0
            total_loss_amount = abs(losses['PnL'].sum()) if not losses.empty else 0
            profit_factor = total_win_amount / total_loss_amount if total_loss_amount > 0 else float('inf')

            # Sharpe ratio (if available)
            sharpe = stats.get('Sharpe Ratio', 0)

            # Sortino ratio (if available)
            sortino = stats.get('Sortino Ratio', 0)

            # Calmar ratio (return / max drawdown)
            calmar = total_return / abs(max_dd) if max_dd != 0 else float('inf')

            # Equity curve data
            equity_curve = pf.value().values
            equity_curve_pct = ((equity_curve - equity_curve[0]) / equity_curve[0]) * 100

            return {
                'success': True,
                'total_return': total_return,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'max_drawdown': max_dd,
                'num_wins': num_wins,
                'num_losses': num_losses,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'calmar_ratio': calmar,
                'equity_curve': equity_curve_pct.tolist(),
                'trades_df': trades_df.to_dict('records') if len(trades_df) <= 20 else trades_df.head(20).to_dict('records'),
                'strategy_name': strategy_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'params': strategy_params
            }
        else:
            return {'success': False, 'error': 'No trades generated'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_top10_report():
    """Create comprehensive report for top 10 strategies"""

    # TOP 10 SELECTION - Balanced Risk/Reward
    top10_strategies = [
        {
            'name': 'ETH 1h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'ETH-USD',
            'timeframe': '1h',
            'params': {'atr_window': 14, 'k': 2.0},
            'description': 'ABSOLUTE CHAMPION - Highest return with manageable drawdown',
            'risk_level': 'HIGH',
            'return_expectation': 'VERY HIGH'
        },
        {
            'name': 'SLV 4h Mean Reversion',
            'strategy': 'mean_reversion',
            'symbol': 'SLV',
            'timeframe': '4h',
            'params': {'window': 30, 'z_thresh': 1.5},
            'description': 'PERFECT BALANCE - 70% return, 9.3% drawdown, 91.7% win rate',
            'risk_level': 'LOW',
            'return_expectation': 'HIGH'
        },
        {
            'name': 'GLD 4h Mean Reversion',
            'strategy': 'mean_reversion',
            'symbol': 'GLD',
            'timeframe': '4h',
            'params': {'window': 30, 'z_thresh': 1.5},
            'description': 'LOWEST RISK - 39% return, 4.7% drawdown, 100% win rate',
            'risk_level': 'VERY LOW',
            'return_expectation': 'MODERATE'
        },
        {
            'name': 'NVDA 1h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'NVDA',
            'timeframe': '1h',
            'params': {'atr_window': 14, 'k': 1.5},
            'description': 'TECH LEADER - 109% return with reasonable 32% drawdown',
            'risk_level': 'MODERATE',
            'return_expectation': 'HIGH'
        },
        {
            'name': 'ETH 4h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'ETH-USD',
            'timeframe': '4h',
            'params': {'atr_window': 14, 'k': 2.0},
            'description': 'CONSERVATIVE ETH - 148% return with lower 35% drawdown than 1h',
            'risk_level': 'HIGH',
            'return_expectation': 'VERY HIGH'
        },
        {
            'name': 'TSLA 4h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'TSLA',
            'timeframe': '4h',
            'params': {'atr_window': 14, 'k': 1.5},
            'description': 'STOCK CHAMPION - 59% return, 27% drawdown, 53% win rate',
            'risk_level': 'MODERATE',
            'return_expectation': 'HIGH'
        },
        {
            'name': 'NQ 4h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'NQ=F',
            'timeframe': '4h',
            'params': {'atr_window': 14, 'k': 1.5},
            'description': 'FUTURES WINNER - 33% return, 26% drawdown, 60% win rate',
            'risk_level': 'MODERATE',
            'return_expectation': 'MODERATE'
        },
        {
            'name': 'BTC 1h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'BTC-USD',
            'timeframe': '1h',
            'params': {'atr_window': 14, 'k': 2.0},
            'description': 'CRYPTO STEADY - 45% return, 29% drawdown, 45% win rate',
            'risk_level': 'MODERATE',
            'return_expectation': 'MODERATE'
        },
        {
            'name': 'META 1h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'META',
            'timeframe': '1h',
            'params': {'atr_window': 14, 'k': 1.5},
            'description': 'SOCIAL MEDIA - 29% return, 29% drawdown, 51% win rate',
            'risk_level': 'MODERATE',
            'return_expectation': 'MODERATE'
        },
        {
            'name': 'XLK 1h Volatility Breakout',
            'strategy': 'volatility_breakout',
            'symbol': 'XLK',
            'timeframe': '1h',
            'params': {'atr_window': 14, 'k': 1.5},
            'description': 'TECH SECTOR - 24% return, 22% drawdown, 48% win rate',
            'risk_level': 'LOW',
            'return_expectation': 'MODERATE'
        }
    ]

    print("=" * 120)
    print("🎯 TOP 10 STRATEGIES - BALANCED RISK/REWARD ANALYSIS")
    print("=" * 120)
    print(f"Analyzing {len(top10_strategies)} elite strategies with optimal return/drawdown balance")
    print("=" * 120)

    detailed_results = []

    for i, strategy in enumerate(top10_strategies, 1):
        print(f"\n{i}. Analyzing {strategy['name']}...")

        result = analyze_strategy_detailed(
            strategy['strategy'],
            strategy['symbol'],
            strategy['timeframe'],
            strategy['params']
        )

        if result['success']:
            result.update({
                'rank': i,
                'description': strategy['description'],
                'risk_level': strategy['risk_level'],
                'return_expectation': strategy['return_expectation']
            })
            detailed_results.append(result)

            # Print summary
            print(f"   ✅ Return: {result['total_return']:.1f}% | Win Rate: {result['win_rate']:.1f}% | Max DD: {result['max_drawdown']:.1f}%")
            print(f"   📊 Trades: {result['total_trades']} | Wins: {result['num_wins']} | Losses: {result['num_losses']}")
            print(f"   💰 Avg Win: {result['avg_win']:.2f}% | Avg Loss: {result['avg_loss']:.2f}%")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")

    return detailed_results


def generate_strategy_logic(strategy_name: str, params: Dict[str, Any]) -> str:
    """Generate detailed entry/exit logic for a strategy"""

    if strategy_name == 'volatility_breakout':
        atr_window = params.get('atr_window', 14)
        k = params.get('k', 2.0)

        logic = f"""
# VOLATILITY BREAKOUT STRATEGY LOGIC
# Parameters: ATR Window = {atr_window}, K Multiplier = {k}

## ENTRY LOGIC:
1. Calculate ATR over {atr_window} periods
2. Create upper band: Previous Close + ({k} × ATR)
3. Create lower band: Previous Close - ({k} × ATR)
4. LONG ENTRY: When current close price BREAKS ABOVE upper band
5. SHORT ENTRY: When current close price BREAKS BELOW lower band

## EXIT LOGIC:
- No specific exit conditions (relies on next opposite signal)
- Position held until opposite signal occurs
- Can be closed at market close if desired (end-of-day exit)

## RISK MANAGEMENT:
- Max drawdown typically 25-40%
- Position sizing: 1-2% per trade recommended
- Stop loss: Consider 2×ATR below entry for longs, above for shorts

## PSEUDO CODE:
```python
def generate_signals(df, atr_window={atr_window}, k={k}):
    # Calculate ATR
    atr = calculate_atr(df, atr_window)

    # Create bands
    df['upper_band'] = df['Close'].shift(1) + (k * atr)
    df['lower_band'] = df['Close'].shift(1) - (k * atr)

    # Generate signals
    signals = pd.Series(0, index=df.index)
    signals[df['Close'] > df['upper_band']] = 1   # Long breakout
    signals[df['Close'] < df['lower_band']] = -1  # Short breakout

    return signals
```
"""
        return logic

    elif strategy_name == 'mean_reversion':
        window = params.get('window', 30)
        z_thresh = params.get('z_thresh', 1.5)

        logic = f"""
# MEAN REVERSION STRATEGY LOGIC
# Parameters: Rolling Window = {window}, Z-Score Threshold = {z_thresh}

## ENTRY LOGIC:
1. Calculate rolling mean and standard deviation over {window} periods
2. Calculate z-score: (price - rolling_mean) / rolling_std
3. LONG ENTRY: When z-score < -{z_thresh} (price is oversold)
4. SHORT ENTRY: When z-score > +{z_thresh} (price is overbought)

## EXIT LOGIC:
- Exit when z-score crosses back to zero (returns to mean)
- No specific profit targets (relies on mean reversion)
- Can be closed at market close if desired

## RISK MANAGEMENT:
- Max drawdown typically 5-15% (much lower than momentum strategies)
- Position sizing: 2-5% per trade (higher due to lower volatility)
- Stop loss: Consider 2×rolling_std below/above entry

## PSEUDO CODE:
```python
def generate_signals(df, window={window}, z_thresh={z_thresh}):
    # Calculate rolling statistics
    df['rolling_mean'] = df['Close'].rolling(window).mean()
    df['rolling_std'] = df['Close'].rolling(window).std()

    # Calculate z-score
    df['z_score'] = (df['Close'] - df['rolling_mean']) / df['rolling_std']

    # Generate signals
    signals = pd.Series(0, index=df.index)
    signals[df['z_score'] < -z_thresh] = 1   # Buy oversold
    signals[df['z_score'] > z_thresh] = -1  # Sell overbought

    return signals
```
"""
        return logic


def create_comprehensive_report(results: List[Dict[str, Any]]):
    """Create the final comprehensive report"""

    report = f"""
# 🎯 TOP 10 STRATEGIES - COMPREHENSIVE ANALYSIS

**Selection Criteria:** Optimal balance of high returns with reasonable drawdown risk
**Backtest Period:** 2 years (2022-2024) | **Initial Capital:** $100,000 | **Fees:** 0.1%

## 📊 OVERVIEW

| Rank | Strategy | Asset | Return | Win Rate | Max DD | Risk Level | Return Expectation |
|------|----------|-------|--------|----------|--------|------------|-------------------|
"""

    for result in results:
        report += f"| {result['rank']} | {result['strategy_name']} | {result['symbol']} | {result['total_return']:.1f}% | {result['win_rate']:.1f}% | {result['max_drawdown']:.1f}% | {result['risk_level']} | {result['return_expectation']} |\n"

    report += """

## 📈 DETAILED ANALYSIS BY STRATEGY

"""

    for result in results:
        report += f"""
### {result['rank']}. {result['strategy_name']} on {result['symbol']} ({result['timeframe']})
**{result['description']}**

#### 📊 PERFORMANCE METRICS
- **Total Return:** {result['total_return']:.2f}%
- **Win Rate:** {result['win_rate']:.1f}%
- **Total Trades:** {result['total_trades']}
- **Max Drawdown:** {result['max_drawdown']:.2f}%
- **Profit Factor:** {result['profit_factor']:.2f}
- **Sharpe Ratio:** {result['sharpe_ratio']:.2f}
- **Calmar Ratio:** {result['calmar_ratio']:.2f}

#### 🎯 TRADE ANALYSIS
- **Winning Trades:** {result['num_wins']}
- **Losing Trades:** {result['num_losses']}
- **Average Win:** {result['avg_win']:.2f}%
- **Average Loss:** {result['avg_loss']:.2f}%
- **Largest Win:** {max([t['ReturnPct'] for t in result['trades_df']]) if result['trades_df'] else 0:.2f}%
- **Largest Loss:** {min([t['ReturnPct'] for t in result['trades_df']]) if result['trades_df'] else 0:.2f}%

#### 📈 EQUITY CURVE
```
Equity growth over time (percentage):
{', '.join([f'{x:.1f}%' for x in result['equity_curve'][:10]])}{'...' if len(result['equity_curve']) > 10 else ''}
```

#### 📋 STRATEGY PARAMETERS
```python
{result['params']}
```

#### 🤖 ENTRY & EXIT LOGIC
{generate_strategy_logic(result['strategy_name'], result['params'])}

#### 💼 RISK ASSESSMENT
- **Risk Level:** {result['risk_level']}
- **Recommended Position Size:** {'1-2%' if result['risk_level'] == 'HIGH' else '2-3%' if result['risk_level'] == 'MODERATE' else '3-5%'}
- **Monitoring Frequency:** {'Daily' if '1h' in result['timeframe'] or '4h' in result['timeframe'] else 'Weekly'}
- **Rebalancing:** {'Monthly' if result['max_drawdown'] < 20 else 'Quarterly'}

---
"""

    report += """
## 🎯 PORTFOLIO RECOMMENDATIONS

### 🏆 **CHAMPION PORTFOLIO** (Balanced Risk)
```
SLV 4h Mean Reversion:    30% (Low risk, high win rate)
ETH 1h Volatility Breakout: 25% (High return potential)
GLD 4h Mean Reversion:    20% (Ultra-low risk, perfect win rate)
NVDA 1h Volatility Breakout: 15% (Tech growth)
NQ 4h Volatility Breakout: 10% (Diversification)
```

### 🛡️ **CONSERVATIVE PORTFOLIO** (Lower Risk)
```
GLD 4h Mean Reversion:    40% (Perfect win rate, lowest DD)
SLV 4h Mean Reversion:    30% (Near-perfect win rate)
XLK 1h Volatility Breakout: 15% (Moderate returns, low DD)
META 1h Volatility Breakout: 10% (Stable tech stock)
NQ 4h Volatility Breakout:  5% (Futures diversification)
```

### 🚀 **GROWTH PORTFOLIO** (Higher Risk/Reward)
```
ETH 1h Volatility Breakout: 35% (Champion strategy)
ETH 4h Volatility Breakout: 25% (Conservative ETH)
NVDA 1h Volatility Breakout: 20% (Tech momentum)
TSLA 4h Volatility Breakout: 15% (EV growth)
BTC 1h Volatility Breakout:  5% (Crypto diversification)
```

## 💡 IMPLEMENTATION GUIDELINES

### 📊 **Risk Management**
- **Max Portfolio Drawdown:** 15-20% stop-loss
- **Position Sizing:** Based on individual strategy risk levels
- **Diversification:** Minimum 3-5 strategies
- **Rebalancing:** Monthly or when drawdown exceeds 10%

### ⏰ **Monitoring Schedule**
- **Hourly Strategies (1h/4h):** Check daily during market hours
- **Daily Strategies:** Review weekly
- **Portfolio:** Monitor daily, rebalance monthly

### 🎛️ **Parameter Tuning**
- **Conservative:** Reduce position sizes by 20-30%
- **Aggressive:** Increase position sizes by 20-30%
- **Market Conditions:** Reduce sizing during high volatility

---

**Generated by Grok Strategy Analysis Engine**
**Comprehensive quantitative analysis across all major asset classes and timeframes**
"""

    return report


if __name__ == "__main__":
    # Run comprehensive analysis
    results = create_top10_report()

    if results:
        # Generate comprehensive report
        report = create_comprehensive_report(results)

        # Save to file
        with open("grok/TOP10_COMPREHENSIVE_REPORT.md", "w") as f:
            f.write(report)

        print("\n💾 Comprehensive report saved to: grok/TOP10_COMPREHENSIVE_REPORT.md")
        print(f"\n🎯 SUMMARY: Analyzed {len(results)} elite strategies")
        print(f"   📈 Average Return: {sum(r['total_return'] for r in results)/len(results):.1f}%")
        print(f"   📊 Average Win Rate: {sum(r['win_rate'] for r in results)/len(results):.1f}%")
        print(f"   🛡️  Average Max DD: {sum(r['max_drawdown'] for r in results)/len(results):.1f}%")
        print(f"   💰 Best Strategy: {max(results, key=lambda x: x['total_return'])['strategy_name']} ({max(results, key=lambda x: x['total_return'])['total_return']:.1f}% return)")
        print(f"   🛡️  Safest Strategy: {min(results, key=lambda x: x['max_drawdown'])['strategy_name']} ({min(results, key=lambda x: x['max_drawdown'])['max_drawdown']:.1f}% drawdown)")

    print("\n" + "=" * 120)
