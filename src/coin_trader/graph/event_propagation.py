"""Event propagation pattern tracking in FalkorDB."""

from __future__ import annotations

from typing import Any, Dict, List

import structlog

from coin_trader.graph.client import GraphClient

logger = structlog.get_logger()


class EventPropagation:
    """Track how market events propagate through price moves."""

    def __init__(self, client: GraphClient) -> None:
        self.client = client

    def create_market_event(
        self, event_type: str, description: str, timestamp: str
    ) -> None:
        """Create a market event node."""
        self.client.query(
            """CREATE (e:MarketEvent {
                   type: $type,
                   description: $description,
                   timestamp: $timestamp
               })""",
            {"type": event_type, "description": description, "timestamp": timestamp},
        )

    def create_price_move(
        self, ticker: str, change_pct: float, timestamp: str
    ) -> None:
        """Create a price move node."""
        self.client.query(
            """CREATE (p:PriceMove {
                   ticker: $ticker,
                   change_pct: $change_pct,
                   timestamp: $timestamp
               })""",
            {"ticker": ticker, "change_pct": change_pct, "timestamp": timestamp},
        )

    def link_event_to_move(
        self,
        event_type: str,
        event_timestamp: str,
        ticker: str,
        move_timestamp: str,
        lag_minutes: int,
        price_impact_pct: float,
    ) -> None:
        """Link a market event to a resulting price move."""
        self.client.query(
            """MATCH (e:MarketEvent {type: $event_type, timestamp: $event_ts})
               MATCH (p:PriceMove {ticker: $ticker, timestamp: $move_ts})
               MERGE (e)-[:TRIGGERED {
                   lag_minutes: $lag,
                   price_impact_pct: $impact
               }]->(p)""",
            {
                "event_type": event_type,
                "event_ts": event_timestamp,
                "ticker": ticker,
                "move_ts": move_timestamp,
                "lag": lag_minutes,
                "impact": price_impact_pct,
            },
        )

    def link_cascade(
        self,
        src_ticker: str,
        src_timestamp: str,
        dst_ticker: str,
        dst_timestamp: str,
        lag_minutes: int,
        magnitude: float,
    ) -> None:
        """Link cascading price moves."""
        self.client.query(
            """MATCH (src:PriceMove {ticker: $src_ticker, timestamp: $src_ts})
               MATCH (dst:PriceMove {ticker: $dst_ticker, timestamp: $dst_ts})
               MERGE (src)-[:CASCADED {
                   lag_minutes: $lag,
                   magnitude: $magnitude
               }]->(dst)""",
            {
                "src_ticker": src_ticker,
                "src_ts": src_timestamp,
                "dst_ticker": dst_ticker,
                "dst_ts": dst_timestamp,
                "lag": lag_minutes,
                "magnitude": magnitude,
            },
        )

    def get_event_impact(self, event_type: str) -> List[Dict[str, Any]]:
        """Get average impact of a specific event type."""
        rows = self.client.query_result(
            """MATCH (e:MarketEvent {type: $type})-[r:TRIGGERED]->(p:PriceMove)
               RETURN avg(p.change_pct) AS avg_impact,
                      avg(r.lag_minutes) AS avg_lag,
                      count(p) AS sample_count""",
            {"type": event_type},
        )
        if not rows:
            return []
        return [
            {"avg_impact": r[0], "avg_lag": r[1], "sample_count": r[2]}
            for r in rows
        ]

    def get_cascade_chain(self, ticker: str, timestamp: str) -> List[Dict[str, Any]]:
        """Get cascade chain from a price move."""
        rows = self.client.query_result(
            """MATCH (src:PriceMove {ticker: $ticker, timestamp: $ts})
                     -[:CASCADED*1..5]->(dst:PriceMove)
               RETURN dst.ticker AS ticker, dst.change_pct AS change_pct,
                      dst.timestamp AS timestamp
               ORDER BY dst.timestamp""",
            {"ticker": ticker, "ts": timestamp},
        )
        return [
            {"ticker": r[0], "change_pct": r[1], "timestamp": r[2]}
            for r in rows
        ]
