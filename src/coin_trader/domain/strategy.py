"""Strategy protocol and base class."""

from __future__ import annotations

import abc
from typing import Any, Dict, Optional

from coin_trader.domain.models import Signal


class Strategy(abc.ABC):
    """Protocol for all trading strategies."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Strategy unique name."""

    @property
    @abc.abstractmethod
    def template(self) -> str:
        """Strategy template type (e.g. 'dip_buy')."""

    @abc.abstractmethod
    async def evaluate(
        self,
        ticker: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        """Evaluate strategy for a ticker. Returns Signal or None."""

    def describe(self) -> Dict[str, Any]:
        """Return strategy description for logging."""
        return {"name": self.name, "template": self.template}
