"""Strategy lineage tracking in FalkorDB."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from coin_trader.graph.client import GraphClient

logger = structlog.get_logger()


class StrategyLineage:
    """Track strategy evolution lineage in graph DB."""

    def __init__(self, client: GraphClient) -> None:
        self.client = client

    def create_strategy_node(
        self,
        strategy_id: str,
        template: str,
        params: Dict[str, Any],
        sharpe: Optional[float] = None,
        win_rate: Optional[float] = None,
        return_pct: Optional[float] = None,
        status: str = "ACTIVE",
    ) -> None:
        """Create a strategy node."""
        self.client.query(
            """MERGE (s:Strategy {id: $id})
               SET s.template = $template,
                   s.params = $params,
                   s.sharpe = $sharpe,
                   s.win_rate = $win_rate,
                   s.return_pct = $return_pct,
                   s.status = $status""",
            {
                "id": strategy_id,
                "template": template,
                "params": str(params),
                "sharpe": sharpe or 0.0,
                "win_rate": win_rate or 0.0,
                "return_pct": return_pct or 0.0,
                "status": status,
            },
        )

    def add_mutation(
        self,
        parent_id: str,
        child_id: str,
        mutation_type: str,
        param_changes: str,
    ) -> None:
        """Record a strategy mutation (parent → child)."""
        self.client.query(
            """MATCH (parent:Strategy {id: $parent_id})
               MATCH (child:Strategy {id: $child_id})
               MERGE (parent)-[:MUTATED_TO {
                   mutation_type: $mutation_type,
                   param_changes: $param_changes
               }]->(child)""",
            {
                "parent_id": parent_id,
                "child_id": child_id,
                "mutation_type": mutation_type,
                "param_changes": param_changes,
            },
        )

    def add_outperformed(
        self, winner_id: str, loser_id: str, period: str, margin_pct: float
    ) -> None:
        """Record that one strategy outperformed another."""
        self.client.query(
            """MATCH (w:Strategy {id: $winner_id})
               MATCH (l:Strategy {id: $loser_id})
               MERGE (w)-[:OUTPERFORMED {period: $period, margin_pct: $margin_pct}]->(l)""",
            {
                "winner_id": winner_id,
                "loser_id": loser_id,
                "period": period,
                "margin_pct": margin_pct,
            },
        )

    def get_ancestors(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all ancestors of a strategy."""
        rows = self.client.query_result(
            """MATCH path=(ancestor:Strategy)-[:MUTATED_TO*]->(s:Strategy {id: $id})
               RETURN ancestor.id AS id, ancestor.template AS template,
                      ancestor.return_pct AS return_pct,
                      length(path) AS depth
               ORDER BY depth""",
            {"id": strategy_id},
        )
        return [
            {"id": r[0], "template": r[1], "return_pct": r[2], "depth": r[3]}
            for r in rows
        ]

    def get_top_strategies(self, min_return: float = 10.0) -> List[Dict[str, Any]]:
        """Get top performing strategies."""
        rows = self.client.query_result(
            """MATCH (s:Strategy)
               WHERE s.return_pct > $min_return
               RETURN s.id AS id, s.template AS template,
                      s.return_pct AS return_pct, s.win_rate AS win_rate
               ORDER BY s.return_pct DESC""",
            {"min_return": min_return},
        )
        return [
            {"id": r[0], "template": r[1], "return_pct": r[2], "win_rate": r[3]}
            for r in rows
        ]

    def get_common_ancestor_params(self, min_return: float = 10.0) -> List[Dict[str, Any]]:
        """Find common parameters in successful strategy lineages."""
        rows = self.client.query_result(
            """MATCH (ancestor:Strategy)-[:MUTATED_TO*]->(good:Strategy)
               WHERE good.return_pct > $min_return
               RETURN ancestor.id AS id, ancestor.params AS params,
                      count(good) AS successful_descendants
               ORDER BY successful_descendants DESC
               LIMIT 10""",
            {"min_return": min_return},
        )
        return [
            {"id": r[0], "params": r[1], "successful_descendants": r[2]}
            for r in rows
        ]
