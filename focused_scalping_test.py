#!/usr/bin/env python3
"""
FOCUSED SCALPING STRATEGY TEST
Tests key strategies on selected assets to find winners quickly
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from shared_utils.data_loader import load_ohlcv_yfinance
from shared_strategies.scalping_strategy import (
    AdvancedScalpingStrategy,
    OBVScalpingStrategy,
    CandlestickScalpingStrategy
)
import vectorbt as vbt

def test_strategy_quick(symbol: str, interval: str, strategy_class, strategy_name: str) -> dict:
    """Quick comprehensive backtest"""
    try:
        print(f"🔍 Testing {strategy_name} on {symbol} {interval}")

        # Load data
        period = '30d' if interval in ['5m', '15m'] else '60d'
        data = load_ohlcv_yfinance(symbol, period=period, interval=interval)

        if len(data) < 100:
            return {'status': 'failed', 'error': 'Insufficient data'}

        # Run strategy
        strategy = strategy_class(data)
        signals = strategy.generate_signals()

        # Backtest
        pf = vbt.Portfolio.from_signals(
            data["Close"],
            entries=signals == 1,
            exits=signals == -1,
            init_cash=50_000,  # $50K for scalping
            fees=0.001,
            freq='D' if 'd' in interval else 'H' if 'h' in interval else '5min'
        )

        # Calculate metrics
        total_return = float(pf.total_return())
        win_rate = float(pf.trades.win_rate()) if len(pf.trades) > 0 else 0
        total_trades = len(pf.trades)
        max_drawdown = float(pf.max_drawdown())
        sharpe_ratio = float(pf.sharpe_ratio()) if len(pf.trades) > 0 else 0

        # Winner criteria
        is_winner = (
            total_return > 0.08 and  # 8%+ return
            win_rate > 0.60 and      # 60%+ win rate
            total_trades >= 15 and   # At least 15 trades
            max_drawdown < 0.12      # Max DD < 12%
        )

        result = {
            'strategy': strategy_name,
            'symbol': symbol,
            'interval': interval,
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'is_winner': is_winner,
            'status': 'success'
        }

        # Save data for winners
        if is_winner:
            data_file = f"data/processed/winners/{symbol}_{interval}_{strategy_name.lower().replace(' ', '_')}.parquet"
            os.makedirs("data/processed/winners", exist_ok=True)
            data.to_parquet(data_file, index=False)
            result['data_file'] = data_file

        return result

    except Exception as e:
        return {'status': 'failed', 'error': str(e), 'strategy': strategy_name, 'symbol': symbol, 'interval': interval}

def main():
    """Focused scalping test"""
    print("⚡ FOCUSED SCALPING STRATEGY TEST")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()

    # High-volatility assets that move (user requested)
    test_assets = [
        'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META',  # Tech stocks
        'SPY', 'QQQ',                                    # ETFs
        'GLD', 'SLV'                                     # Commodities
    ]

    timeframes = ['5m', '15m', '30m']

    strategies = [
        (AdvancedScalpingStrategy, "Advanced Scalping"),
        (OBVScalpingStrategy, "OBV Scalping"),
        (CandlestickScalpingStrategy, "Candlestick Scalping")
    ]

    all_results = []

    for asset in test_assets:
        print(f"\n🏢 ASSET: {asset}")
        print("-" * 30)

        for timeframe in timeframes:
            print(f"\n⏰ {timeframe}:")

            for strategy_class, strategy_name in strategies:
                result = test_strategy_quick(asset, timeframe, strategy_class, strategy_name)
                all_results.append(result)

                if result.get('status') == 'success':
                    ret = result.get('total_return', 0)
                    win = result.get('win_rate', 0)
                    trades = result.get('total_trades', 0)

                    winner_icon = "🏆" if result.get('is_winner', False) else "❌"
                    print(".3f"
                else:
                    print(f"❌ {strategy_name}: {result.get('error', 'Failed')}")

    # Analyze winners
    winners = [r for r in all_results if r.get('status') == 'success' and r.get('is_winner', False)]
    losers = [r for r in all_results if r.get('status') == 'success' and not r.get('is_winner', False)]

    print("
📊 RESULTS SUMMARY"    print("=" * 50)
    print(f"Total tests: {len(all_results)}")
    print(f"🏆 WINNERS: {len(winners)}")
    print(f"❌ LOSERS: {len(losers)}")

    if winners:
        print("
🎯 WINNING STRATEGIES:"        sorted_winners = sorted(winners, key=lambda x: x['total_return'], reverse=True)

        for i, result in enumerate(sorted_winners, 1):
            print(f"\n{i}. 🏆 {result['strategy']} on {result['symbol']} {result['interval']}")
            print(".3f")
            print(".3f")
            print(f"   Trades: {result['total_trades']}")

        # Strategy performance
        print("
📈 WINNER BREAKDOWN:"        strat_perf = {}
        for result in winners:
            strat = result['strategy']
            strat_perf[strat] = strat_perf.get(strat, []) + [result['total_return']]

        for strat, returns in strat_perf.items():
            avg_ret = np.mean(returns)
            count = len(returns)
            print(".3f"
    # Save winners
    if winners:
        winners_df = pd.DataFrame(winners)
        winners_df.to_csv('scalping_winners_focused.csv', index=False)
        print("
💾 Winners saved to: scalping_winners_focused.csv"
    # Show sample losers
    if losers:
        print("
📝 SAMPLE LOSERS (not saved):"        worst_losers = sorted(losers, key=lambda x: x['total_return'])[:3]
        for result in worst_losers:
            print(".3f"
if __name__ == "__main__":
    main()
