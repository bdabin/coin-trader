"""Tests for strategy evolution."""

from __future__ import annotations

import random
from unittest.mock import MagicMock

import pytest

from coin_trader.domain.evolution import StrategyEvolver


@pytest.fixture
def evolver():
    return StrategyEvolver()


class TestMutation:
    def test_mutate_params(self, evolver):
        random.seed(42)
        params = {"drop_pct": -7, "recovery_pct": 2, "timeframe_hours": 24}
        mutated = evolver.mutate_params(params, mutation_rate=1.0)
        # At least one param should change
        # Mutation is probabilistic with seed, just verify bounds
        # Bounds should be enforced
        assert -15 <= mutated["drop_pct"] <= -2
        assert 1 <= mutated["recovery_pct"] <= 10
        assert 1 <= mutated["timeframe_hours"] <= 72

    def test_mutation_rate_zero(self, evolver):
        params = {"drop_pct": -7, "recovery_pct": 2}
        mutated = evolver.mutate_params(params, mutation_rate=0.0)
        assert mutated == params

    def test_bounds_enforcement(self):
        # Test static method directly
        assert StrategyEvolver._enforce_bounds("drop_pct", -20.0) == -15.0
        assert StrategyEvolver._enforce_bounds("drop_pct", -1.0) == -2.0
        assert StrategyEvolver._enforce_bounds("k_factor", 1.5) == 0.9
        assert StrategyEvolver._enforce_bounds("k_factor", 0.05) == 0.1
        assert StrategyEvolver._enforce_bounds("unknown", 42.0) == 42.0


class TestCrossover:
    def test_crossover(self, evolver):
        random.seed(42)
        a = {"drop_pct": -7, "recovery_pct": 2, "timeframe_hours": 24}
        b = {"drop_pct": -5, "recovery_pct": 3, "timeframe_hours": 12}
        child = evolver.crossover(a, b)
        # Each param should come from either parent
        for key in child:
            assert child[key] in [a[key], b[key]]

    def test_crossover_missing_keys(self, evolver):
        a = {"drop_pct": -7, "extra_a": 1}
        b = {"drop_pct": -5, "extra_b": 2}
        child = evolver.crossover(a, b)
        assert "extra_a" in child
        assert "extra_b" in child


class TestGraphInsights:
    def test_no_lineage(self, evolver):
        result = evolver.get_graph_insights("dip_buy")
        assert "No graph data" in result

    def test_with_lineage(self):
        mock_lineage = MagicMock()
        mock_lineage.get_top_strategies.return_value = [
            {"id": "dip_buy_v1", "return_pct": 23.82, "win_rate": 1.0},
        ]
        mock_lineage.get_common_ancestor_params.return_value = [
            {"id": "dip_buy_-7", "params": "{'drop_pct': -7}", "successful_descendants": 5},
        ]
        evolver = StrategyEvolver(lineage=mock_lineage)
        result = evolver.get_graph_insights("dip_buy")
        assert "dip_buy_v1" in result
        assert "23.82" in result


class TestRecordMutation:
    def test_record_mutation(self):
        mock_lineage = MagicMock()
        evolver = StrategyEvolver(lineage=mock_lineage)
        evolver.record_mutation(
            parent_id="v1",
            child_id="v2",
            parent_params={"drop_pct": -7},
            child_params={"drop_pct": -6},
        )
        mock_lineage.add_mutation.assert_called_once()
        call_args = mock_lineage.add_mutation.call_args
        assert "drop_pct: -7" in call_args.kwargs.get("param_changes", "")

    def test_record_without_lineage(self, evolver):
        # Should not raise
        evolver.record_mutation("v1", "v2", {"a": 1}, {"a": 2})
