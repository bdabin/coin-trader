"""Coin correlation network in FalkorDB."""

from __future__ import annotations

from typing import Any, Dict, List

import structlog

from coin_trader.graph.client import GraphClient

logger = structlog.get_logger()


class CoinNetwork:
    """Manage coin correlation graph."""

    def __init__(self, client: GraphClient) -> None:
        self.client = client

    def upsert_coin(self, ticker: str, name: str = "", sector: str = "") -> None:
        """Create or update a coin node."""
        self.client.query(
            """MERGE (c:Coin {ticker: $ticker})
               SET c.name = $name, c.sector = $sector""",
            {"ticker": ticker, "name": name, "sector": sector},
        )

    def set_correlation(
        self,
        ticker_a: str,
        ticker_b: str,
        coefficient: float,
        lag_minutes: int = 0,
        period: str = "24h",
    ) -> None:
        """Set correlation between two coins."""
        self.client.query(
            """MATCH (a:Coin {ticker: $ticker_a})
               MATCH (b:Coin {ticker: $ticker_b})
               MERGE (a)-[r:CORRELATES]->(b)
               SET r.coefficient = $coefficient,
                   r.lag_minutes = $lag_minutes,
                   r.period = $period""",
            {
                "ticker_a": ticker_a,
                "ticker_b": ticker_b,
                "coefficient": coefficient,
                "lag_minutes": lag_minutes,
                "period": period,
            },
        )

    def set_same_sector(self, ticker_a: str, ticker_b: str) -> None:
        """Mark two coins as same sector."""
        self.client.query(
            """MATCH (a:Coin {ticker: $ticker_a})
               MATCH (b:Coin {ticker: $ticker_b})
               MERGE (a)-[:SAME_SECTOR]->(b)""",
            {"ticker_a": ticker_a, "ticker_b": ticker_b},
        )

    def get_correlated_coins(
        self, ticker: str, min_coefficient: float = 0.7, max_lag: int = 15
    ) -> List[Dict[str, Any]]:
        """Get coins correlated with given ticker.

        Use case: BTC drops → which alts follow within 15 min?
        """
        rows = self.client.query_result(
            """MATCH (src:Coin {ticker: $ticker})-[r:CORRELATES]->(alt:Coin)
               WHERE r.coefficient > $min_coef AND r.lag_minutes <= $max_lag
               RETURN alt.ticker AS ticker, r.coefficient AS coefficient,
                      r.lag_minutes AS lag_minutes
               ORDER BY r.coefficient DESC""",
            {
                "ticker": ticker,
                "min_coef": min_coefficient,
                "max_lag": max_lag,
            },
        )
        return [
            {"ticker": r[0], "coefficient": r[1], "lag_minutes": r[2]}
            for r in rows
        ]

    def get_sector_coins(self, ticker: str) -> List[str]:
        """Get all coins in the same sector."""
        rows = self.client.query_result(
            """MATCH (c:Coin {ticker: $ticker})-[:SAME_SECTOR]-(peer:Coin)
               RETURN DISTINCT peer.ticker AS ticker""",
            {"ticker": ticker},
        )
        return [r[0] for r in rows]
