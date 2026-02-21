"""AI orchestrator — coordinates Opus (strategy) + Codex (engineering)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from coin_trader.ai.codex_engineer import CodexEngineer
from coin_trader.ai.opus_analyst import OpusAnalyst
from coin_trader.domain.models import AIDecision, Signal

logger = structlog.get_logger()


class AIOrchestrator:
    """Coordinates Opus 4.6 (strategic decisions) and Codex 5.3 (engineering)."""

    def __init__(
        self,
        opus: Optional[OpusAnalyst] = None,
        codex: Optional[CodexEngineer] = None,
    ) -> None:
        self.opus = opus
        self.codex = codex
        self._enabled = opus is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def evaluate_signal(
        self,
        signal: Signal,
        market_context: Dict[str, Any],
    ) -> Optional[AIDecision]:
        """Have Opus evaluate a signal for execution."""
        if not self.opus:
            return None

        try:
            decision = await self.opus.evaluate_signal(signal, market_context)
            logger.info(
                "ai.signal_evaluated",
                ticker=signal.ticker,
                decision=decision.decision,
                confidence=decision.confidence,
            )
            return decision
        except Exception as e:
            logger.error("ai.evaluate_error", error=str(e))
            return None

    async def analyze_market(self, context: Dict[str, Any]) -> str:
        """Get market analysis from Opus."""
        if not self.opus:
            return "AI not configured"
        return await self.opus.analyze_market(context)

    async def discuss(self, message: str) -> str:
        """Free-form discussion with Opus."""
        if not self.opus:
            return "AI not configured"
        return await self.opus.discuss(message)

    async def generate_backtest(
        self,
        strategy_name: str,
        template: str,
        params: Dict[str, Any],
    ) -> str:
        """Have Codex generate backtest code."""
        if not self.codex:
            return "Codex not configured"
        return await self.codex.generate_backtest(strategy_name, template, params)

    async def evolve_strategy(
        self,
        parent_name: str,
        parent_params: Dict[str, Any],
        parent_return: float,
        graph_insights: str = "",
    ) -> str:
        """Use Codex to generate strategy mutations, informed by graph data."""
        if not self.codex:
            return "Codex not configured"
        return await self.codex.generate_mutations(
            parent_name=parent_name,
            parent_params=parent_params,
            parent_return=parent_return,
            ancestor_patterns=graph_insights,
        )
