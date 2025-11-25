#!/usr/bin/env python3
"""
SIMPLE SCALPING STRATEGY TEST
More lenient conditions to actually generate trades and find winners
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
import vectorbt as vbt

def create_simple_momentum_scalping(data: pd.DataFrame) -> pd.Series:
    """Simple momentum-based scalping with volume confirmation"""
    df = data.copy()

    # Simple momentum (5-period)
    df['momentum'] = df['Close'] - df['Close'].shift(5)
    df['momentum_sma'] = df['momentum'].rolling(3).mean()

    # Volume confirmation
    df['volume_sma'] = df['Volume'].rolling(10).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma']

    signals = pd.Series(0, index=df.index)

    # Long: Positive momentum + volume
    long_condition = (
        (df['momentum'] > 0) &
        (df['momentum_sma'] > 0) &
        (df['volume_ratio'] > 1.1)  # 10% above average volume
    )

    # Short: Negative momentum + volume
    short_condition = (
        (df['momentum'] < 0) &
        (df['momentum_sma'] < 0) &
        (df['volume_ratio'] > 1.1)
    )

    signals[long_condition] = 1
    signals[short_condition] = -1

    return signals

def create_rsi_scalping(data: pd.DataFrame) -> pd.Series:
    """RSI-based scalping strategy"""
    df = data.copy()

    # Calculate RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Volume filter
    df['volume_sma'] = df['Volume'].rolling(10).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma']

    signals = pd.Series(0, index=df.index)

    # RSI oversold + volume
    long_condition = (
        (df['rsi'] < 35) &  # Oversold
        (df['volume_ratio'] > 1.2)  # Above average volume
    )

    # RSI overbought + volume
    short_condition = (
        (df['rsi'] > 65) &  # Overbought
        (df['volume_ratio'] > 1.2)
    )

    signals[long_condition] = 1
    signals[short_condition] = -1

    return signals

def create_volume_breakout_scalping(data: pd.DataFrame) -> pd.Series:
    """Volume breakout scalping"""
    df = data.copy()

    # Price action
    df['high_10'] = df['High'].rolling(10).max()
    df['low_10'] = df['Low'].rolling(10).min()

    # Volume spike
    df['volume_sma'] = df['Volume'].rolling(20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma']

    signals = pd.Series(0, index=df.index)

    # Breakout above recent high + volume spike
    long_breakout = (
        (df['Close'] > df['high_10'].shift(1)) &
        (df['volume_ratio'] > 1.5)  # 50% above average volume
    )

    # Breakdown below recent low + volume spike
    short_breakout = (
        (df['Close'] < df['low_10'].shift(1)) &
        (df['volume_ratio'] > 1.5)
    )

    signals[long_breakout] = 1
    signals[short_breakout] = -1

    return signals

def test_scalping_strategy(symbol: str, interval: str, strategy_func, strategy_name: str) -> dict:
    """Test a scalping strategy"""
    try:
        print(f"🔍 Testing {strategy_name} on {symbol} {interval}")

        # Load data
        period = '30d' if interval in ['5m', '15m'] else '60d'
        data = load_ohlcv_yfinance(symbol, period=period, interval=interval)

        if len(data) < 100:
            return {'status': 'failed', 'error': 'Insufficient data'}

        # Generate signals
        signals = strategy_func(data)
        signal_count = len(signals[signals != 0])

        if signal_count == 0:
            print(f"   ⚠️  No signals generated")
            return {'status': 'no_signals', 'signals': 0}

        # Backtest
        pf = vbt.Portfolio.from_signals(
            data["Close"],
            entries=signals == 1,
            exits=signals == -1,
            init_cash=25_000,  # Smaller capital for scalping
            fees=0.001,
            freq='D' if 'd' in interval else 'H' if 'h' in interval else '5min'
        )

        # Metrics
        total_return = float(pf.total_return())
        win_rate = float(pf.trades.win_rate()) if len(pf.trades) > 0 else 0
        total_trades = len(pf.trades)
        max_drawdown = float(pf.max_drawdown())
        sharpe_ratio = float(pf.sharpe_ratio()) if len(pf.trades) > 0 else 0

        # More lenient winner criteria for scalping
        is_winner = (
            total_return > 0.03 and  # 3%+ return (more realistic for scalping)
            win_rate > 0.52 and      # 52%+ win rate
            total_trades >= 8 and    # At least 8 trades
            max_drawdown < 0.08      # Max DD < 8%
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
            'signals_generated': signal_count,
            'is_winner': is_winner,
            'status': 'success'
        }

        # Save winner data
        if is_winner:
            data_file = f"data/processed/winners/{symbol}_{interval}_{strategy_name.lower().replace(' ', '_')}.parquet"
            os.makedirs("data/processed/winners", exist_ok=True)
            data.to_parquet(data_file, index=False)
            result['data_file'] = data_file

        return result

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}

def main():
    """Test simple scalping strategies"""
    print("⚡ SIMPLE SCALPING STRATEGY TEST")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()

    # Assets that move (user requested)
    test_assets = ['NVDA', 'TSLA', 'SPY', 'QQQ', 'GLD', 'SLV', 'AAPL', 'MSFT']
    timeframes = ['5m', '15m']

    strategies = [
        (create_simple_momentum_scalping, "Momentum Scalping"),
        (create_rsi_scalping, "RSI Scalping"),
        (create_volume_breakout_scalping, "Volume Breakout Scalping")
    ]

    all_results = []
    winners = []

    for asset in test_assets:
        print(f"\n🏢 ASSET: {asset}")
        print("-" * 30)

        for timeframe in timeframes:
            print(f"\n⏰ {timeframe}:")

            for strategy_func, strategy_name in strategies:
                result = test_scalping_strategy(asset, timeframe, strategy_func, strategy_name)
                all_results.append(result)

                if result.get('status') == 'success':
                    ret = result.get('total_return', 0)
                    win = result.get('win_rate', 0)
                    trades = result.get('total_trades', 0)
                    signals = result.get('signals_generated', 0)

                    winner_icon = "🏆" if result.get('is_winner', False) else "❌"
                    print(".3f"
                    if result.get('is_winner', False):
                        winners.append(result)

                elif result.get('status') == 'no_signals':
                    print(f"⚠️  {strategy_name}: No signals")
                else:
                    print(f"❌ {strategy_name}: {result.get('error', 'Failed')}")

    # Results summary
    print("\n" + "="*60)
    print("📊 SCALPING RESULTS SUMMARY")
    print("="*60)

    successful_tests = [r for r in all_results if r.get('status') == 'success']
    print(f"Total tests: {len(all_results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"🏆 WINNERS: {len(winners)}")

    if winners:
        print("\n🎯 WINNING SCALPING STRATEGIES:")
        print("=" * 50)

        sorted_winners = sorted(winners, key=lambda x: (x['total_return'], x['win_rate']), reverse=True)

        for i, result in enumerate(sorted_winners, 1):
            print(f"\n{i}. 🏆 {result['strategy']} on {result['symbol']} {result['interval']}")
            print(".3f")
            print(".3f")
            print(f"   Trades: {result['total_trades']}")
            print(".3f")

        # Performance by strategy type
        print("\n📈 WINNERS BY STRATEGY TYPE:")
        strategy_perf = {}
        for result in winners:
            strat = result['strategy']
            strategy_perf[strat] = strategy_perf.get(strat, []) + [result['total_return']]

        for strat, returns in strategy_perf.items():
            avg_return = np.mean(returns)
            count = len(returns)
            print(".3f"
        # Save winners
        winners_df = pd.DataFrame(winners)
        winners_df.to_csv('simple_scalping_winners.csv', index=False)
        print("
💾 Winners saved to: simple_scalping_winners.csv"
    else:
        print("\n❌ No winning strategies found with current parameters.")
        print("Try adjusting the winner criteria or strategy parameters.")

    # Show some examples of what didn't work
    if successful_tests:
        print("\n📝 EXAMPLES OF NON-WINNERS (for reference):")
        non_winners = [r for r in successful_tests if not r.get('is_winner', False)][:3]
        for result in non_winners:
            print(".3f"

if __name__ == "__main__":
    main()
