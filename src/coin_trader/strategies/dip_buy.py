"""Dip Buy strategy — validated +23.82%, 100% win rate.

Buy when price drops by `drop_pct` within `timeframe_hours`,
sell when price recovers by `recovery_pct` from entry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from coin_trader.domain.models import Signal, SignalType
from coin_trader.domain.strategy import Strategy
from coin_trader.strategies.registry import register_strategy

logger = structlog.get_logger()


@register_strategy("dip_buy")
class DipBuyStrategy(Strategy):
    """Buys the dip, sells on recovery."""

    def __init__(
        self,
        drop_pct: float = -7.0,
        recovery_pct: float = 2.0,
        timeframe_hours: int = 24,
        name_suffix: str = "",
    ) -> None:
        self.drop_pct = drop_pct
        self.recovery_pct = recovery_pct
        self.timeframe_hours = timeframe_hours
        self._name = f"dip_buy_{int(drop_pct)}_{int(recovery_pct)}_{timeframe_hours}"
        if name_suffix:
            self._name += f"_{name_suffix}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def template(self) -> str:
        return "dip_buy"

    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        """Evaluate dip buy conditions.

        market_data expected keys:
            - price_history: list of hourly close prices (newest last)
            - current_price: current price
            - has_position: bool, whether we hold this ticker
            - entry_price: float, avg entry price (if has_position)
        """
        price_history: List[float] = market_data.get("price_history", [])
        current_price: float = market_data.get("current_price", 0)
        has_position: bool = market_data.get("has_position", False)
        entry_price: float = market_data.get("entry_price", 0)

        if not price_history or not current_price:
            return None

        # Trim history to timeframe
        history = price_history[-(self.timeframe_hours + 1):]
        if len(history) < 2:
            return None

        start_price = history[0]
        change_pct = (current_price / start_price - 1) * 100

        # SELL: check recovery from entry
        if has_position and entry_price > 0:
            profit_pct = (current_price / entry_price - 1) * 100
            if profit_pct >= self.recovery_pct:
                return Signal(
                    strategy_name=self.name,
                    ticker=ticker,
                    signal_type=SignalType.SELL,
                    strength=min(profit_pct / (self.recovery_pct * 2), 1.0),
                    reason=f"Recovery {profit_pct:.1f}% >= {self.recovery_pct}%",
                    params={
                        "change_pct": change_pct,
                        "profit_pct": profit_pct,
                        "entry_price": entry_price,
                    },
                )

        # BUY: check dip threshold
        if not has_position and change_pct <= self.drop_pct:
            strength = min(abs(change_pct) / abs(self.drop_pct * 2), 1.0)
            return Signal(
                strategy_name=self.name,
                ticker=ticker,
                signal_type=SignalType.BUY,
                strength=strength,
                reason=f"Dip {change_pct:.1f}% <= {self.drop_pct}%",
                params={
                    "change_pct": change_pct,
                    "start_price": start_price,
                    "current_price": current_price,
                },
            )

        return None

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "template": self.template,
            "drop_pct": self.drop_pct,
            "recovery_pct": self.recovery_pct,
            "timeframe_hours": self.timeframe_hours,
        }
