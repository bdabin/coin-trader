"""Redis-backed event bus for inter-component communication."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import structlog

from coin_trader.persistence.redis import RedisCache

logger = structlog.get_logger()

# Channel names
CH_TICK = "tick"
CH_SIGNAL = "signal"
CH_TRADE = "trade"
CH_RISK = "risk"
CH_AI = "ai_decision"


class EventBus:
    """Redis pub/sub based event bus."""

    def __init__(self, redis: RedisCache) -> None:
        self.redis = redis
        self._handlers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}

    def on(self, channel: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register handler for a channel."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    async def emit(self, channel: str, data: Dict[str, Any]) -> None:
        """Publish event and notify local handlers."""
        await self.redis.publish(channel, data)
        for handler in self._handlers.get(channel, []):
            try:
                await handler(data)
            except Exception as e:
                logger.error("event_bus.handler_error", channel=channel, error=str(e))

    async def start_listening(self) -> None:
        """Start listening on all registered channels."""
        channels = list(self._handlers.keys())
        if not channels:
            logger.warning("event_bus.no_channels")
            return

        logger.info("event_bus.listening", channels=channels)
        await self.redis.subscribe(channels, self._dispatch)

    async def _dispatch(self, channel: str, data: Dict[str, Any]) -> None:
        """Dispatch message to registered handlers."""
        for handler in self._handlers.get(channel, []):
            try:
                await handler(data)
            except Exception as e:
                logger.error("event_bus.dispatch_error", channel=channel, error=str(e))
