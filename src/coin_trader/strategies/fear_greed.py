"""Fear & Greed strategy — contrarian buy on extreme fear."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from coin_trader.domain.models import Signal, SignalType
from coin_trader.domain.strategy import Strategy
from coin_trader.strategies.registry import register_strategy

logger = structlog.get_logger()


@register_strategy("fear_greed")
class FearGreedStrategy(Strategy):
    """Buy on extreme fear, sell on extreme greed."""

    def __init__(
        self,
        buy_threshold: int = 25,
        sell_threshold: int = 75,
    ) -> None:
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    @property
    def name(self) -> str:
        return f"fear_greed_{self.buy_threshold}_{self.sell_threshold}"

    @property
    def template(self) -> str:
        return "fear_greed"

    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        fg_value: int = market_data.get("fear_greed_value", -1)
        has_position: bool = market_data.get("has_position", False)

        if fg_value < 0:
            return None

        # SELL: extreme greed
        if has_position and fg_value >= self.sell_threshold:
            strength = min((fg_value - self.sell_threshold) / 25, 1.0)
            return Signal(
                strategy_name=self.name,
                ticker=ticker,
                signal_type=SignalType.SELL,
                strength=max(strength, 0.3),
                reason=f"Extreme Greed: F&G={fg_value} >= {self.sell_threshold}",
            )

        # BUY: extreme fear
        if not has_position and fg_value <= self.buy_threshold:
            strength = min((self.buy_threshold - fg_value) / 25, 1.0)
            return Signal(
                strategy_name=self.name,
                ticker=ticker,
                signal_type=SignalType.BUY,
                strength=max(strength, 0.3),
                reason=f"Extreme Fear: F&G={fg_value} <= {self.buy_threshold}",
            )

        return None
