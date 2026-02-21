"""Tests for Redis cache and event bus."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from coin_trader.persistence.redis import RedisCache
from coin_trader.stream.handlers import TickHandler
from coin_trader.stream.redis_bus import CH_SIGNAL, CH_TICK, EventBus


class FakeRedisClient:
    """Fake Redis client for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, str] = {}
        self._ttls: Dict[str, int] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value
        self._ttls[key] = ttl

    async def get(self, key: str) -> str:
        return self._store.get(key)

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        pass

    async def publish(self, channel: str, data: str) -> int:
        return 1

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, "0")) + 1
        self._store[key] = str(val)
        return val

    async def expire(self, key: str, ttl: int) -> None:
        self._ttls[key] = ttl

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    def pubsub(self) -> AsyncMock:
        return AsyncMock()


class FakePipeline:
    def __init__(self, client: FakeRedisClient) -> None:
        self._client = client
        self._commands: List[Any] = []

    def get(self, key: str) -> FakePipeline:
        self._commands.append(("get", key))
        return self

    def incr(self, key: str) -> FakePipeline:
        self._commands.append(("incr", key))
        return self

    def expire(self, key: str, ttl: int) -> FakePipeline:
        self._commands.append(("expire", key, ttl))
        return self

    async def execute(self) -> List[Any]:
        results = []
        for cmd in self._commands:
            if cmd[0] == "get":
                results.append(self._client._store.get(cmd[1]))
            elif cmd[0] == "incr":
                val = await self._client.incr(cmd[1])
                results.append(val)
            elif cmd[0] == "expire":
                await self._client.expire(cmd[1], cmd[2])
                results.append(True)
        self._commands.clear()
        return results


@pytest.fixture
def fake_redis():
    cache = RedisCache(url="redis://fake:6379")
    cache._client = FakeRedisClient()
    return cache


class TestRedisCache:
    @pytest.mark.asyncio
    async def test_set_and_get_price(self, fake_redis):
        await fake_redis.set_price("KRW-BTC", 50000000.0)
        price = await fake_redis.get_price("KRW-BTC")
        assert price == 50000000.0

    @pytest.mark.asyncio
    async def test_get_missing_price(self, fake_redis):
        price = await fake_redis.get_price("KRW-NONE")
        assert price is None

    @pytest.mark.asyncio
    async def test_get_all_prices(self, fake_redis):
        await fake_redis.set_price("KRW-BTC", 50000000.0)
        await fake_redis.set_price("KRW-ETH", 4000000.0)
        prices = await fake_redis.get_all_prices(["KRW-BTC", "KRW-ETH", "KRW-XRP"])
        assert prices["KRW-BTC"] == 50000000.0
        assert prices["KRW-ETH"] == 4000000.0
        assert "KRW-XRP" not in prices

    @pytest.mark.asyncio
    async def test_rate_limit(self, fake_redis):
        assert await fake_redis.check_rate_limit("test", max_count=2, window_secs=60) is True
        assert await fake_redis.check_rate_limit("test", max_count=2, window_secs=60) is True
        assert await fake_redis.check_rate_limit("test", max_count=2, window_secs=60) is False

    @pytest.mark.asyncio
    async def test_publish(self, fake_redis):
        count = await fake_redis.publish("test_channel", {"event": "tick"})
        assert count == 1


class TestEventBus:
    @pytest.mark.asyncio
    async def test_register_and_emit(self, fake_redis):
        bus = EventBus(fake_redis)
        received: List[Dict[str, Any]] = []

        async def handler(data: Dict[str, Any]) -> None:
            received.append(data)

        bus.on(CH_TICK, handler)
        await bus.emit(CH_TICK, {"ticker": "KRW-BTC", "price": 50000000})

        assert len(received) == 1
        assert received[0]["ticker"] == "KRW-BTC"

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, fake_redis):
        bus = EventBus(fake_redis)
        results: List[str] = []

        async def h1(data: Dict[str, Any]) -> None:
            results.append("h1")

        async def h2(data: Dict[str, Any]) -> None:
            results.append("h2")

        bus.on(CH_SIGNAL, h1)
        bus.on(CH_SIGNAL, h2)
        await bus.emit(CH_SIGNAL, {"signal": "BUY"})

        assert results == ["h1", "h2"]

    @pytest.mark.asyncio
    async def test_handler_error_doesnt_crash(self, fake_redis):
        bus = EventBus(fake_redis)
        results: List[str] = []

        async def bad_handler(data: Dict[str, Any]) -> None:
            raise ValueError("broken")

        async def good_handler(data: Dict[str, Any]) -> None:
            results.append("ok")

        bus.on(CH_TICK, bad_handler)
        bus.on(CH_TICK, good_handler)
        await bus.emit(CH_TICK, {"test": True})

        assert results == ["ok"]

    @pytest.mark.asyncio
    async def test_emit_to_nonexistent_channel(self, fake_redis):
        bus = EventBus(fake_redis)
        # Should not raise
        await bus.emit("nonexistent", {"data": 1})


class TestTickHandler:
    @pytest.mark.asyncio
    async def test_processes_tick(self, fake_redis):
        bus = EventBus(fake_redis)
        received: List[Dict[str, Any]] = []

        async def on_tick(data: Dict[str, Any]) -> None:
            received.append(data)

        bus.on(CH_TICK, on_tick)
        handler = TickHandler(fake_redis, bus)

        tick = {"ticker": "KRW-BTC", "price": 50000000, "volume": 0.5}
        await handler.handle(tick)

        # Price should be cached
        price = await fake_redis.get_price("KRW-BTC")
        assert price == 50000000.0

        # Event should be emitted
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_ignores_invalid_tick(self, fake_redis):
        bus = EventBus(fake_redis)
        handler = TickHandler(fake_redis, bus)

        # Missing ticker
        await handler.handle({"price": 100})
        # Missing price
        await handler.handle({"ticker": "KRW-BTC"})
        # Both missing
        await handler.handle({})
