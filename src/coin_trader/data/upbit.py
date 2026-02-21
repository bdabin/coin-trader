"""Upbit REST API data source."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from coin_trader.data.protocols import DataSource

logger = structlog.get_logger()

UPBIT_API = "https://api.upbit.com/v1"


class UpbitDataSource(DataSource):
    """Fetch OHLCV and market data from Upbit."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "upbit"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        """Fetch current ticker data."""
        ticker = kwargs.get("ticker", "KRW-BTC")
        return await self.get_ticker(ticker)

    async def get_ticker(self, ticker: str) -> Dict[str, Any]:
        """Get current ticker info."""
        session = await self._get_session()
        async with session.get(f"{UPBIT_API}/ticker", params={"markets": ticker}) as resp:
            data = await resp.json()
            if data and len(data) > 0:
                item = data[0]
                return {
                    "ticker": item.get("market", ""),
                    "price": item.get("trade_price", 0),
                    "high_price": item.get("high_price", 0),
                    "low_price": item.get("low_price", 0),
                    "volume": item.get("acc_trade_volume_24h", 0),
                    "change_pct": item.get("signed_change_rate", 0) * 100,
                }
            return {}

    async def get_ohlcv(
        self, ticker: str, interval: str = "minutes/60", count: int = 24
    ) -> List[Dict[str, Any]]:
        """Get OHLCV candle data."""
        session = await self._get_session()
        url = f"{UPBIT_API}/candles/{interval}"
        params = {"market": ticker, "count": count}
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            return [
                {
                    "timestamp": c.get("candle_date_time_utc", ""),
                    "open": c.get("opening_price", 0),
                    "high": c.get("high_price", 0),
                    "low": c.get("low_price", 0),
                    "close": c.get("trade_price", 0),
                    "volume": c.get("candle_acc_trade_volume", 0),
                }
                for c in (data if isinstance(data, list) else [])
            ]

    async def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Get orderbook data."""
        session = await self._get_session()
        async with session.get(
            f"{UPBIT_API}/orderbook", params={"markets": ticker}
        ) as resp:
            data = await resp.json()
            if data and len(data) > 0:
                return data[0]
            return {}
