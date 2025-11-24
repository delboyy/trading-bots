import ccxt
from loguru import logger


class Exchange:
    """Thin wrapper around CCXT for a single exchange (Binance testnet by default)."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        exchange_class = ccxt.binance
        self.exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("Binance sandbox (testnet) enabled")

    def get_price(self, symbol: str) -> float:
        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker["last"])

    def order_market(self, symbol: str, side: str, size: float):
        logger.info(f"Placing market order: {side} {size} {symbol}")
        if side.lower() == "buy":
            return self.exchange.create_market_buy_order(symbol, size)
        else:
            return self.exchange.create_market_sell_order(symbol, size)
