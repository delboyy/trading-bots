"""
Grok Strategy Finder - Find Winning Strategies Across Assets
Tests all available strategies on multiple assets to find profitable combinations.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.backtest import run_backtest


def test_strategy_on_asset(
    strategy_name: str,
    symbol: str,
    interval: str = "1h",
    strategy_params: Dict = None
) -> Dict:
    """Test a single strategy on a single asset and return results."""
    if strategy_params is None:
        strategy_params = {}

    try:
        pf = run_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            period="2y",  # 2 years of data
            interval=interval,
            strategy_params=strategy_params
        )

        stats = pf.stats()
        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "interval": interval,
            "params": strategy_params,
            "total_return": float(stats["Total Return [%]"]),
            "win_rate": float(stats.get("Win Rate [%]", 0)),
            "total_trades": int(stats["Total Trades"]),
            "profit_factor": float(stats.get("Profit Factor", 0)),
            "sharpe_ratio": float(stats.get("Sharpe Ratio", 0)),
            "max_drawdown": float(stats.get("Max Drawdown [%]", 0)),
            "success": True
        }
    except Exception as e:
        print(f"Error testing {strategy_name} on {symbol}: {e}")
        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "interval": interval,
            "params": strategy_params,
            "total_return": -999,
            "win_rate": 0,
            "total_trades": 0,
            "profit_factor": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "success": False,
            "error": str(e)
        }


def find_winning_strategies():
    """Test all strategies on multiple assets and find the winners."""

    # Define what to test
    strategies = [
        ("mean_reversion", {"window": 20, "z_thresh": 1.5}),
        ("mean_reversion", {"window": 20, "z_thresh": 2.0}),
        ("mean_reversion", {"window": 30, "z_thresh": 1.5}),
        ("momentum", {"fast": 10, "slow": 30}),
        ("momentum", {"fast": 5, "slow": 20}),
        ("momentum", {"fast": 20, "slow": 50}),
        ("breakout", {"window": 20}),
        ("breakout", {"window": 10}),
        ("breakout", {"window": 30}),
        ("volatility_breakout", {"atr_window": 14, "k": 1.5}),
        ("volatility_breakout", {"atr_window": 14, "k": 2.0}),
        ("volatility_breakout", {"atr_window": 21, "k": 1.5}),
    ]

    # Test on these assets
    assets = [
        ("BTC-USD", "1h"),   # Bitcoin hourly
        ("BTC-USD", "4h"),   # Bitcoin 4-hour
        ("ETH-USD", "1h"),   # Ethereum
        ("SPY", "1h"),       # S&P 500
        ("QQQ", "1h"),       # Nasdaq 100
        ("GLD", "1h"),       # Gold ETF
        ("SLV", "1h"),       # Silver ETF
        ("TSLA", "1h"),      # Tesla (volatile stock)
        ("AAPL", "1h"),      # Apple (stable stock)
        ("NVDA", "1h"),      # Nvidia (high growth)
    ]

    results = []

    print("=" * 80)
    print("GROK STRATEGY FINDER - TESTING ALL COMBINATIONS")
    print("=" * 80)
    print(f"Testing {len(strategies)} strategy variants × {len(assets)} assets = {len(strategies) * len(assets)} total tests")
    print("=" * 80)

    total_tests = len(strategies) * len(assets)
    current_test = 0

    for strategy_name, params in strategies:
        for symbol, interval in assets:
            current_test += 1
            print(f"[{current_test}/{total_tests}] Testing {strategy_name} on {symbol} ({interval})...")

            result = test_strategy_on_asset(strategy_name, symbol, interval, params)
            results.append(result)

            if result["success"]:
                return_pct = result["total_return"]
                win_rate = result["win_rate"]
                trades = result["total_trades"]
                print(f"  ✅ Success: {return_pct:.1f}% return, {win_rate:.1f}% win rate, {trades} trades")
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")

    return results


def analyze_results(results: List[Dict]) -> Dict:
    """Analyze the results and find the best performers."""

    # Filter successful tests
    successful = [r for r in results if r["success"] and r["total_trades"] > 10]  # Require minimum 10 trades

    if not successful:
        return {"error": "No successful strategy tests found"}

    # Sort by total return
    by_return = sorted(successful, key=lambda x: x["total_return"], reverse=True)

    # Sort by win rate
    by_win_rate = sorted(successful, key=lambda x: x["win_rate"], reverse=True)

    # Sort by Sharpe ratio (risk-adjusted)
    by_sharpe = sorted([r for r in successful if r["sharpe_ratio"] > -10],
                      key=lambda x: x["sharpe_ratio"], reverse=True)

    # Find strategies with positive returns
    profitable = [r for r in successful if r["total_return"] > 0]

    return {
        "total_tests": len(results),
        "successful_tests": len(successful),
        "profitable_strategies": len(profitable),
        "top_by_return": by_return[:10],
        "top_by_win_rate": by_win_rate[:10],
        "top_by_sharpe": by_sharpe[:10] if by_sharpe else [],
        "profitable_only": profitable,
        "best_overall": by_return[0] if by_return else None,
        "best_profitable": profitable[0] if profitable else None
    }


def print_analysis(analysis: Dict):
    """Print a comprehensive analysis of the results."""

    print("\n" + "=" * 80)
    print("STRATEGY FINDER RESULTS ANALYSIS")
    print("=" * 80)

    print(f"Total Tests Run: {analysis['total_tests']}")
    print(f"Successful Tests: {analysis['successful_tests']}")
    print(f"Profitable Strategies: {analysis['profitable_strategies']}")

    if analysis['profitable_strategies'] > 0:
        best = analysis['best_profitable']
        print("\n🏆 BEST PROFITABLE STRATEGY FOUND:")        print(f"  Strategy: {best['strategy']}")
        print(f"  Asset: {best['symbol']} ({best['interval']})")
        print(f"  Parameters: {best['params']}")
        print(".1f"        print(".1f"        print(f"  Trades: {best['total_trades']}")
        print(".1f"        print(".2f"
    if analysis['best_overall']:
        best = analysis['best_overall']
        print("\n📊 BEST OVERALL PERFORMANCE (including losses):")        print(f"  Strategy: {best['strategy']}")
        print(f"  Asset: {best['symbol']} ({best['interval']})")
        print(f"  Parameters: {best['params']}")
        print(".1f"        print(".1f"        print(f"  Trades: {best['total_trades']}")

    print("\n📈 TOP 5 PROFITABLE STRATEGIES:")    profitable = analysis['profitable_only']
    if profitable:
        for i, result in enumerate(profitable[:5], 1):
            print(f"  {i}. {result['strategy']} on {result['symbol']} ({result['interval']}): {result['total_return']:.1f}% return, {result['win_rate']:.1f}% win rate")
    else:
        print("  ❌ No profitable strategies found!")

    print("\n📊 TOP 5 BY WIN RATE:")    for i, result in enumerate(analysis['top_by_win_rate'][:5], 1):
        print(f"  {i}. {result['strategy']} on {result['symbol']} ({result['interval']}): {result['win_rate']:.1f}% win rate, {result['total_return']:.1f}% return")

    if analysis['top_by_sharpe']:
        print("\n🎯 TOP 5 BY SHARPE RATIO (risk-adjusted):")        for i, result in enumerate(analysis['top_by_sharpe'][:5], 1):
            print(f"  {i}. {result['strategy']} on {result['symbol']} ({result['interval']}): Sharpe {result['sharpe_ratio']:.2f}, Return {result['total_return']:.1f}%")


if __name__ == "__main__":
    # Run the comprehensive strategy search
    results = find_winning_strategies()

    # Analyze the results
    analysis = analyze_results(results)

    # Print the analysis
    print_analysis(analysis)

    # Save detailed results
    import json
    with open("grok/strategy_finder_results.json", "w") as f:
        json.dump({
            "analysis": analysis,
            "all_results": results
        }, f, indent=2, default=str)

    print("\n💾 Detailed results saved to: grok/strategy_finder_results.json")
    print("=" * 80)
