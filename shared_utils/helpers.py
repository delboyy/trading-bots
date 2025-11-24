import json
from datetime import datetime
from typing import Dict


TRADES_FILE = "logs/trades.jsonl"


def log_trade(trade: Dict, trades_file: str = TRADES_FILE) -> None:
    """Append a trade dict as JSON line to file."""
    trade = {"timestamp": datetime.utcnow().isoformat(), **trade}
    with open(trades_file, "a") as f:
        f.write(json.dumps(trade) + "\n")
