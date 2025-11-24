from dataclasses import dataclass


@dataclass
class RiskConfig:
    max_position_pct: float
    max_total_leverage: float
    max_drawdown_pct: float
    stop_loss_pct: float
    take_profit_pct: float


class RiskEngine:
    def __init__(self, config: RiskConfig):
        self.config = config

    def position_size(self, equity: float, price: float) -> float:
        # TODO: Complete this method. Source file was truncated here.
        # max_cash = equity * self.confi
        pass
