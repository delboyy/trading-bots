import vectorbt as vbt
import importlib
from utils.data_loader import load_ohlcv_yfinance
from typing import Dict, Any


def load_strategy(strategy_name: str, data, **params):
    module = importlib.import_module(f"strategies.{strategy_name}")
    strategy_class = getattr(module, "Strategy")
    return strategy_class(data, **params)


def run_backtest(
    strategy_name: str,
    symbol: str = "SPY",
    period: str = "2y",
    interval: str = "1h",
    strategy_params: Dict[str, Any] | None = None,
) -> vbt.Portfolio:
    if strategy_params is None:
        strategy_params = {}

    data = load_ohlcv_yfinance(symbol, period=period, interval=interval)
    strategy = load_strategy(strategy_name, data, **strategy_params)
    signals = strategy.generate_signals()

    pf = vbt.Portfolio.from_signals(
        data["Close"],
        entries=signals == 1,
        exits=signals == -1,
        init_cash=100_000,
        fees=0.001,
    )

    return pf


if __name__ == "__main__":
    pf = run_backtest("mean_reversion", symbol="BTC-USD", interval="1h")
    print(pf.stats())
    pf.plot().show()
