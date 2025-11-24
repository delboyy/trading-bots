from backtesting.backtest import run_backtest
import itertools


WINDOWS = [10, 20, 30, 40]
Z_SCORES = [1.0, 1.5, 2.0]


def optimize_mean_reversion(symbol: str = "BTC-USD"):
    best = None

    for w, z in itertools.product(WINDOWS, Z_SCORES):
        print(f"Testing window={w}, z={z}")
        pf = run_backtest(
            "mean_reversion",
            symbol=symbol,
            strategy_params={"window": w, "z_thresh": z},
        )
        stats = pf.stats()
        total_return = stats["Total Return [%]"]

        if best is None or total_return > best["return"]:
            best = {"window": w, "z": z, "return": float(total_return)}

    print("BEST:", best)
    return best


if __name__ == "__main__":
    optimize_mean_reversion()
