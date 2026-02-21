"""Upbit notice/announcement fetcher."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from coin_trader.data.protocols import DataSource

logger = structlog.get_logger()

UPBIT_NOTICE_API = "https://api-manager.upbit.com/api/v1/notices"


class NoticeFetcher(DataSource):
    """Fetch and parse Upbit exchange notices for alpha signals."""

    def __init__(self, keywords: Optional[List[str]] = None) -> None:
        self.keywords = keywords or ["신규", "상장", "에어드롭", "마켓", "유의"]
        self._session: Optional[aiohttp.ClientSession] = None
        self._seen_ids: set = set()

    @property
    def name(self) -> str:
        return "notice_fetcher"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        notices = await self.get_new_notices()
        return {"notices": notices, "count": len(notices)}

    async def get_new_notices(self) -> List[Dict[str, Any]]:
        """Fetch notices and return only new ones matching keywords."""
        session = await self._get_session()
        try:
            async with session.get(
                UPBIT_NOTICE_API, params={"page": "1", "per_page": "20"}
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

            notices = data.get("data", {}).get("list", [])
            new_notices = []

            for notice in notices:
                notice_id = notice.get("id", 0)
                if notice_id in self._seen_ids:
                    continue

                title = notice.get("title", "")
                matched_keywords = [kw for kw in self.keywords if kw in title]

                if matched_keywords:
                    new_notices.append({
                        "id": notice_id,
                        "title": title,
                        "created_at": notice.get("created_at", ""),
                        "matched_keywords": matched_keywords,
                        "tickers": self._extract_tickers(title),
                    })
                    self._seen_ids.add(notice_id)

            return new_notices
        except Exception as e:
            logger.error("notice_fetcher.error", error=str(e))
            return []

    @staticmethod
    def _extract_tickers(title: str) -> List[str]:
        """Extract ticker symbols from notice title."""
        # Match patterns like (BTC), (ETH), common in Upbit notices
        matches = re.findall(r'\(([A-Z]{2,10})\)', title)
        return [f"KRW-{m}" for m in matches]
