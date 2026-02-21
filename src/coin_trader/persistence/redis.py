"""Redis cache + pub/sub event bus."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

PRICE_PREFIX = "price:"
PRICE_TTL = 10  # seconds


class RedisCache:
    """Redis-based price cache and pub/sub event bus."""

    def __init__(self, url: str = "redis://localhost:6379") -> None:
        self.url = url
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(self.url, decode_responses=True)
        await self._client.ping()
        logger.info("redis.connected", url=self.url)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            logger.info("redis.closed")

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected")
        return self._client

    # --- Price Cache ---

    async def set_price(self, ticker: str, price: float) -> None:
        """Cache current price with TTL."""
        await self.client.setex(f"{PRICE_PREFIX}{ticker}", PRICE_TTL, str(price))

    async def get_price(self, ticker: str) -> Optional[float]:
        """Get cached price."""
        val = await self.client.get(f"{PRICE_PREFIX}{ticker}")
        return float(val) if val else None

    async def get_all_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Get all cached prices."""
        pipe = self.client.pipeline()
        for t in tickers:
            pipe.get(f"{PRICE_PREFIX}{t}")
        values = await pipe.execute()
        result: Dict[str, float] = {}
        for t, v in zip(tickers, values):
            if v is not None:
                result[t] = float(v)
        return result

    # --- Pub/Sub ---

    async def publish(self, channel: str, data: Dict[str, Any]) -> int:
        """Publish event to a channel."""
        return await self.client.publish(channel, json.dumps(data))

    async def subscribe(
        self,
        channels: List[str],
        callback: Callable[[str, Dict[str, Any]], Any],
    ) -> None:
        """Subscribe to channels and call callback for each message."""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    data = json.loads(message["data"])
                    await callback(channel, data)
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()

    # --- Rate Limiting ---

    async def check_rate_limit(self, key: str, max_count: int, window_secs: int) -> bool:
        """Simple sliding window rate limiter. Returns True if allowed."""
        current = await self.client.get(f"rate:{key}")
        if current and int(current) >= max_count:
            return False
        pipe = self.client.pipeline()
        pipe.incr(f"rate:{key}")
        pipe.expire(f"rate:{key}", window_secs)
        await pipe.execute()
        return True
