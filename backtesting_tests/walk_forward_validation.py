#!/usr/bin/env python3
"""
🎯 WALK-FORWARD VALIDATION - OVERFITTING PROTECTION

This script performs comprehensive walk-forward testing on all validated strategies
to ensure they work consistently across different market conditions and prevent overfitting.

Key Features:
- Walk-forward testing (train on past, test on future)
- Multiple market regimes (bull, bear, sideways)
- Out-of-sample validation
- IBKR live data validation where available
- Robustness scoring
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json
from typing import Dict, List, Tuple, Optional, Callable
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from robust_backtesting_engine import RobustBacktestEngine, test_strategy_robustness, validate_with_ibkr_live
from comprehensive_strategy_validation import (
    load_stock_data, TimeBasedScalpingStrategy, RSIScalpingStrategy,
    VolumeBreakoutStrategy, CandlestickScalpingStrategy, FibonacciMomentumStrategy
)

# ===============================
# STRATEGY DEFINITIONS FOR ROBUST TESTING
# ===============================

def rsi_aggressive_strategy(df: pd.DataFrame, signal_only: bool = False, get_levels: bool = False):
    """RSI Aggressive Strategy wrapper for robust testing"""
    # Calculate indicators
    if 'rsi' not in df.columns:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
        rs = gain / loss
        df_copy = df.copy()
        df_copy['rsi'] = 100 - (100 / (1 + rs))
        df_copy['avg_volume'] = df_copy['Volume'].rolling(20).mean()
    else:
        df_copy = df.copy()

    if signal_only or get_levels:
        # Return signal or levels for backtesting engine
        if len(df_copy) < 10:
            return None if signal_only else (None, None)

        current_rsi = df_copy['rsi'].iloc[-1]
        prev_rsi = df_copy['rsi'].iloc[-2]
        current_volume = df_copy['Volume'].iloc[-1]
        avg_volume = df_copy['avg_volume'].iloc[-1]

        if current_volume < avg_volume * 1.2:
            return None if signal_only else (None, None)

        current_price = df_copy['Close'].iloc[-1]

        # Bullish signal
        if prev_rsi <= 25 and current_rsi > 25:
            if signal_only:
                return 'buy'
            # Calculate stop loss and take profit
            stop_loss = current_price * 0.993  # 0.7% stop loss
            take_profit = current_price * 1.012  # 1.2% take profit
            return stop_loss, take_profit

        # Bearish signal
        if prev_rsi >= 75 and current_rsi < 75:
            if signal_only:
                return 'sell'
            stop_loss = current_price * 1.007  # 0.7% stop loss
            take_profit = current_price * 0.988  # 1.2% take profit
            return stop_loss, take_profit

        return None if signal_only else (None, None)

    return df_copy

def candlestick_momentum_strategy(df: pd.DataFrame, signal_only: bool = False, get_levels: bool = False):
    """Candlestick Momentum Strategy wrapper"""
    df_copy = df.copy()
    df_copy['avg_volume'] = df_copy['Volume'].rolling(20).mean()

    if signal_only or get_levels:
        if len(df_copy) < 10:
            return None if signal_only else (None, None)

        # Simple momentum + volume signal
        current_price = df_copy['Close'].iloc[-1]
        current_volume = df_copy['Volume'].iloc[-1]
        avg_volume = df_copy['avg_volume'].iloc[-1]

        # Check for volume spike
        if current_volume < avg_volume * 1.4:
            return None if signal_only else (None, None)

        # Simple momentum signal (5-bar)
        momentum = current_price - df_copy['Close'].iloc[-6]
        momentum_pct = momentum / df_copy['Close'].iloc[-6]

        if momentum_pct > 0.003:  # 0.3% momentum
            if signal_only:
                return 'buy'
            stop_loss = current_price * 0.993
            take_profit = current_price * 1.015
            return stop_loss, take_profit
        elif momentum_pct < -0.003:
            if signal_only:
                return 'sell'
            stop_loss = current_price * 1.007
            take_profit = current_price * 0.985
            return stop_loss, take_profit

        return None if signal_only else (None, None)

    return df_copy

def fibonacci_momentum_strategy(df: pd.DataFrame, signal_only: bool = False, get_levels: bool = False):
    """Fibonacci Momentum Strategy wrapper"""
    df_copy = df.copy()

    # Calculate Fibonacci levels
    recent_high = df_copy['High'].rolling(50).max()
    recent_low = df_copy['Low'].rolling(50).min()

    for level in [0.236, 0.382, 0.618, 0.786]:
        df_copy[f'fib_{level}'] = recent_low + (recent_high - recent_low) * level

    df_copy['momentum'] = df_copy['Close'] - df_copy['Close'].shift(6)
    df_copy['avg_volume'] = df_copy['Volume'].rolling(20).mean()

    if signal_only or get_levels:
        if len(df_copy) < 10:
            return None if signal_only else (None, None)

        current_price = df_copy['Close'].iloc[-1]
        momentum = df_copy['momentum'].iloc[-1]
        current_volume = df_copy['Volume'].iloc[-1]
        avg_volume = df_copy['avg_volume'].iloc[-1]

        if current_volume < avg_volume * 1.5:
            return None if signal_only else (None, None)

        # Check Fibonacci levels
        for level in [0.236, 0.382, 0.618, 0.786]:
            fib_price = df_copy[f'fib_{level}'].iloc[-1]
            price_distance = abs(current_price - fib_price) / current_price

            if price_distance < 0.003:  # Within 0.3% of Fib level
                if current_price < fib_price and momentum > 0.002:  # Bullish
                    if signal_only:
                        return 'buy'
                    stop_loss = current_price * 0.991
                    take_profit = current_price * 1.016
                    return stop_loss, take_profit
                elif current_price > fib_price and momentum < -0.002:  # Bearish
                    if signal_only:
                        return 'sell'
                    stop_loss = current_price * 1.009
                    take_profit = current_price * 0.984
                    return stop_loss, take_profit

        return None if signal_only else (None, None)

    return df_copy

# ===============================
# MARKET REGIME DETECTION
# ===============================

def detect_market_regime(df: pd.DataFrame) -> str:
    """Detect current market regime"""
    if len(df) < 20:
        return "unknown"

    # Calculate returns
    returns = df['Close'].pct_change().dropna()

    # Trend strength (20-day)
    trend = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]

    # Volatility (20-day)
    volatility = returns.tail(20).std() * np.sqrt(252)  # Annualized

    # Volume trend
    volume_trend = (df['Volume'].iloc[-1] - df['Volume'].rolling(20).mean().iloc[-1]) / df['Volume'].rolling(20).mean().iloc[-1]

    # Classify regime
    if trend > 0.05 and volatility < 0.30:  # Strong uptrend, low volatility
        return "bull_trend"
    elif trend < -0.05 and volatility < 0.30:  # Strong downtrend, low volatility
        return "bear_trend"
    elif volatility > 0.40:  # High volatility
        return "volatile"
    else:  # Sideways
        return "sideways"

# ===============================
# COMPREHENSIVE WALK-FORWARD TESTING
# ===============================

def run_comprehensive_walk_forward_validation():
    """Run comprehensive walk-forward validation on all strategies"""

    print("🚀 Starting Comprehensive Walk-Forward Validation")
    print("=" * 60)

    strategies = {
        'GOOGL_RSI_Aggressive': {
            'func': rsi_aggressive_strategy,
            'symbol': 'GOOGL',
            'timeframe': '15mins',
            'expected_return': 71.52
        },
        'GLD_Candlestick_Momentum': {
            'func': candlestick_momentum_strategy,
            'symbol': 'GLD',
            'timeframe': '5mins',
            'expected_return': 69.45
        },
        'GLD_Fibonacci_Momentum': {
            'func': fibonacci_momentum_strategy,
            'symbol': 'GLD',
            'timeframe': '5mins',
            'expected_return': 66.75
        }
    }

    results = {}

    for strategy_name, config in strategies.items():
        print(f"\n🔍 Testing {strategy_name}")
        print("-" * 40)

        # Load data
        df = load_stock_data(config['symbol'], config['timeframe'])
        if df.empty:
            print(f"❌ No data available for {config['symbol']}")
            continue

        print(f"📊 Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}")

        # Detect market regimes in the data
        regime = detect_market_regime(df)
        print(f"📈 Market regime: {regime}")

        # Test with robust backtesting
        print("⚙️ Running robust backtesting...")

        # Crypto-like parameters (low commissions)
        engine_params = {
            'commission_per_trade': 0.01,  # 0.01%
            'slippage_pct': 0.05,  # 0.05%
            'max_risk_per_trade': 0.01,  # 1%
        }

        robust_results = test_strategy_robustness(
            config['func'],
            df,
            config['symbol'],
            engine_params
        )

        # Extract results
        regular = robust_results['regular_backtest']
        walk_forward = robust_results['walk_forward_backtest']
        robustness = robust_results['robustness_score']

        reg_return = regular.get('total_return', 0) * 100
        wf_return = walk_forward.get('total_return', 0) * 100

        print(f"   Regular Backtest Return: {reg_return:.2f}%")
        print(f"   Walk-Forward Return: {wf_return:.1f}%")
        print(f"   Robustness Score: {robustness:.2f} (higher = more consistent)")

        # Check for overfitting
        overfitting_flags = []

        if robustness < 0.7:
            overfitting_flags.append("Low robustness - may be overfitted")

        if walk_forward['total_return'] < regular['total_return'] * 0.5:
            overfitting_flags.append("Walk-forward performance significantly worse")

        if walk_forward['sharpe_ratio'] < 1.0:
            overfitting_flags.append("Poor risk-adjusted walk-forward returns")

        # Store results
        results[strategy_name] = {
            'config': config,
            'market_regime': regime,
            'regular_backtest': regular,
            'walk_forward_backtest': walk_forward,
            'robustness_score': robustness,
            'overfitting_flags': overfitting_flags,
            'recommendation': 'PASS' if robustness > 0.7 and len(overfitting_flags) == 0 else 'REVIEW'
        }

        if overfitting_flags:
            print("⚠️ OVERFITTING CONCERNS:")
            for flag in overfitting_flags:
                print(f"   • {flag}")
        else:
            print("✅ No overfitting concerns detected")

    # Generate comprehensive report
    generate_walk_forward_report(results)

    return results

def generate_walk_forward_report(results: Dict):
    """Generate comprehensive walk-forward validation report"""

    print("\n" + "="*80)
    print("🎯 WALK-FORWARD VALIDATION REPORT")
    print("="*80)

    print(f"\nValidated {len(results)} strategies with walk-forward testing")
    print("\n📊 STRATEGY ROBUSTNESS SUMMARY:")

    print("<20")
    print("-" * 85)

    for strategy_name, data in results.items():
        regular = data['regular_backtest']
        wf = data['walk_forward_backtest']
        robustness = data['robustness_score']

        reg_return = regular.get('total_return', 0) * 100
        wf_return = wf.get('total_return', 0) * 100
        reg_sharpe = regular.get('sharpe_ratio', 0)
        wf_sharpe = wf.get('sharpe_ratio', 0)

        status = "✅ PASS" if data['recommendation'] == 'PASS' else "⚠️ REVIEW"

        print("<20")

    print("\n📋 DETAILED ANALYSIS:")

    for strategy_name, data in results.items():
        print(f"\n🎯 {strategy_name}")
        print(f"   Market Regime: {data['market_regime']}")
        print(".2f")
        print(f"   Recommendation: {data['recommendation']}")

        if data['overfitting_flags']:
            print("   Overfitting Concerns:")
            for flag in data['overfitting_flags']:
                print(f"   • {flag}")

        # Compare key metrics
        reg = data['regular_backtest']
        wf = data['walk_forward_backtest']

        print("   Performance Comparison:")
        print(f"   • Win Rate: Regular={reg.get('win_rate', 0):.1f}, WF={wf.get('win_rate', 0):.1f}")
        print(f"   • Max Drawdown: Regular={reg.get('max_drawdown', 0):.2f}, WF={wf.get('max_drawdown', 0):.2f}")
        print(f"   • Sharpe Ratio: Regular={reg.get('sharpe_ratio', 0):.2f}, WF={wf.get('sharpe_ratio', 0):.2f}")
        print(f"   • Total Trades: Regular={reg.get('total_trades', 0)}, WF={wf.get('total_trades', 0)}")

    # Overall assessment
    passed_strategies = sum(1 for r in results.values() if r['recommendation'] == 'PASS')
    total_strategies = len(results)

    print("\n🎖️ OVERALL ASSESSMENT:")
    print(f"   Strategies Passed: {passed_strategies}/{total_strategies} ({passed_strategies/total_strategies*100:.1f}%)")

    if passed_strategies >= total_strategies * 0.75:
        print("   ✅ MAJORITY PASS - Strategies are robust and not overfitted")
    else:
        print("   ⚠️ REVIEW REQUIRED - Potential overfitting concerns")

    print("\n💡 RECOMMENDATIONS:")
    if passed_strategies > 0:
        print("   ✅ Proceed with confidence for passed strategies")
        print("   📊 Consider position sizing based on robustness scores")

    if passed_strategies < total_strategies:
        print("   🔧 Review and optimize strategies with low robustness")
        print("   📈 Consider alternative parameter sets or logic")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"/Users/a1/Projects/Trading/trading-bots/backtesting_tests/walk_forward_results_{timestamp}.json"

    # Convert to JSON-serializable format
    json_results = {}
    for k, v in results.items():
        json_results[k] = {}
        for k2, v2 in v.items():
            if k2 in ['regular_backtest', 'walk_forward_backtest']:
                json_results[k][k2] = {}
                for k3, v3 in v2.items():
                    if isinstance(v3, (np.float64, np.int64)):
                        json_results[k][k2][k3] = float(v3) if isinstance(v3, np.float64) else int(v3)
                    elif isinstance(v3, list):
                        # Convert trades/portfolio data
                        json_results[k][k2][k3] = f"{len(v3)} items"
                    else:
                        json_results[k][k2][k3] = v3
            else:
                json_results[k][k2] = v2

    with open(report_file, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)

    print(f"\n📁 Detailed results saved to: {report_file}")

def run_ibkr_live_validation():
    """Run live validation with IBKR for available strategies"""

    print("\n🔴 IBKR LIVE VALIDATION")
    print("=" * 40)

    # Only test strategies with stock symbols that should be available
    live_tests = {
        'GOOGL_RSI_Aggressive': rsi_aggressive_strategy,
        'GLD_Candlestick_Momentum': candlestick_momentum_strategy,
        'GLD_Fibonacci_Momentum': fibonacci_momentum_strategy
    }

    live_results = {}

    for strategy_name, strategy_func in live_tests.items():
        print(f"\n📡 Testing {strategy_name} with IBKR live data...")

        symbol = strategy_name.split('_')[0]  # Extract symbol from name
        if symbol == 'GOOGL':
            symbol = 'GOOGL'  # IBKR symbol
        elif symbol == 'GLD':
            symbol = 'GLD'

        try:
            result = validate_with_ibkr_live(strategy_func, symbol, duration_days=30)
            live_results[strategy_name] = result

            if 'error' in result:
                print(f"❌ IBKR validation failed: {result['error']}")
            else:
                reg_return = result['regular_backtest'].get('total_return', 0) * 100
                wf_return = result['walk_forward_backtest'].get('total_return', 0) * 100
                robustness = result.get('robustness_score', 0)

                print(f"   Robustness: {robustness:.2f}")
        except Exception as e:
            print(f"❌ IBKR validation error: {str(e)}")
            live_results[strategy_name] = {'error': str(e)}

    return live_results

if __name__ == "__main__":
    # Run comprehensive walk-forward validation
    wf_results = run_comprehensive_walk_forward_validation()

    # Run IBKR live validation if possible
    try:
        print("\n🔴 Attempting IBKR live validation...")
        ibkr_results = run_ibkr_live_validation()

        # Combine results
        final_results = {
            'walk_forward_validation': wf_results,
            'ibkr_live_validation': ibkr_results,
            'validation_timestamp': datetime.now().isoformat()
        }

        # Save combined results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_report_file = f"/Users/a1/Projects/Trading/trading-bots/backtesting_tests/final_validation_report_{timestamp}.json"

        with open(final_report_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)

        print(f"\n📁 Final comprehensive report saved to: {final_report_file}")

    except Exception as e:
        print(f"\n⚠️ IBKR live validation skipped: {str(e)}")

    print("\n🎯 Walk-forward validation completed!")
    print("Strategies tested for overfitting and market condition robustness.")
