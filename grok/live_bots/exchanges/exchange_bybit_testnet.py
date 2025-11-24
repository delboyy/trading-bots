import os
import time
import hmac
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from loguru import logger


class BybitTestnetClient:
    BASE_URL = "https://api-testnet.bybit.com"

    def __init__(self, account_type: str = "UNIFIED"):
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("BYBIT_API_KEY or BYBIT_API_SECRET missing.")

        self.account_type = account_type
        self.recv_window = int(os.getenv("BYBIT_RECV_WINDOW", "5000"))
        self.session = requests.Session()

    def _sign(self, params: Dict[str, Any], body: str = "") -> Dict[str, Any]:
        timestamp = str(int(time.time() * 1000))
        recv_window = str(self.recv_window)
        sign_str = timestamp + self.api_key + recv_window + body
        signature = hmac.new(self.api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
        signed_params = {
            "apiKey": self.api_key,
            "timestamp": timestamp,
            "recvWindow": recv_window,
            "sign": signature,
        }
        return signed_params

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False):
        if params is None:
            params = {}

        body_str = ""
        headers = {}
        if signed:
            if method == "GET":
                body_str = json.dumps(params, separators=(",", ":"), sort_keys=True)
                signed_headers = self._sign(params, body_str)
                headers = {
                    "X-BAPI-API-KEY": signed_headers["apiKey"],
                    "X-BAPI-SIGN": signed_headers["sign"],
                    "X-BAPI-TIMESTAMP": signed_headers["timestamp"],
                    "X-BAPI-RECV-WINDOW": signed_headers["recvWindow"],
                    "X-BAPI-SIGN-TYPE": "2",
                }
                full_params = params
                payload = None
            else:
                body_str = json.dumps(params, separators=(",", ":"), sort_keys=True)
                signed_headers = self._sign(params, body_str)
                headers = {
                    "X-BAPI-API-KEY": signed_headers["apiKey"],
                    "X-BAPI-SIGN": signed_headers["sign"],
                    "X-BAPI-TIMESTAMP": signed_headers["timestamp"],
                    "X-BAPI-RECV-WINDOW": signed_headers["recvWindow"],
                    "X-BAPI-SIGN-TYPE": "2",
                    "Content-Type": "application/json",
                }
                full_params = None
                payload = body_str
        else:
            full_params = params
            payload = None

        url = f"{self.BASE_URL}{path}"
        logger.info(f"Bybit request {method} {path} params={full_params}")

        try:
            if method == "GET":
                response = self.session.get(url, params=full_params, headers=headers, timeout=10)
            else:
                response = self.session.post(url, params=None, data=payload, headers=headers, timeout=10)
            try:
                data = response.json()
            except ValueError:
                raise RuntimeError(f"Non-JSON response: {response.text}")
        except Exception as e:
            raise RuntimeError(f"HTTP error: {e}") from e

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit error {data.get('retCode')}: {data.get('retMsg')}")

        return data.get("result")

    def fetch_price(self, symbol: str) -> float:
        params = {"category": "linear", "symbol": symbol.replace("/", "")}
        result = self._request("GET", "/v5/market/tickers", params)
        ticker = result["list"][0]
        return float(ticker["lastPrice"])

    def get_balance(self, asset: str = "USDT") -> float:
        params = {"accountType": self.account_type}
        result = self._request("GET", "/v5/account/wallet-balance", params, signed=True)
        for entry in result.get("list", []):
            for coin in entry.get("coin", []):
                if coin.get("coin") == asset:
                    return float(coin.get("walletBalance", 0))
        raise RuntimeError(f"Asset {asset} not found in wallet balance.")

    def get_position_info(self, symbol: Optional[str] = None):
        params = {"category": "linear"}
        if symbol:
            params["symbol"] = symbol.replace("/", "")
        result = self._request("GET", "/v5/position/list", params, signed=True)
        return result.get("list", [])

    def create_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        payload = {
            "category": "linear",
            "symbol": symbol.replace("/", ""),
            "side": side.capitalize(),
            "orderType": "Market",
            "qty": str(quantity),
            "timeInForce": "GoodTillCancel",
        }
        result = self._request("POST", "/v5/order/create", payload, signed=True)
        return result
