"""Live trading executor — Phase 2, uses real Upbit API."""

from __future__ import annotations

from typing import Any, Dict

import structlog

logger = structlog.get_logger()


class LiveTrader:
    """Live trading executor using Upbit API.

    Phase 2: Only enabled after paper trading validation.
    """

    def __init__(self, access_key: str, secret_key: str) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self._upbit: Any = None

    def _get_upbit(self) -> Any:
        if self._upbit is None:
            import pyupbit
            self._upbit = pyupbit.Upbit(self.access_key, self.secret_key)
        return self._upbit

    async def buy_market(self, ticker: str, krw_amount: float) -> Dict[str, Any]:
        """Execute market buy order."""
        logger.warning("live.buy_market", ticker=ticker, amount=krw_amount)
        upbit = self._get_upbit()
        result = upbit.buy_market_order(ticker, krw_amount)
        logger.info("live.buy_executed", result=result)
        return result or {}

    async def sell_market(self, ticker: str, quantity: float) -> Dict[str, Any]:
        """Execute market sell order."""
        logger.warning("live.sell_market", ticker=ticker, quantity=quantity)
        upbit = self._get_upbit()
        result = upbit.sell_market_order(ticker, quantity)
        logger.info("live.sell_executed", result=result)
        return result or {}

    async def get_balance(self, ticker: str = "KRW") -> float:
        """Get balance for a ticker."""
        upbit = self._get_upbit()
        balance = upbit.get_balance(ticker)
        return float(balance) if balance else 0.0
