"""
Grok Timeframe & Asset Class Tester
Tests winning strategies across different timeframes and asset classes
"""

import sys
import os
from pathlib import Path
from typing import Dict, List

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backtesting.backtest import run_backtest


def test_strategy_matrix():
    """Test winning strategies across multiple timeframes and asset classes"""

    # Define winning strategies and their best parameters
    winning_strategies = [
        ("volatility_breakout", {"atr_window": 14, "k": 2.0}, "ETH Volatility Breakout"),
        ("volatility_breakout", {"atr_window": 14, "k": 1.5}, "ETH Conservative VB"),
        ("volatility_breakout", {"atr_window": 14, "k": 2.0}, "BTC Volatility Breakout"),
        ("mean_reversion", {"window": 30, "z_thresh": 1.5}, "GLD Mean Reversion"),
        ("mean_reversion", {"window": 20, "z_thresh": 1.5}, "SLV Mean Reversion"),
    ]

    # Define test matrix: (symbol, timeframe, asset_class)
    test_matrix = [
        # Crypto
        ("BTC-USD", "1h", "Crypto"),
        ("BTC-USD", "4h", "Crypto"),
        ("BTC-USD", "1d", "Crypto"),
        ("ETH-USD", "1h", "Crypto"),
        ("ETH-USD", "4h", "Crypto"),
        ("ETH-USD", "1d", "Crypto"),
        ("ADA-USD", "1h", "Crypto"),
        ("SOL-USD", "1h", "Crypto"),

        # Stocks - Tech
        ("AAPL", "1h", "Stocks-Tech"),
        ("AAPL", "1d", "Stocks-Tech"),
        ("MSFT", "1h", "Stocks-Tech"),
        ("NVDA", "1h", "Stocks-Tech"),
        ("TSLA", "1h", "Stocks-Tech"),

        # Stocks - Indices
        ("SPY", "1h", "Stocks-Index"),
        ("SPY", "1d", "Stocks-Index"),
        ("QQQ", "1h", "Stocks-Index"),
        ("IWM", "1h", "Stocks-Index"),

        # Commodities
        ("GLD", "1h", "Commodities"),
        ("GLD", "1d", "Commodities"),
        ("SLV", "1h", "Commodities"),
        ("USO", "1h", "Commodities"),  # Oil ETF
        ("UNG", "1h", "Commodities"),  # Natural Gas ETF

        # Bonds/Currencies (if available)
        ("TLT", "1h", "Bonds"),  # Treasury Bonds
        ("EURUSD=X", "1h", "Forex"),
        ("GBPUSD=X", "1h", "Forex"),
    ]

    results = []

    print("=" * 100)
    print("GROK TIMEFRAME & ASSET CLASS MATRIX TESTER")
    print("=" * 100)
    print(f"Testing {len(winning_strategies)} winning strategies × {len(test_matrix)} asset/timeframe combos = {len(winning_strategies) * len(test_matrix)} total tests")
    print("=" * 100)

    total_tests = len(winning_strategies) * len(test_matrix)
    current_test = 0

    for strategy_name, params, strategy_desc in winning_strategies:
        print(f"\n🔬 TESTING STRATEGY: {strategy_desc}")
        print("-" * 60)

        for symbol, timeframe, asset_class in test_matrix:
            current_test += 1
            test_id = f"{strategy_desc[:15]} on {symbol} ({timeframe})"

            print(f"[{current_test:3d}/{total_tests}] {test_id}...")

            try:
                pf = run_backtest(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    interval=timeframe,
                    strategy_params=params
                )

                stats = pf.stats()
                ret = stats['Total Return [%]']
                win_rate = stats.get('Win Rate [%]', 0)
                trades = stats['Total Trades']
                sharpe = stats.get('Sharpe Ratio', 0)
                max_dd = stats.get('Max Drawdown [%]', 0)

                # Only record results with minimum activity
                if trades >= 5:  # Require at least 5 trades
                    result = {
                        "strategy": strategy_name,
                        "strategy_desc": strategy_desc,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "asset_class": asset_class,
                        "params": params,
                        "total_return": float(ret),
                        "win_rate": float(win_rate),
                        "total_trades": int(trades),
                        "sharpe_ratio": float(sharpe),
                        "max_drawdown": float(max_dd),
                        "success": True
                    }
                    results.append(result)

                    # Show results inline
                    status = "🏆 WINNER" if ret > 0 else "⚠️  BREAK-EVEN/LOSS"
                    print(".1f"                else:
                    print(f"  ❌ Skipped: Only {trades} trades (need ≥5)")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results.append({
                    "strategy": strategy_name,
                    "strategy_desc": strategy_desc,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "asset_class": asset_class,
                    "params": params,
                    "error": str(e),
                    "success": False
                })

    return results


def analyze_matrix_results(results: List[Dict]):
    """Analyze results across timeframes and asset classes"""

    successful = [r for r in results if r.get("success", False)]

    if not successful:
        return {"error": "No successful tests"}

    # Group by strategy and asset class
    strategy_asset_performance = {}
    timeframe_performance = {}
    asset_class_performance = {}

    for result in successful:
        strategy = result["strategy_desc"]
        asset_class = result["asset_class"]
        timeframe = result["timeframe"]
        ret = result["total_return"]

        # Strategy by asset class
        key = f"{strategy} × {asset_class}"
        if key not in strategy_asset_performance:
            strategy_asset_performance[key] = []
        strategy_asset_performance[key].append(ret)

        # Timeframe performance
        if timeframe not in timeframe_performance:
            timeframe_performance[timeframe] = []
        timeframe_performance[timeframe].append(ret)

        # Asset class performance
        if asset_class not in asset_class_performance:
            asset_class_performance[asset_class] = []
        asset_class_performance[asset_class].append(ret)

    # Calculate averages
    strategy_asset_avg = {k: sum(v)/len(v) for k, v in strategy_asset_performance.items()}
    timeframe_avg = {k: sum(v)/len(v) for k, v in timeframe_performance.items()}
    asset_class_avg = {k: sum(v)/len(v) for k, v in asset_class_performance.items()}

    # Find winners (positive returns)
    winners = [r for r in successful if r["total_return"] > 0]
    winners_by_asset_class = {}
    for winner in winners:
        asset_class = winner["asset_class"]
        if asset_class not in winners_by_asset_class:
            winners_by_asset_class[asset_class] = 0
        winners_by_asset_class[asset_class] += 1

    return {
        "total_tests": len(results),
        "successful_tests": len(successful),
        "winning_tests": len(winners),
        "win_rate": len(winners) / len(successful) * 100 if successful else 0,
        "strategy_asset_avg": strategy_asset_avg,
        "timeframe_avg": timeframe_avg,
        "asset_class_avg": asset_class_avg,
        "winners_by_asset_class": winners_by_asset_class,
        "top_performers": sorted(winners, key=lambda x: x["total_return"], reverse=True)[:10],
        "all_successful": successful
    }


def print_matrix_analysis(analysis: Dict):
    """Print comprehensive analysis"""

    print("\n" + "=" * 100)
    print("TIMEFRAME & ASSET CLASS MATRIX ANALYSIS")
    print("=" * 100)

    print(f"Total Tests Run: {analysis['total_tests']}")
    print(f"Successful Tests: {analysis['successful_tests']}")
    print(f"Winning Tests (Positive Return): {analysis['winning_tests']}")
    print(f"Overall Win Rate: {analysis['win_rate']:.1f}%")
    # Top performers
    print("\n🏆 TOP 10 PERFORMERS:")    for i, result in enumerate(analysis['top_performers'][:10], 1):
        print(f"  {i}. {result['strategy_desc']} on {result['symbol']} ({result['timeframe']})")
        print(f"   Win Rate: {result['win_rate']:.1f}%, Trades: {result['total_trades']}")
    # Strategy × Asset Class Performance
    print("\n📊 STRATEGY × ASSET CLASS AVERAGE RETURNS:")    sorted_strategy_asset = sorted(analysis['strategy_asset_avg'].items(),
                                       key=lambda x: x[1], reverse=True)
    for combo, avg_return in sorted_strategy_asset:
        winner_indicator = "🏆" if avg_return > 0 else "⚠️"
        print(f"   Avg Return: {avg_return:.1f}%")
    # Timeframe Performance
    print("\n⏰ TIMEFRAME AVERAGE RETURNS:")    sorted_timeframes = sorted(analysis['timeframe_avg'].items(),
                             key=lambda x: x[1], reverse=True)
    for timeframe, avg_return in sorted_timeframes:
        winner_indicator = "🏆" if avg_return > 0 else "⚠️"
        print(f"   Avg Return: {avg_return:.1f}%")
    # Asset Class Performance
    print("\n🏢 ASSET CLASS AVERAGE RETURNS:")    sorted_asset_classes = sorted(analysis['asset_class_avg'].items(),
                                key=lambda x: x[1], reverse=True)
    for asset_class, avg_return in sorted_asset_classes:
        winner_indicator = "🏆" if avg_return > 0 else "⚠️"
        winners_count = analysis['winners_by_asset_class'].get(asset_class, 0)
        print(f"   Winners: {winners_count}")
    # Key insights
    print("\n💡 KEY INSIGHTS:")    print(f"  • Best performing asset class: {max(analysis['asset_class_avg'], key=analysis['asset_class_avg'].get)}")
    print(f"  • Best timeframe: {max(analysis['timeframe_avg'], key=analysis['timeframe_avg'].get)}")
    print(f"  • Win rate across all tests: {analysis['win_rate']:.1f}%")
    print(f"  • Total winning combinations: {analysis['winning_tests']}")

    if analysis['top_performers']:
        best = analysis['top_performers'][0]
        print("\n🎯 BEST OVERALL COMBINATION:")        print(f"  Strategy: {best['strategy_desc']}")
        print(f"  Asset: {best['symbol']} ({best['asset_class']})")
        print(f"  Timeframe: {best['timeframe']}")
        print(f"  Return: {best['total_return']:.1f}% | Win Rate: {best['win_rate']:.1f}%")
        print(f"  Trades: {best['total_trades']}")


if __name__ == "__main__":
    # Run the comprehensive matrix test
    results = test_strategy_matrix()

    # Analyze results
    analysis = analyze_matrix_results(results)

    # Print analysis
    print_matrix_analysis(analysis)

    # Save detailed results
    import json
    with open("grok/timeframe_asset_results.json", "w") as f:
        json.dump({
            "analysis": analysis,
            "all_results": results
        }, f, indent=2, default=str)

    print("\n💾 Detailed results saved to: grok/timeframe_asset_results.json")
    print("=" * 100)
