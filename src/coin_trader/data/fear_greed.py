"""Fear & Greed Index data source — free, no auth required."""

from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp
import structlog

from coin_trader.data.protocols import DataSource

logger = structlog.get_logger()

FEAR_GREED_API = "https://api.alternative.me/fng/"


class FearGreedDataSource(DataSource):
    """Crypto Fear & Greed Index."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "fear_greed"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        return await self.get_index()

    async def get_index(self) -> Dict[str, Any]:
        """Get current Fear & Greed index.

        Returns:
            {value: 0-100, classification: str, timestamp: int}
            0-24: Extreme Fear, 25-49: Fear, 50: Neutral,
            51-74: Greed, 75-100: Extreme Greed
        """
        session = await self._get_session()
        try:
            async with session.get(FEAR_GREED_API, params={"limit": "1"}) as resp:
                data = await resp.json()
                if data and "data" in data and len(data["data"]) > 0:
                    item = data["data"][0]
                    return {
                        "value": int(item.get("value", 50)),
                        "classification": item.get("value_classification", "Neutral"),
                        "timestamp": int(item.get("timestamp", 0)),
                    }
                return {"value": 50, "classification": "Neutral", "timestamp": 0}
        except Exception as e:
            logger.error("fear_greed.error", error=str(e))
            return {"value": 50, "classification": "Neutral", "timestamp": 0}
