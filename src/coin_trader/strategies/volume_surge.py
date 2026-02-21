"""Volume Surge strategy — buy on unusual volume with positive price action."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from coin_trader.domain.models import Signal, SignalType
from coin_trader.domain.strategy import Strategy
from coin_trader.strategies.registry import register_strategy

logger = structlog.get_logger()


@register_strategy("volume_surge")
class VolumeSurgeStrategy(Strategy):
    """Buy when volume spikes above average with positive price movement."""

    def __init__(
        self,
        lookback_hours: int = 24,
        volume_multiplier: float = 3.0,
    ) -> None:
        self.lookback_hours = lookback_hours
        self.volume_multiplier = volume_multiplier

    @property
    def name(self) -> str:
        return f"volume_surge_{self.lookback_hours}_{int(self.volume_multiplier)}"

    @property
    def template(self) -> str:
        return "volume_surge"

    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        volume_history: List[float] = market_data.get("volume_history", [])
        current_volume: float = market_data.get("volume", 0)
        change_pct: float = market_data.get("change_pct", 0)
        has_position: bool = market_data.get("has_position", False)

        if not volume_history or not current_volume:
            return None

        history = volume_history[-(self.lookback_hours):]
        if len(history) < 2:
            return None

        avg_volume = sum(history) / len(history)
        if avg_volume <= 0:
            return None

        volume_ratio = current_volume / avg_volume

        # BUY: volume surge + positive price
        if not has_position and volume_ratio >= self.volume_multiplier and change_pct > 0:
            strength = min(volume_ratio / (self.volume_multiplier * 2), 1.0)
            return Signal(
                strategy_name=self.name,
                ticker=ticker,
                signal_type=SignalType.BUY,
                strength=strength,
                reason=f"Volume surge {volume_ratio:.1f}x avg, price +{change_pct:.1f}%",
            )

        return None
