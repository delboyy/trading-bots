import os
import time
import hmac
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from loguru import logger


class BinanceDemoClient:
    BASE_URL = "https://testnet.binancefuture.com"

    def __init__(self):
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("BINANCE_API_KEY or BINANCE_API_SECRET missing.")

        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _sign_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = params.copy()
        params["timestamp"] = int(time.time() * 1000)
        query = "&".join(f"{k}={params[k]}" for k in sorted(params))
        signature = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False):
        if params is None:
            params = {}
        request_params = self._sign_params(params) if signed else params

        logger.info(f"Request {method} {path} params={request_params}")
        try:
            url = f"{self.BASE_URL}{path}"
            if method == "GET":
                response = self.session.get(url, params=request_params, timeout=10)
            else:
                query = "&".join(f"{k}={request_params[k]}" for k in sorted(request_params))
                response = self.session.post(
                    url,
                    data=query,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )
            data = response.json()
        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {e}") from e

        if response.status_code >= 300:
            raise RuntimeError(f"API error ({response.status_code}): {data}")

        return data

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return symbol.replace("/", "")

    def fetch_price(self, symbol: str) -> float:
        norm_symbol = self._normalize_symbol(symbol)
        data = self._request("GET", "/fapi/v1/ticker/price", {"symbol": norm_symbol})
        return float(data["price"])

    def create_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        norm_symbol = self._normalize_symbol(symbol)
        payload = {
            "symbol": norm_symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
        }
        return self._request("POST", "/fapi/v1/order", payload, signed=True)

    def get_balance(self, asset: str = "USDT") -> float:
        balances = self._request("GET", "/fapi/v2/balance", signed=True)
        match = next((b for b in balances if b["asset"] == asset), None)
        if not match:
            raise RuntimeError(f"Asset {asset} not found in balance.")
        return float(match["balance"])

    def get_position_info(self, symbol: Optional[str] = None):
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
        positions = self._request("GET", "/fapi/v2/positionRisk", params, signed=True)
        return positions
