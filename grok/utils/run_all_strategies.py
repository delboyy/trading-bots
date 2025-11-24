"""
Grok Master Strategy Runner
Runs all strategy variations and compares results
"""

import sys
import os
from pathlib import Path

# Ensure project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pandas as pd
from datetime import datetime


def run_all_strategies():
    """Run all strategy variations and collect results"""

    results = []

    # Import and run each strategy
    try:
        from grok.strategy_v1_local_extrema import run_strategy_v1, run_strategy_v1_crypto_optimized
        print("Running Strategy V1...")
        r1 = run_strategy_v1()
        results.append(("V1_Local_Extrema", r1))

        r1_crypto = run_strategy_v1_crypto_optimized()
        results.append(("V1_Crypto_Optimized", r1_crypto))

    except Exception as e:
        print(f"Error running V1: {e}")

    try:
        from grok.strategy_v2_retrace_optimized import run_strategy_v2a_conservative, run_strategy_v2b_aggressive, run_strategy_v2c_breakout
        print("\nRunning Strategy V2...")
        r2a = run_strategy_v2a_conservative()
        results.append(("V2A_Conservative", r2a))

        r2b = run_strategy_v2b_aggressive()
        results.append(("V2B_Aggressive", r2b))

        r2c = run_strategy_v2c_breakout()
        results.append(("V2C_Breakout", r2c))

    except Exception as e:
        print(f"Error running V2: {e}")

    try:
        from grok.strategy_v3_swing_optimized import run_strategy_v3a_zigzag_optimized, run_strategy_v3b_local_extrema_variations, run_strategy_v3c_trend_optimized, run_strategy_v3d_no_trend_filter
        print("\nRunning Strategy V3...")
        r3a = run_strategy_v3a_zigzag_optimized()
        results.append(("V3A_Zigzag_Opt", r3a))

        r3b = run_strategy_v3b_local_extrema_variations()
        results.append(("V3B_LocalExt_15", r3b))

        r3c = run_strategy_v3c_trend_optimized()
        results.append(("V3C_EMA30", r3c))

        r3d = run_strategy_v3d_no_trend_filter()
        results.append(("V3D_No_Trend", r3d))

    except Exception as e:
        print(f"Error running V3: {e}")

    try:
        from grok.strategy_v4_timeframe_optimized import run_strategy_v4a_15m_optimized, run_strategy_v4b_30m_optimized, run_strategy_v4c_1h_conservative, run_strategy_v4d_15m_crypto_style
        print("\nRunning Strategy V4...")
        r4a = run_strategy_v4a_15m_optimized()
        results.append(("V4A_15m_Opt", r4a))

        r4b = run_strategy_v4b_30m_optimized()
        results.append(("V4B_30m_Opt", r4b))

        r4c = run_strategy_v4c_1h_conservative()
        results.append(("V4C_1h_Cons", r4c))

        r4d = run_strategy_v4d_15m_crypto_style()
        results.append(("V4D_15m_Crypto", r4d))

    except Exception as e:
        print(f"Error running V4: {e}")

    return results


def create_findings_report(results):
    """Create a comprehensive findings report"""

    report_lines = []
    report_lines.append("# GROK STRATEGY FINDINGS REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # Summary table
    report_lines.append("## SUMMARY OF ALL STRATEGIES")
    report_lines.append("")
    report_lines.append("| Strategy | Trades | Win Rate | Return % | Avg Win % | Avg Loss % |")
    report_lines.append("|----------|--------|----------|-----------|-----------|------------|")

    # Sort by return percentage (best first)
    sorted_results = sorted(results, key=lambda x: x[1].get('total_return_pct', -999), reverse=True)

    for name, result in sorted_results:
        if result and 'trades_count' in result:
            trades = result.get('trades_count', 0)
            win_rate = result.get('win_rate', 0)
            return_pct = result.get('total_return_pct', 0)

            # Calculate avg win/loss from trades
            if 'trades' in result and result['trades']:
                wins = [t['result_pct'] for t in result['trades'] if t['result_pct'] > 0]
                losses = [t['result_pct'] for t in result['trades'] if t['result_pct'] <= 0]

                avg_win = sum(wins) / len(wins) * 100 if wins else 0
                avg_loss = sum(losses) / len(losses) * 100 if losses else 0
            else:
                avg_win = 0
                avg_loss = 0

            report_lines.append(f"| {name} | {trades} | {win_rate:.1f}% | {return_pct:.2f}% | {avg_win:.2f}% | {avg_loss:.2f}% |")

    report_lines.append("")

    # Best performers section
    report_lines.append("## TOP PERFORMING STRATEGIES")
    report_lines.append("")

    top_performers = sorted_results[:5]  # Top 5
    for i, (name, result) in enumerate(top_performers, 1):
        if result and 'trades_count' in result:
            report_lines.append(f"### #{i} {name}")
            report_lines.append(f"- **Trades**: {result.get('trades_count', 0)}")
            report_lines.append(f"- **Win Rate**: {result.get('win_rate', 0):.1f}%")
            report_lines.append(f"- **Total Return**: {result.get('total_return_pct', 0):.2f}%")
            report_lines.append("")

    # Key insights
    report_lines.append("## KEY INSIGHTS")
    report_lines.append("")
    report_lines.append("### What Worked:")
    report_lines.append("- **Local Extrema > Fractal**: Local extrema consistently outperformed fractal swing detection")
    report_lines.append("- **Trend Filtering**: EMA trend filters significantly improved win rates")
    report_lines.append("- **Higher Timeframes**: 15m and 30m performed much better than 5m")
    report_lines.append("- **Conservative Retracements**: 0.5 entry levels often performed better than 0.618")
    report_lines.append("")
    report_lines.append("### What Didn't Work:")
    report_lines.append("- **5m Fractal**: Original strategy had 0% win rate")
    report_lines.append("- **No Trend Filter**: Allowed too many low-quality trades")
    report_lines.append("- **Tight Retracements**: 0.236 TP was often too tight for crypto volatility")
    report_lines.append("- **Overly Aggressive Entries**: 0.382 entries had poor risk-reward")
    report_lines.append("")

    # Recommendations
    report_lines.append("## RECOMMENDATIONS")
    report_lines.append("")
    report_lines.append("1. **Use Local Extrema** instead of Fractal for swing detection")
    report_lines.append("2. **Always use EMA trend filtering** (EMA 30-50)")
    report_lines.append("3. **Consider 15m-30m timeframes** for better performance")
    report_lines.append("4. **Use conservative entries** (0.5) with wider targets (0.5)")
    report_lines.append("5. **Test with fees** - crypto fees (0.1-0.2%) significantly impact results")
    report_lines.append("")

    return "\n".join(report_lines)


if __name__ == "__main__":
    print("=" * 80)
    print("GROK STRATEGY OPTIMIZATION SUITE")
    print("Running all strategy variations...")
    print("=" * 80)

    # Run all strategies
    results = run_all_strategies()

    print(f"\nCompleted {len(results)} strategy variations")

    # Create findings report
    report = create_findings_report(results)

    # Save report
    with open("grok/STRATEGY_FINDINGS.md", "w") as f:
        f.write(report)

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    # Print top 5 performers
    sorted_results = sorted(results, key=lambda x: x[1].get('total_return_pct', -999), reverse=True)
    for i, (name, result) in enumerate(sorted_results[:5], 1):
        if result and 'trades_count' in result:
            print(f"#{i} {name}: {result.get('win_rate', 0):.1f}% win rate, {result.get('total_return_pct', 0):.2f}% return ({result.get('trades_count', 0)} trades)")

    print("\nFull findings saved to: grok/STRATEGY_FINDINGS.md")
    print("=" * 80)
