"""CoinGecko data source — free, no API key required."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from coin_trader.data.protocols import DataSource

logger = structlog.get_logger()

COINGECKO_API = "https://api.coingecko.com/api/v3"

# Mapping Upbit tickers to CoinGecko IDs
TICKER_TO_ID = {
    "KRW-BTC": "bitcoin",
    "KRW-ETH": "ethereum",
    "KRW-XRP": "ripple",
    "KRW-SOL": "solana",
    "KRW-DOGE": "dogecoin",
    "KRW-ADA": "cardano",
    "KRW-AVAX": "avalanche-2",
    "KRW-LINK": "chainlink",
    "KRW-DOT": "polkadot",
    "KRW-MATIC": "matic-network",
}


class CoinGeckoDataSource(DataSource):
    """CoinGecko social + market data."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "coingecko"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch(self, **kwargs: Any) -> Dict[str, Any]:
        ticker = kwargs.get("ticker", "KRW-BTC")
        return await self.get_coin_data(ticker)

    async def get_coin_data(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive coin data including social metrics."""
        coin_id = TICKER_TO_ID.get(ticker, ticker.split("-")[-1].lower())
        session = await self._get_session()

        try:
            async with session.get(
                f"{COINGECKO_API}/coins/{coin_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "true",
                    "developer_data": "true",
                },
            ) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()

            community = data.get("community_data", {})
            developer = data.get("developer_data", {})
            sentiment = data.get("sentiment_votes_up_percentage", 0)

            return {
                "ticker": ticker,
                "market_cap_rank": data.get("market_cap_rank", 0),
                "coingecko_score": data.get("coingecko_score", 0),
                "community_score": data.get("community_score", 0),
                "developer_score": data.get("developer_score", 0),
                "sentiment_up_pct": sentiment,
                "twitter_followers": community.get("twitter_followers", 0),
                "reddit_subscribers": community.get("reddit_subscribers", 0),
                "github_stars": developer.get("stars", 0),
                "commit_count_4w": developer.get("commit_count_4_weeks", 0),
            }
        except Exception as e:
            logger.error("coingecko.error", ticker=ticker, error=str(e))
            return {}

    async def get_btc_dominance(self) -> float:
        """Get BTC market dominance percentage."""
        session = await self._get_session()
        try:
            async with session.get(f"{COINGECKO_API}/global") as resp:
                data = await resp.json()
                return data.get("data", {}).get("market_cap_percentage", {}).get("btc", 0.0)
        except Exception:
            return 0.0

    async def get_trending(self) -> List[Dict[str, Any]]:
        """Get trending coins by search volume."""
        session = await self._get_session()
        try:
            async with session.get(f"{COINGECKO_API}/search/trending") as resp:
                data = await resp.json()
                coins = data.get("coins", [])
                return [
                    {
                        "name": c["item"]["name"],
                        "symbol": c["item"]["symbol"],
                        "market_cap_rank": c["item"].get("market_cap_rank", 0),
                    }
                    for c in coins
                ]
        except Exception:
            return []
