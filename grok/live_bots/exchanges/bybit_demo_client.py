import os
import time
import hmac
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

import pandas as pd
import requests
from dotenv import load_dotenv


class BybitDemoClient:
    BASE_URL = "https://api-demo.bybit.com"
    RECV_WINDOW = "5000"
    SIGN_TYPE = "2"

    def __init__(self):
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

        self.api_key = os.getenv("BYBIT_DEMO_API_KEY")
        self.api_secret = os.getenv("BYBIT_DEMO_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("BYBIT_DEMO_API_KEY or BYBIT_DEMO_API_SECRET missing.")

        self.session = requests.Session()

    def _sign(self, payload: str) -> Dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        pre_sign = timestamp + self.api_key + self.RECV_WINDOW + payload
        signature = hmac.new(
            self.api_secret.encode(), pre_sign.encode(), hashlib.sha256
        ).hexdigest()
        return {
            "X-BAPI-SIGN-TYPE": self.SIGN_TYPE,
            "X-BAPI-SIGN": signature,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": self.RECV_WINDOW,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        private: bool = False,
    ) -> Dict[str, Any]:
        if params is None:
            params = {}

        url = f"{self.BASE_URL}{endpoint}"
        headers = {}
        payload_str = ""

        if private:
            if method.upper() == "GET":
                query = urlencode(sorted(params.items()))
                payload_str = query
                headers = self._sign(payload_str)
                url = f"{url}?{query}" if query else url
                data = None
            else:
                payload_str = json.dumps(params, sort_keys=True, separators=(",", ":"))
                headers = self._sign(payload_str)
                data = payload_str
        else:
            if method.upper() == "GET" and params:
                query = urlencode(sorted(params.items()))
                url = f"{url}?{query}"
            data = json.dumps(params) if method.upper() != "GET" else None

        print(f"{method.upper()} {endpoint} {params}")

        response = self.session.request(
            method.upper(), url, headers=headers, data=data, timeout=10
        )

        try:
            result = response.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response: {response.text}")

        if result.get("retCode") != 0:
            raise RuntimeError(f"Bybit error {result.get('retCode')}: {result}")

        return result.get("result", {})

    def get_price(self, symbol: str = "BTCUSDT") -> float:
        params = {"category": "linear", "symbol": symbol}
        data = self._request("GET", "/v5/market/tickers", params=params, private=False)
        ticker = data["list"][0]
        return float(ticker["lastPrice"])

    def get_balance(self, asset: str = "USDT") -> float:
        params = {"accountType": "UNIFIED"}
        data = self._request("GET", "/v5/account/wallet-balance", params=params, private=True)
        for entry in data.get("list", []):
            for coin in entry.get("coin", []):
                if coin.get("coin") == asset:
                    balance_str = coin.get("availableToWithdraw") or coin.get("walletBalance") or coin.get("equity") or "0"
                    return float(balance_str)
        raise RuntimeError(f"Asset {asset} not found in wallet balance.")

    def get_positions(self, symbol: str = "BTCUSDT") -> List[Dict[str, Any]]:
        params = {"category": "linear", "symbol": symbol}
        data = self._request("GET", "/v5/position/list", params=params, private=True)
        return data.get("list", [])

    def place_market_order(self, symbol: str, side: str, qty: float) -> Dict[str, Any]:
        payload = {
            "category": "linear",
            "symbol": symbol,
            "side": side.capitalize(),
            "orderType": "Market",
            "qty": str(qty),
        }
        data = self._request("POST", "/v5/order/create", params=payload, private=True)
        return {
            "orderId": data.get("orderId"),
            "price": data.get("avgPrice"),
        }

    def fetch_candles(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        data = self._request("GET", "/v5/market/kline", params=params, private=False)
        records = data.get("list", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(
            records,
            columns=["startTime", "open", "high", "low", "close", "volume", *([None] * (len(records[0]) - 6))],
        )
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        df["Time"] = pd.to_datetime(df["startTime"], unit="ms")
        numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
        df[numeric_cols] = df[numeric_cols].astype(float)
        df = df[["Time", "Open", "High", "Low", "Close", "Volume"]]
        df.sort_values("Time", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
