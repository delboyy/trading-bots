from backtesting.backtest import run_backtest


def evaluate_strategy(strategy_name: str, symbol: str = "BTC-USD"):
    pf = run_backtest(strategy_name, symbol=symbol)
    stats = pf.stats()
    print(stats)
    return stats
