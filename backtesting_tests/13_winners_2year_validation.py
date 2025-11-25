#!/usr/bin/env python3
"""
13 High-Return Winners - 2-Year IBKR Validation
Tests all 13 validated scalping strategies on 2-year IBKR data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append('.')

from shared_strategies.scalping_strategy import ScalpingStrategy


class ThirteenWinners2YearValidator:
    def __init__(self):
        self.data_dir = Path('data/processed')
        self.ibkr_dir = self.data_dir / 'ibkr_2year'

        # All 13 high-return winner strategies from the analysis
        self.thirteen_winners = [
            {
                'name': 'TSLA Time-Based 15m (Default)',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {},
                '60day_return': 0.3608,
                '60day_win_rate': 0.6226
            },
            {
                'name': 'TSLA Time-Based 15m (Vol 1.3x)',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {'volume_multiplier': 1.3},
                '60day_return': 0.3137,
                '60day_win_rate': 0.5758
            },
            {
                'name': 'TSLA Time-Based 15m (Vol 1.5x)',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {'volume_multiplier': 1.5},
                '60day_return': 0.3610,
                '60day_win_rate': 0.6415
            },
            {
                'name': 'TSLA Time-Based 15m (Mom 7)',
                'strategy': 'time_based_scalping',
                'symbol': 'TSLA',
                'interval': '15m',
                'params': {'momentum_period': 7},
                '60day_return': 0.3615,
                '60day_win_rate': 0.6226
            },
            {
                'name': 'GOOGL RSI 15m (Aggressive)',
                'strategy': 'rsi_scalping',
                'symbol': 'GOOGL',
                'interval': '15m',
                'params': {'rsi_period': 7, 'rsi_oversold': 25, 'rsi_overbought': 75},
                '60day_return': 0.0950,
                '60day_win_rate': 0.5517
            },
            {
                'name': 'BAC RSI 15m (Aggressive)',
                'strategy': 'rsi_scalping',
                'symbol': 'BAC',
                'interval': '15m',
                'params': {'rsi_period': 7, 'rsi_oversold': 25, 'rsi_overbought': 75},
                '60day_return': 0.0527,
                '60day_win_rate': 0.6429
            },
            {
                'name': 'BAC RSI 15m (Vol 1.5x)',
                'strategy': 'rsi_scalping',
                'symbol': 'BAC',
                'interval': '15m',
                'params': {'rsi_period': 14, 'volume_multiplier': 1.5},
                '60day_return': 0.0550,
                '60day_win_rate': 0.7143
            },
            {
                'name': 'DIA Candlestick 5m (Default)',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {},
                '60day_return': 0.0567,
                '60day_win_rate': 0.7742
            },
            {
                'name': 'DIA Candlestick 5m (Vol 1.4x)',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {'volume_multiplier': 1.4},
                '60day_return': 0.0716,
                '60day_win_rate': 0.7436
            },
            {
                'name': 'DIA Candlestick 5m (TP 1.2%)',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {'take_profit_pct': 0.012},
                '60day_return': 0.0567,
                '60day_win_rate': 0.7742
            },
            {
                'name': 'DIA Candlestick 5m (SL 0.4%)',
                'strategy': 'candlestick_scalping',
                'symbol': 'DIA',
                'interval': '5m',
                'params': {'stop_loss_pct': 0.004},
                '60day_return': 0.0567,
                '60day_win_rate': 0.7742
            },
            {
                'name': 'AMD Volume Breakout 5m (1.8x)',
                'strategy': 'volume_breakout',
                'symbol': 'AMD',
                'interval': '5m',
                'params': {'volume_multiplier': 1.8},
                '60day_return': 0.1375,
                '60day_win_rate': 0.6667
            },
            {
                'name': 'AMD Volume Breakout 5m (2.0x)',
                'strategy': 'volume_breakout',
                'symbol': 'AMD',
                'interval': '5m',
                'params': {'volume_multiplier': 2.0},
                '60day_return': 0.1220,
                '60day_win_rate': 0.6429
            }
        ]

    def load_ibkr_data(self, symbol: str, interval: str) -> pd.DataFrame:
        """Load IBKR 2-year data for a symbol"""
        # Look for parquet files in ibkr_2year directory (try multiple naming patterns)
        interval_clean = interval.replace(' ', '').replace('m', 'mins')

        # Try different filename patterns
        patterns = [
            f"ibkr_{symbol}_{interval_clean}_2year.parquet",  # Original TSLA format
            f"{symbol}_{interval_clean}_2y.parquet",          # New format for others
            f"ibkr_{symbol}_{interval_clean}_2y.parquet"      # Alternative format
        ]

        for pattern in patterns:
            filepath = self.ibkr_dir / pattern
            if filepath.exists():
                print(f"Loading IBKR data: {pattern}")
                df = pd.read_parquet(filepath)

                # Ensure proper datetime index
                if 'Time' in df.columns:
                    df['Time'] = pd.to_datetime(df['Time'])
                    df.set_index('Time', inplace=True)

                print(f"Loaded {len(df)} rows of IBKR data")
                print(f"Date range: {df.index[0]} to {df.index[-1]}")
                return df

        print(f"No IBKR data found for {symbol} {interval} (tried patterns: {patterns})")
        return pd.DataFrame()

    def run_strategy_test(self, strategy_config: dict) -> dict:
        """Test a single strategy on 2-year IBKR data"""
        strategy_name = strategy_config['name']
        strategy_type = strategy_config['strategy']
        symbol = strategy_config['symbol']
        interval = strategy_config['interval']
        params = strategy_config['params']
        expected_60d_return = strategy_config['60day_return']
        expected_60d_winrate = strategy_config['60day_win_rate']

        print(f"\n🔄 Testing {strategy_name}...")

        results = {
            'strategy_name': strategy_name,
            'strategy_type': strategy_type,
            'symbol': symbol,
            'interval': interval,
            'params': str(params),
            'expected_60d_return': expected_60d_return,
            'expected_60d_winrate': expected_60d_winrate,
            'ibkr_2year': {},
            'assessment': {}
        }

        # Test on IBKR 2-year data
        ibkr_data = self.load_ibkr_data(symbol, interval)
        if not ibkr_data.empty:
            try:
                print(f"Running 2-year backtest on {len(ibkr_data)} data points...")
                strategy = ScalpingStrategy(ibkr_data, strategy_type=strategy_type, **params)
                ibkr_results = strategy.backtest()

                results['ibkr_2year'] = {
                    'total_return': ibkr_results.get('total_return', 0),
                    'win_rate': ibkr_results.get('win_rate', 0),
                    'total_trades': ibkr_results.get('total_trades', 0),
                    'max_drawdown': ibkr_results.get('max_drawdown', 0),
                    'sharpe_ratio': ibkr_results.get('sharpe_ratio', 0),
                    'data_points': len(ibkr_data),
                    'date_range': f"{ibkr_data.index[0].date()} to {ibkr_data.index[-1].date()}",
                    'status': 'success'
                }

                # Assessment
                ibkr_return = ibkr_results.get('total_return', 0)
                return_diff = ibkr_return - expected_60d_return

                results['assessment'] = {
                    'return_vs_60d': return_diff,
                    'return_multiple': ibkr_return / expected_60d_return if expected_60d_return != 0 else 0,
                    'meets_threshold': ibkr_return > 0.03,  # 3% annual return threshold
                    'robust': abs(return_diff) < 0.10,  # Within 10% of 60-day performance
                    'recommendation': self.get_recommendation(ibkr_return, return_diff)
                }

            except Exception as e:
                print(f"Error during 2-year backtest: {e}")
                results['ibkr_2year'] = {'status': 'error', 'error': str(e)}
                results['assessment'] = {'recommendation': 'ERROR'}
        else:
            results['ibkr_2year'] = {'status': 'no_data'}
            results['assessment'] = {'recommendation': 'NO_DATA'}

        return results

    def get_recommendation(self, ibkr_return: float, return_diff: float) -> str:
        """Get deployment recommendation based on 2-year performance"""
        if ibkr_return > 0.08:  # 8%+ return on 2-year data
            return "HIGH_PRIORITY"
        elif ibkr_return > 0.05:  # 5%+ return on 2-year data
            return "DEPLOY"
        elif ibkr_return > 0.03:  # 3%+ return on 2-year data
            return "MONITOR"
        elif ibkr_return > 0.01:  # 1%+ return on 2-year data
            return "REVIEW"
        elif return_diff > -0.05:  # Within 5% of 60-day performance
            return "STABLE"
        else:
            return "AVOID"

    def run_all_winners_validation(self):
        """Run comprehensive validation of all 13 winners"""
        print("🏆 13 HIGH-RETURN WINNERS - 2-YEAR IBKR VALIDATION")
        print("=" * 80)
        print("Testing all 13 validated scalping strategies on 2-year IBKR data")
        print("Comparing 60-day performance vs 2-year robustness")
        print("=" * 80)

        all_results = []

        for winner in self.thirteen_winners:
            result = self.run_strategy_test(winner)
            all_results.append(result)

            # Print immediate results
            print(f"\n📊 {result['strategy_name']} Results:")

            if result['ibkr_2year'].get('status') == 'success':
                ibkr = result['ibkr_2year']
                expected = result['expected_60d_return']
                actual = ibkr['total_return']
                diff = actual - expected

                print("  IBKR 2-Year Data:")
                print(f"    Return: {actual:.2%}, Expected (60d): {expected:.2%}")
                print(f"    Difference: {diff:+.2%}")
                print(f"    Win Rate: {ibkr['win_rate']:.1%}")
                print(f"    Trades: {ibkr['total_trades']}")
                print(f"    Max DD: {ibkr['max_drawdown']:.2%}")

                assessment = result['assessment']
                print(f"    Recommendation: {assessment['recommendation']}")

                if abs(diff) > 0.05:
                    print(f"    ⚠️  Significant deviation from 60-day performance")
            else:
                print(f"  IBKR 2-Year: {result['ibkr_2year'].get('status', 'unknown')}")

        # Save comprehensive results
        results_df = pd.DataFrame(all_results)
        results_df.to_csv('backtesting_tests/13_winners_2year_validation.csv', index=False)

        print("\n🎯 VALIDATION COMPLETE")
        print(f"Total strategies tested: {len(all_results)}")

        # Performance analysis
        successful_tests = sum(1 for r in all_results if r['ibkr_2year'].get('status') == 'success')
        high_priority = sum(1 for r in all_results if r['assessment'].get('recommendation') == 'HIGH_PRIORITY')
        deployable = sum(1 for r in all_results if r['assessment'].get('recommendation') in ['HIGH_PRIORITY', 'DEPLOY'])

        print(f"Successful 2-year tests: {successful_tests}/13")
        print(f"High priority strategies: {high_priority}")
        print(f"Deployable strategies: {deployable}")

        # Best performers
        successful_results = [r for r in all_results if r['ibkr_2year'].get('status') == 'success']
        if successful_results:
            best_performer = max(successful_results, key=lambda x: x['ibkr_2year']['total_return'])
            print("\n🏆 BEST 2-YEAR PERFORMER:")
            print(f"  {best_performer['strategy_name']}: {best_performer['ibkr_2year']['total_return']:.2%} return")

        # Strategy type analysis
        strategy_types = {}
        for result in successful_results:
            strat_type = result['strategy_type']
            ret = result['ibkr_2year']['total_return']
            if strat_type not in strategy_types:
                strategy_types[strat_type] = []
            strategy_types[strat_type].append(ret)

        print("\n📊 STRATEGY TYPE PERFORMANCE:")
        for strat_type, returns in strategy_types.items():
            avg_return = np.mean(returns)
            print(f"  {strat_type}: {avg_return:.2%} avg return ({len(returns)} strategies)")

        return results_df


def main():
    validator = ThirteenWinners2YearValidator()
    results = validator.run_all_winners_validation()

    # Final deployment recommendations
    print("\n🎯 FINAL DEPLOYMENT RECOMMENDATIONS")
    print("Based on 2-year IBKR validation:")

    high_priority = [r for r in results.to_dict('records')
                    if r['assessment'].get('recommendation') == 'HIGH_PRIORITY']

    deploy = [r for r in results.to_dict('records')
             if r['assessment'].get('recommendation') == 'DEPLOY']

    monitor = [r for r in results.to_dict('records')
              if r['assessment'].get('recommendation') == 'MONITOR']

    if high_priority:
        print("\n🚀 HIGH PRIORITY (Deploy Immediately):")
        for strategy in high_priority:
            print(f"  • {strategy['strategy_name']}: {strategy['ibkr_2year']['total_return']:.2%}")

    if deploy:
        print("\n✅ DEPLOY (Good 2-year performance):")
        for strategy in deploy:
            print(f"  • {strategy['strategy_name']}: {strategy['ibkr_2year']['total_return']:.2%}")

    if monitor:
        print("\n👀 MONITOR (Meets minimum threshold):")
        for strategy in monitor:
            print(f"  • {strategy['strategy_name']}: {strategy['ibkr_2year']['total_return']:.2%}")

    # Risk warning
    print("\n⚠️  RISK REMINDER:")
    print("  • All strategies tested on paper trading data")
    print("  • Live trading may have different slippage/commissions")
    print("  • Monitor performance and adjust position sizing")
    print("  • Never risk more than 1-2% per trade")

if __name__ == "__main__":
    main()
