"""Paper trading executor — simulates trades without real money."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

from coin_trader.config import AppConfig
from coin_trader.domain.models import Portfolio, Trade
from coin_trader.domain.portfolio import PortfolioManager
from coin_trader.domain.risk import RiskManager
from coin_trader.domain.strategy import Strategy
from coin_trader.execution.engine import ExecutionEngine

logger = structlog.get_logger()


class PaperTrader:
    """Paper trading simulator wrapping the ExecutionEngine."""

    def __init__(
        self,
        config: AppConfig,
        strategies: List[Strategy],
    ) -> None:
        self.config = config
        portfolio = Portfolio(krw_balance=Decimal(str(config.trading.initial_krw)))
        self.portfolio_manager = PortfolioManager(portfolio, config.risk.fee_rate)
        self.risk_manager = RiskManager(config.risk)
        self.engine = ExecutionEngine(
            config=config,
            portfolio_manager=self.portfolio_manager,
            risk_manager=self.risk_manager,
            strategies=strategies,
        )

    async def process_tick(self, tick: Dict[str, Any]) -> List[Trade]:
        """Process tick through paper engine."""
        return await self.engine.process_tick(tick)

    def get_portfolio(self) -> Portfolio:
        """Get current portfolio state."""
        return self.portfolio_manager.portfolio

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return self.engine.get_summary()
