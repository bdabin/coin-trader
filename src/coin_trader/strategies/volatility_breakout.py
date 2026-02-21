"""Volatility Breakout strategy — Larry Williams style."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from coin_trader.domain.models import Signal, SignalType
from coin_trader.domain.strategy import Strategy
from coin_trader.strategies.registry import register_strategy

logger = structlog.get_logger()


@register_strategy("volatility_breakout")
class VolatilityBreakoutStrategy(Strategy):
    """Buy when price breaks above open + k * (prev_high - prev_low)."""

    def __init__(self, k_factor: float = 0.5) -> None:
        self.k_factor = k_factor

    @property
    def name(self) -> str:
        return f"volatility_breakout_{int(self.k_factor * 10)}"

    @property
    def template(self) -> str:
        return "volatility_breakout"

    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        current_price: float = market_data.get("current_price", 0)
        has_position: bool = market_data.get("has_position", False)
        open_price: float = market_data.get("open_price", 0)
        prev_high: float = market_data.get("prev_high", 0)
        prev_low: float = market_data.get("prev_low", 0)

        if not current_price or not prev_high or not prev_low:
            return None

        range_val = prev_high - prev_low
        if range_val <= 0:
            return None

        target = open_price + self.k_factor * range_val if open_price else 0

        # BUY: breakout above target
        if not has_position and target > 0 and current_price > target:
            strength = min((current_price - target) / range_val, 1.0)
            return Signal(
                strategy_name=self.name,
                ticker=ticker,
                signal_type=SignalType.BUY,
                strength=max(strength, 0.1),
                reason=f"Breakout: {current_price:.0f} > target {target:.0f}",
            )

        return None
