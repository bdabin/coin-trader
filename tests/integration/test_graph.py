"""Tests for graph layer with mocked FalkorDB client."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from coin_trader.graph.client import GraphClient
from coin_trader.graph.coin_network import CoinNetwork
from coin_trader.graph.event_propagation import EventPropagation
from coin_trader.graph.strategy_lineage import StrategyLineage


class FakeQueryResult:
    """Fake FalkorDB query result."""

    def __init__(self, rows: Optional[List[Any]] = None) -> None:
        self.result_set = rows or []


class FakeGraph:
    """Fake FalkorDB graph that records queries."""

    def __init__(self) -> None:
        self.queries: List[Dict[str, Any]] = []
        self._results: List[FakeQueryResult] = []

    def set_result(self, rows: List[Any]) -> None:
        self._results.append(FakeQueryResult(rows))

    def query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> FakeQueryResult:
        self.queries.append({"cypher": cypher, "params": params})
        if self._results:
            return self._results.pop(0)
        return FakeQueryResult()


@pytest.fixture
def fake_client():
    client = GraphClient.__new__(GraphClient)
    client._graph = FakeGraph()
    client._db = MagicMock()
    return client


class TestStrategyLineage:
    def test_create_strategy_node(self, fake_client):
        lineage = StrategyLineage(fake_client)
        lineage.create_strategy_node(
            strategy_id="dip_buy_-7_2_24",
            template="dip_buy",
            params={"drop_pct": -7, "recovery_pct": 2},
            return_pct=23.82,
            win_rate=1.0,
        )
        assert len(fake_client._graph.queries) == 1
        q = fake_client._graph.queries[0]
        assert "MERGE (s:Strategy" in q["cypher"]
        assert q["params"]["id"] == "dip_buy_-7_2_24"

    def test_add_mutation(self, fake_client):
        lineage = StrategyLineage(fake_client)
        lineage.add_mutation(
            parent_id="dip_buy_v1",
            child_id="dip_buy_v2",
            mutation_type="param_change",
            param_changes="drop_pct: -5 → -7",
        )
        q = fake_client._graph.queries[0]
        assert "MUTATED_TO" in q["cypher"]

    def test_add_outperformed(self, fake_client):
        lineage = StrategyLineage(fake_client)
        lineage.add_outperformed("winner", "loser", "7d", 15.5)
        q = fake_client._graph.queries[0]
        assert "OUTPERFORMED" in q["cypher"]

    def test_get_ancestors(self, fake_client):
        fake_client._graph.set_result([
            ["dip_buy_v1", "dip_buy", 10.5, 2],
            ["dip_buy_v0", "dip_buy", 5.0, 1],
        ])
        lineage = StrategyLineage(fake_client)
        ancestors = lineage.get_ancestors("dip_buy_v3")
        assert len(ancestors) == 2
        assert ancestors[0]["id"] == "dip_buy_v1"

    def test_get_top_strategies(self, fake_client):
        fake_client._graph.set_result([
            ["dip_buy_-7_2_24", "dip_buy", 23.82, 1.0],
        ])
        lineage = StrategyLineage(fake_client)
        top = lineage.get_top_strategies(min_return=10.0)
        assert len(top) == 1
        assert top[0]["return_pct"] == 23.82

    def test_get_common_ancestor_params(self, fake_client):
        fake_client._graph.set_result([
            ["dip_buy_-7", "{'drop_pct': -7}", 5],
        ])
        lineage = StrategyLineage(fake_client)
        result = lineage.get_common_ancestor_params()
        assert result[0]["successful_descendants"] == 5


class TestCoinNetwork:
    def test_upsert_coin(self, fake_client):
        network = CoinNetwork(fake_client)
        network.upsert_coin("KRW-BTC", name="Bitcoin", sector="L1")
        q = fake_client._graph.queries[0]
        assert "MERGE (c:Coin" in q["cypher"]

    def test_set_correlation(self, fake_client):
        network = CoinNetwork(fake_client)
        network.set_correlation("KRW-BTC", "KRW-ETH", 0.87, lag_minutes=5)
        q = fake_client._graph.queries[0]
        assert "CORRELATES" in q["cypher"]

    def test_get_correlated_coins(self, fake_client):
        fake_client._graph.set_result([
            ["KRW-ETH", 0.87, 5],
            ["KRW-SOL", 0.72, 10],
        ])
        network = CoinNetwork(fake_client)
        correlated = network.get_correlated_coins("KRW-BTC")
        assert len(correlated) == 2
        assert correlated[0]["ticker"] == "KRW-ETH"
        assert correlated[0]["coefficient"] == 0.87

    def test_set_same_sector(self, fake_client):
        network = CoinNetwork(fake_client)
        network.set_same_sector("KRW-ETH", "KRW-SOL")
        q = fake_client._graph.queries[0]
        assert "SAME_SECTOR" in q["cypher"]

    def test_get_sector_coins(self, fake_client):
        fake_client._graph.set_result([["KRW-SOL"], ["KRW-AVAX"]])
        network = CoinNetwork(fake_client)
        peers = network.get_sector_coins("KRW-ETH")
        assert "KRW-SOL" in peers


class TestEventPropagation:
    def test_create_market_event(self, fake_client):
        ep = EventPropagation(fake_client)
        ep.create_market_event("NEW_LISTING", "COIN listed on Upbit", "2026-02-21T10:00:00")
        q = fake_client._graph.queries[0]
        assert "MarketEvent" in q["cypher"]

    def test_create_price_move(self, fake_client):
        ep = EventPropagation(fake_client)
        ep.create_price_move("KRW-BTC", -5.2, "2026-02-21T10:05:00")
        q = fake_client._graph.queries[0]
        assert "PriceMove" in q["cypher"]

    def test_link_event_to_move(self, fake_client):
        ep = EventPropagation(fake_client)
        ep.link_event_to_move(
            "NEW_LISTING", "2026-02-21T10:00:00",
            "KRW-NEWCOIN", "2026-02-21T10:05:00",
            lag_minutes=5, price_impact_pct=15.3,
        )
        q = fake_client._graph.queries[0]
        assert "TRIGGERED" in q["cypher"]

    def test_get_event_impact(self, fake_client):
        fake_client._graph.set_result([[15.3, 5.0, 10]])
        ep = EventPropagation(fake_client)
        impact = ep.get_event_impact("NEW_LISTING")
        assert len(impact) == 1
        assert impact[0]["avg_impact"] == 15.3
        assert impact[0]["sample_count"] == 10

    def test_get_cascade_chain(self, fake_client):
        fake_client._graph.set_result([
            ["KRW-ETH", -3.5, "2026-02-21T10:10:00"],
            ["KRW-SOL", -2.1, "2026-02-21T10:15:00"],
        ])
        ep = EventPropagation(fake_client)
        chain = ep.get_cascade_chain("KRW-BTC", "2026-02-21T10:05:00")
        assert len(chain) == 2
        assert chain[0]["ticker"] == "KRW-ETH"

    def test_link_cascade(self, fake_client):
        ep = EventPropagation(fake_client)
        ep.link_cascade(
            "KRW-BTC", "2026-02-21T10:05:00",
            "KRW-ETH", "2026-02-21T10:10:00",
            lag_minutes=5, magnitude=0.65,
        )
        q = fake_client._graph.queries[0]
        assert "CASCADED" in q["cypher"]
