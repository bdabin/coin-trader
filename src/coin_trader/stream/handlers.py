"""Event handlers connecting WebSocket ticks to the event bus."""

from __future__ import annotations

from typing import Any, Dict

import structlog

from coin_trader.persistence.redis import RedisCache
from coin_trader.stream.redis_bus import CH_TICK, EventBus

logger = structlog.get_logger()


class TickHandler:
    """Handles incoming WebSocket ticks: cache price + emit event."""

    def __init__(self, redis: RedisCache, event_bus: EventBus) -> None:
        self.redis = redis
        self.event_bus = event_bus
        self._tick_count = 0

    async def handle(self, tick: Dict[str, Any]) -> None:
        """Process a tick from WebSocket."""
        ticker = tick.get("ticker", "")
        price = tick.get("price", 0)

        if not ticker or not price:
            return

        # Cache price
        await self.redis.set_price(ticker, price)

        # Emit tick event
        await self.event_bus.emit(CH_TICK, tick)

        self._tick_count += 1
        if self._tick_count % 100 == 0:
            logger.debug("tick_handler.processed", count=self._tick_count, last=ticker)
