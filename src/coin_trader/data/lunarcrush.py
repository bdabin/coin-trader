"""LunarCrush social intelligence data source."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from coin_trader.data.protocols import DataSource

logger = structlog.get_logger()

LUNARCRUSH_API = "https://lunarcrush.com/api4/public"


class LunarCrushDataSource(DataSource):
    """LunarCrush social data — Galaxy Score, Alt Rank, sentiment."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "lunarcrush"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "BTC")
        return await self.get_coin_data(symbol)

    async def get_coin_data(self, symbol: str) -> Dict[str, Any]:
        """Get social metrics for a coin."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{LUNARCRUSH_API}/coins/{symbol}/v1"
            ) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
                return {
                    "symbol": symbol,
                    "galaxy_score": data.get("galaxy_score", 0),
                    "alt_rank": data.get("alt_rank", 0),
                    "social_volume": data.get("social_volume", 0),
                    "social_volume_change": data.get("social_volume_24h_change", 0),
                    "social_sentiment": data.get("social_sentiment", 0),
                    "volatility": data.get("volatility", 0),
                }
        except Exception as e:
            logger.error("lunarcrush.error", symbol=symbol, error=str(e))
            return {}

    async def get_top_coins(
        self, sort: str = "galaxy_score", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get top coins sorted by metric."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{LUNARCRUSH_API}/coins/list/v1",
                params={"sort": sort, "limit": str(limit)},
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("data", [])
        except Exception:
            return []
