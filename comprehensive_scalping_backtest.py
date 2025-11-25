#!/usr/bin/env python3
"""
COMPREHENSIVE SCALPING STRATEGY BACKTEST SUITE
Tests multiple advanced scalping strategies across diverse assets
Focuses on finding winners with detailed performance analysis
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
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

def create_time_based_strategy(data: pd.DataFrame) -> pd.Series:
    """
    Time-based scalping strategy using session indicators
    """
    df = data.copy()

    # Add session indicator
    from shared_utils.indicators import get_session_indicator
    df['session'] = get_session_indicator(df)

    # Simple time-based strategy: Buy in NY AM session, Sell in NY PM
    signals = pd.Series(0, index=df.index)

    # Buy during NY AM session (high liquidity)
    ny_am = df['session'] == 3  # NY AM session
    price_low = df['Low'] < df['Low'].rolling(10).mean()  # Price near lows

    # Sell during NY PM session (profit taking)
    ny_pm = df['session'] == 4  # NY PM session
    price_high = df['High'] > df['High'].rolling(10).mean()  # Price near highs

    signals[ny_am & price_low] = 1
    signals[ny_pm & price_high] = -1

    return signals

def create_momentum_scalping_strategy(data: pd.DataFrame) -> pd.Series:
    """
    Momentum-based scalping using short-term momentum
    """
    df = data.copy()

    # Short-term momentum indicators
    df['momentum_5'] = df['Close'] - df['Close'].shift(5)
    df['momentum_10'] = df['Close'] - df['Close'].shift(10)
    df['momentum_sma'] = df['momentum_5'].rolling(5).mean()

    # Volume confirmation
    df['volume_sma'] = df['Volume'].rolling(20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma']

    signals = pd.Series(0, index=df.index)

    # Long signals: Strong upward momentum + volume
    long_signal = (
        (df['momentum_5'] > 0) &
        (df['momentum_10'] > 0) &
        (df['momentum_sma'] > df['momentum_sma'].shift(1)) &
        (df['volume_ratio'] > 1.2)
    )

    # Short signals: Strong downward momentum + volume
    short_signal = (
        (df['momentum_5'] < 0) &
        (df['momentum_10'] < 0) &
        (df['momentum_sma'] < df['momentum_sma'].shift(1)) &
        (df['volume_ratio'] > 1.2)
    )

    signals[long_signal] = 1
    signals[short_signal] = -1

    return signals

def comprehensive_backtest(strategy_func, strategy_name: str, symbol: str,
                          interval: str, **kwargs) -> Dict[str, Any]:
    """
    Comprehensive backtest with detailed performance metrics
    """
    try:
        print(f"🔍 Backtesting {strategy_name} on {symbol} {interval}")

        # Load data (use appropriate period for timeframe)
        if interval in ['5m', '15m']:
            period = '30d'  # Last 30 days for high-frequency data
        elif interval == '30m':
            period = '60d'  # Last 60 days for 30m
        else:
            period = '90d'  # Last 90 days for lower frequency

        data = load_ohlcv_yfinance(symbol, period=period, interval=interval)

        if len(data) < 100:
            return {'error': f'Insufficient data: {len(data)} bars', 'status': 'failed'}

        # Generate signals
        if callable(strategy_func):
            if hasattr(strategy_func, '__name__') and 'strategy' in strategy_func.__name__:
                # It's a class-based strategy
                strategy = strategy_func(data, **kwargs)
                signals = strategy.generate_signals()
            else:
                # It's a function-based strategy
                signals = strategy_func(data)
        else:
            # Fallback
            signals = pd.Series(0, index=data.index)

        # Run backtest
        pf = vbt.Portfolio.from_signals(
            data["Close"],
            entries=signals == 1,
            exits=signals == -1,
            init_cash=100_000,  # $100K starting capital
            fees=0.001,  # 0.1% per trade (scalping fees)
            freq='D' if 'd' in interval else 'H' if 'h' in interval else '5min'
        )

        # Calculate comprehensive metrics
        total_return = float(pf.total_return())
        win_rate = float(pf.trades.win_rate()) if len(pf.trades) > 0 else 0
        total_trades = len(pf.trades)
        max_drawdown = float(pf.max_drawdown())
        sharpe_ratio = float(pf.sharpe_ratio()) if len(pf.trades) > 0 else 0
        profit_factor = float(pf.trades.profit_factor()) if len(pf.trades) > 0 else 0

        # Additional metrics
        avg_trade_return = float(pf.trades.mean()) if len(pf.trades) > 0 else 0
        max_win = float(pf.trades.max()) if len(pf.trades) > 0 else 0
        max_loss = float(pf.trades.min()) if len(pf.trades) > 0 else 0

        # Risk-adjusted metrics
        calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        sortino_ratio = float(pf.sortino_ratio()) if len(pf.trades) > 0 else 0

        # Trading efficiency
        avg_holding_period = np.mean([len(pos) for pos in pf.positions if len(pos) > 0]) if hasattr(pf, 'positions') and pf.positions else 0

        # Market conditions
        volatility = data['Close'].pct_change().std() * np.sqrt(252)  # Annualized volatility
        avg_volume = data['Volume'].mean()

        # Determine if this is a WINNER (profitable strategy)
        is_winner = (
            total_return > 0.05 and  # At least 5% return
            win_rate > 0.55 and      # At least 55% win rate
            total_trades >= 10 and   # At least 10 trades
            max_drawdown < 0.15      # Max drawdown < 15%
        )

        result = {
            'strategy': strategy_name,
            'symbol': symbol,
            'interval': interval,
            'period': period,
            'data_points': len(data),

            # Core Performance
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'max_drawdown': max_drawdown,

            # Risk Metrics
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'profit_factor': profit_factor,

            # Trade Analysis
            'avg_trade_return': avg_trade_return,
            'max_win': max_win,
            'max_loss': max_loss,
            'avg_holding_period': avg_holding_period,

            # Market Context
            'volatility': volatility,
            'avg_volume': avg_volume,

            # Winner Classification
            'is_winner': is_winner,
            'status': 'success'
        }

        # Save data for winners only
        if is_winner:
            data_file = f"data/processed/winners/{symbol}_{interval}_{strategy_name.lower().replace(' ', '_')}.parquet"
            os.makedirs("data/processed/winners", exist_ok=True)
            data.to_parquet(data_file, index=False)
            result['data_file'] = data_file

        return result

    except Exception as e:
        print(f"❌ Error in {strategy_name} on {symbol}: {e}")
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'interval': interval,
            'error': str(e),
            'status': 'failed'
        }

def main():
    """Run comprehensive scalping strategy backtests"""
    print("🚀 COMPREHENSIVE SCALPING STRATEGY BACKTEST SUITE")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print()

    # Diverse asset classes (stocks, ETFs, commodities)
    test_assets = [
        # Large Cap Stocks
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',

        # ETFs
        'SPY', 'QQQ', 'IWM', 'VTI', 'XLK', 'XLF', 'XLE',

        # Commodities/Precious Metals
        'GLD', 'SLV', 'USO', 'UNG',

        # International
        'EWJ', 'EWG', 'EWU', 'FXI',  # Japan, Germany, UK, China

        # Sector ETFs
        'XLY', 'XLP', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI'
    ]

    # Scalping timeframes
    timeframes = ['5m', '15m', '30m']

    # Strategy configurations
    strategies = [
        (AdvancedScalpingStrategy, "Advanced Scalping", {}),
        (OBVScalpingStrategy, "OBV Scalping", {}),
        (CandlestickScalpingStrategy, "Candlestick Scalping", {}),
        (create_time_based_strategy, "Time-Based Scalping", {}),
        (create_momentum_scalping_strategy, "Momentum Scalping", {})
    ]

    all_results = []

    print("🎯 TESTING ACROSS MULTIPLE ASSET CLASSES")
    print("Assets:", len(test_assets))
    print("Timeframes:", len(timeframes))
    print("Strategies:", len(strategies))
    print("Total combinations:", len(test_assets) * len(timeframes) * len(strategies))
    print()

    # Run comprehensive backtests
    for asset in test_assets:
        print(f"\n🏢 TESTING ASSET: {asset}")
        print("-" * 50)

        for timeframe in timeframes:
            print(f"\n⏰ {timeframe} Timeframe:")

            for strategy_func, strategy_name, kwargs in strategies:
                result = comprehensive_backtest(
                    strategy_func, strategy_name, asset, timeframe, **kwargs
                )
                all_results.append(result)

                if result.get('status') == 'success':
                    ret = result.get('total_return', 0)
                    win = result.get('win_rate', 0)
                    trades = result.get('total_trades', 0)
                    dd = result.get('max_drawdown', 0)

                    status_icon = "🏆" if result.get('is_winner', False) else "❌"
                    print(".3f"
                else:
                    print(f"❌ {strategy_name}: {result.get('error', 'Failed')}")

    # Analyze results
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE RESULTS ANALYSIS")
    print("="*80)

    successful_results = [r for r in all_results if r.get('status') == 'success']
    failed_results = [r for r in all_results if r.get('status') == 'failed']
    winner_results = [r for r in successful_results if r.get('is_winner', False)]

    print(f"Total backtests attempted: {len(all_results)}")
    print(f"Successful backtests: {len(successful_results)}")
    print(f"Failed backtests: {len(failed_results)}")
    print(f"🏆 WINNING STRATEGIES: {len(winner_results)}")
    print()

    if winner_results:
        print("🎯 TOP WINNING STRATEGIES:")
        print("=" * 50)

        # Sort by multiple criteria
        sorted_winners = sorted(winner_results,
                               key=lambda x: (x['total_return'], x['win_rate'], -x['max_drawdown']),
                               reverse=True)

        for i, result in enumerate(sorted_winners[:15], 1):  # Top 15 winners
            print(f"\n{i}. 🏆 {result['strategy']} on {result['symbol']} {result['interval']}")
            print(".3f")
            print(".3f")
            print(".3f")
            print(".3f")
            print(f"   📊 Trades: {result['total_trades']}")

        print("
💎 WINNER BREAKDOWN BY CATEGORY:"        print("=" * 40)

        # Group by strategy type
        strategy_performance = {}
        for result in winner_results:
            strat = result['strategy']
            if strat not in strategy_performance:
                strategy_performance[strat] = []
            strategy_performance[strat].append(result['total_return'])

        for strategy, returns in strategy_performance.items():
            avg_return = np.mean(returns)
            win_count = len(returns)
            print(".3f")

        # Group by asset class
        print("
📈 WINNERS BY ASSET CLASS:"        print("=" * 40)

        asset_performance = {}
        for result in winner_results:
            asset = result['symbol']
            if asset not in asset_performance:
                asset_performance[asset] = []
            asset_performance[asset].append(result['total_return'])

        # Sort by average return
        sorted_assets = sorted(asset_performance.items(),
                              key=lambda x: np.mean(x[1]), reverse=True)

        for asset, returns in sorted_assets[:10]:  # Top 10 assets
            avg_return = np.mean(returns)
            win_count = len(returns)
            print(".3f")

        # Timeframe analysis
        print("
⏰ WINNERS BY TIMEFRAME:"        print("=" * 40)

        tf_performance = {}
        for result in winner_results:
            tf = result['interval']
            if tf not in tf_performance:
                tf_performance[tf] = []
            tf_performance[tf].append(result['total_return'])

        for tf, returns in tf_performance.items():
            avg_return = np.mean(returns)
            win_count = len(returns)
            print(".3f")

    # Save comprehensive results
    results_df = pd.DataFrame(all_results)
    results_df.to_csv('comprehensive_scalping_results.csv', index=False)

    winners_df = pd.DataFrame(winner_results)
    winners_df.to_csv('scalping_winners_only.csv', index=False)

    print("\n💾 RESULTS SAVED:")
    print(f"   📄 All results: comprehensive_scalping_results.csv ({len(all_results)} tests)")
    print(f"   🏆 Winners only: scalping_winners_only.csv ({len(winner_results)} winners)")
    print(f"   📁 Winner data: data/processed/winners/")

    # Show some losing strategies for context
    if successful_results:
        losing_results = [r for r in successful_results if not r.get('is_winner', False)]
        if losing_results:
            print("\n📝 SAMPLE LOSERS (for context, not saved):")
            sample_losers = sorted(losing_results,
                                   key=lambda x: x['total_return'])[:5]  # Worst 5

            for result in sample_losers:
                print(".3f"))

if __name__ == "__main__":
    main()
