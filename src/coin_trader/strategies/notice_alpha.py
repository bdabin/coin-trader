"""Notice Alpha strategy — trade on exchange announcements."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from coin_trader.domain.models import Signal, SignalType
from coin_trader.domain.strategy import Strategy
from coin_trader.strategies.registry import register_strategy

logger = structlog.get_logger()


@register_strategy("notice_alpha")
class NoticeAlphaStrategy(Strategy):
    """Buy coins mentioned in bullish exchange notices."""

    def __init__(
        self,
        keywords: Optional[List[str]] = None,
    ) -> None:
        self.keywords = keywords or ["신규", "상장", "에어드롭"]

    @property
    def name(self) -> str:
        return "notice_alpha"

    @property
    def template(self) -> str:
        return "notice_alpha"

    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        notices: List[Dict[str, Any]] = market_data.get("notices", [])
        has_position: bool = market_data.get("has_position", False)

        if not notices or has_position:
            return None

        # Check if this ticker is mentioned in any recent notice
        for notice in notices:
            notice_tickers: List[str] = notice.get("tickers", [])
            matched_keywords: List[str] = notice.get("matched_keywords", [])

            if ticker in notice_tickers and matched_keywords:
                # Higher strength for new listings
                is_listing = any(kw in ["신규", "상장"] for kw in matched_keywords)
                strength = 0.9 if is_listing else 0.6

                return Signal(
                    strategy_name=self.name,
                    ticker=ticker,
                    signal_type=SignalType.BUY,
                    strength=strength,
                    reason=f"Notice: {notice.get('title', '')[:50]}",
                    params={"notice_id": notice.get("id", 0)},
                )

        return None
