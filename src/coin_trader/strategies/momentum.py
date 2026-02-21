"""Momentum strategy — trend-following based on recent price movement."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from coin_trader.domain.models import Signal, SignalType
from coin_trader.domain.strategy import Strategy
from coin_trader.strategies.registry import register_strategy

logger = structlog.get_logger()


@register_strategy("momentum")
class MomentumStrategy(Strategy):
    """Buy on strong upward momentum, sell on reversal."""

    def __init__(
        self,
        lookback_hours: int = 12,
        entry_threshold: float = 5.0,
        exit_threshold: float = -3.0,
    ) -> None:
        self.lookback_hours = lookback_hours
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    @property
    def name(self) -> str:
        entry = int(self.entry_threshold)
        exit_ = int(self.exit_threshold)
        return f"momentum_{self.lookback_hours}_{entry}_{exit_}"

    @property
    def template(self) -> str:
        return "momentum"

    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        price_history: List[float] = market_data.get("price_history", [])
        current_price: float = market_data.get("current_price", 0)
        has_position: bool = market_data.get("has_position", False)
        entry_price: float = market_data.get("entry_price", 0)

        if not price_history or not current_price:
            return None

        history = price_history[-(self.lookback_hours + 1):]
        if len(history) < 2:
            return None

        start_price = history[0]
        change_pct = (current_price / start_price - 1) * 100

        # SELL: exit on reversal from entry
        if has_position and entry_price > 0:
            profit_pct = (current_price / entry_price - 1) * 100
            if profit_pct <= self.exit_threshold:
                return Signal(
                    strategy_name=self.name,
                    ticker=ticker,
                    signal_type=SignalType.SELL,
                    strength=min(abs(profit_pct) / 10, 1.0),
                    reason=f"Momentum reversal {profit_pct:.1f}% <= {self.exit_threshold}%",
                )

        # BUY: enter on strong momentum
        if not has_position and change_pct >= self.entry_threshold:
            return Signal(
                strategy_name=self.name,
                ticker=ticker,
                signal_type=SignalType.BUY,
                strength=min(change_pct / (self.entry_threshold * 2), 1.0),
                reason=f"Momentum {change_pct:.1f}% >= {self.entry_threshold}%",
            )

        return None
