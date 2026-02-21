"""AI-assisted strategy evolution with graph lineage tracking."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

import structlog

from coin_trader.graph.strategy_lineage import StrategyLineage

logger = structlog.get_logger()


class StrategyEvolver:
    """Evolve strategies using mutation + graph lineage analysis."""

    def __init__(self, lineage: Optional[StrategyLineage] = None) -> None:
        self.lineage = lineage

    def mutate_params(
        self,
        params: Dict[str, Any],
        mutation_rate: float = 0.3,
    ) -> Dict[str, Any]:
        """Mutate strategy parameters within reasonable bounds."""
        mutated = dict(params)

        for key, value in params.items():
            if random.random() > mutation_rate:
                continue

            if isinstance(value, (int, float)):
                # Gaussian mutation: +-20% of current value
                delta = value * random.gauss(0, 0.2)
                new_val = value + delta

                # Bounds enforcement
                new_val = self._enforce_bounds(key, new_val)

                if isinstance(value, int):
                    mutated[key] = int(round(new_val))
                else:
                    mutated[key] = round(new_val, 2)

        return mutated

    def crossover(
        self,
        params_a: Dict[str, Any],
        params_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Crossover two parameter sets."""
        result: Dict[str, Any] = {}
        all_keys = set(params_a.keys()) | set(params_b.keys())

        for key in all_keys:
            if key in params_a and key in params_b:
                result[key] = random.choice([params_a[key], params_b[key]])
            elif key in params_a:
                result[key] = params_a[key]
            else:
                result[key] = params_b[key]

        return result

    def get_graph_insights(self, template: str) -> str:
        """Get evolution insights from graph lineage."""
        if not self.lineage:
            return "No graph data available"

        try:
            top = self.lineage.get_top_strategies(min_return=5.0)
            ancestors = self.lineage.get_common_ancestor_params(min_return=10.0)

            lines = ["Top performing strategies:"]
            for s in top[:5]:
                lines.append(f"  - {s['id']}: return={s['return_pct']}%, win_rate={s['win_rate']}")

            lines.append("\nCommon ancestor parameters:")
            for a in ancestors[:3]:
                desc = a['successful_descendants']
                lines.append(f"  - {a['id']}: {a['params']} ({desc} descendants)")

            return "\n".join(lines)
        except Exception as e:
            logger.error("evolution.graph_error", error=str(e))
            return f"Graph query error: {e}"

    def record_mutation(
        self,
        parent_id: str,
        child_id: str,
        parent_params: Dict[str, Any],
        child_params: Dict[str, Any],
    ) -> None:
        """Record a mutation in the graph."""
        if not self.lineage:
            return

        changes = []
        for key in set(parent_params.keys()) | set(child_params.keys()):
            old = parent_params.get(key)
            new = child_params.get(key)
            if old != new:
                changes.append(f"{key}: {old} → {new}")

        self.lineage.add_mutation(
            parent_id=parent_id,
            child_id=child_id,
            mutation_type="parameter_mutation",
            param_changes="; ".join(changes),
        )

    @staticmethod
    def _enforce_bounds(key: str, value: float) -> float:
        """Enforce parameter bounds based on key name."""
        bounds = {
            "drop_pct": (-15.0, -2.0),
            "recovery_pct": (1.0, 10.0),
            "timeframe_hours": (1, 72),
            "lookback_hours": (1, 72),
            "entry_threshold": (1.0, 15.0),
            "exit_threshold": (-10.0, -1.0),
            "k_factor": (0.1, 0.9),
            "volume_multiplier": (1.5, 10.0),
            "buy_threshold": (5, 40),
            "sell_threshold": (60, 95),
        }

        if key in bounds:
            lo, hi = bounds[key]
            return max(lo, min(hi, value))
        return value
