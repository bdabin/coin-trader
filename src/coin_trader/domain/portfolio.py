"""Portfolio management - buy/sell execution on portfolio state."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

import structlog

from coin_trader.domain.models import (
    Portfolio,
    Position,
    PositionStatus,
    Side,
    Trade,
)

logger = structlog.get_logger()


class PortfolioManager:
    """Manages portfolio state: execute buys/sells, track positions."""

    def __init__(self, portfolio: Portfolio, fee_rate: float = 0.05) -> None:
        self.portfolio = portfolio
        self.fee_rate = fee_rate / 100  # Convert from percentage

    def execute_buy(
        self,
        strategy_name: str,
        ticker: str,
        price: Decimal,
        krw_amount: Decimal,
        reason: str = "",
    ) -> Optional[Trade]:
        """Execute a buy order. Returns Trade or None if insufficient funds."""
        if self.portfolio.krw_balance < krw_amount:
            logger.warning("portfolio.insufficient_funds", ticker=ticker)
            return None

        fee = krw_amount * Decimal(str(self.fee_rate))
        net_amount = krw_amount - fee
        quantity = net_amount / price

        # Deduct KRW
        self.portfolio.krw_balance -= krw_amount

        # Create position
        position = Position(
            strategy_name=strategy_name,
            ticker=ticker,
            entry_price=price,
            quantity=quantity,
            highest_price=price,
        )
        self.portfolio.positions[ticker] = position

        trade = Trade(
            strategy_name=strategy_name,
            ticker=ticker,
            side=Side.BUY,
            price=price,
            quantity=quantity,
            total_krw=krw_amount,
            fee=fee,
            reason=reason,
        )

        logger.info(
            "portfolio.buy",
            ticker=ticker,
            price=str(price),
            quantity=str(quantity),
            fee=str(fee),
        )
        return trade

    def execute_sell(
        self,
        strategy_name: str,
        ticker: str,
        price: Decimal,
        reason: str = "",
    ) -> Optional[Trade]:
        """Execute a sell order for full position. Returns Trade or None."""
        if ticker not in self.portfolio.positions:
            logger.warning("portfolio.no_position", ticker=ticker)
            return None

        position = self.portfolio.positions[ticker]
        if position.status != PositionStatus.OPEN:
            return None

        gross_krw = position.quantity * price
        fee = gross_krw * Decimal(str(self.fee_rate))
        net_krw = gross_krw - fee

        # Cost basis includes buy-side fee: quantity came from (krw - buy_fee) / price,
        # so the true cost is the full KRW amount spent (quantity * entry_price + buy_fee).
        # Simplified: cost = quantity * entry_price / (1 - fee_rate)
        raw_cost = position.quantity * position.entry_price
        fee_dec = Decimal(str(self.fee_rate))
        buy_fee = raw_cost * fee_dec / (Decimal("1") - fee_dec)
        cost = raw_cost + buy_fee
        profit = net_krw - cost
        profit_pct = float(profit / cost * 100) if cost > 0 else 0.0

        # Update portfolio
        self.portfolio.krw_balance += net_krw
        self.portfolio.total_trades += 1
        self.portfolio.total_profit += profit
        if profit > 0:
            self.portfolio.winning_trades += 1

        # Close position
        position.status = PositionStatus.CLOSED
        position.exit_price = price
        position.exit_time = datetime.utcnow()
        position.profit = profit
        position.profit_pct = profit_pct

        trade = Trade(
            strategy_name=strategy_name,
            ticker=ticker,
            side=Side.SELL,
            price=price,
            quantity=position.quantity,
            total_krw=net_krw,
            fee=fee,
            reason=reason,
            profit=profit,
            profit_pct=profit_pct,
        )

        logger.info(
            "portfolio.sell",
            ticker=ticker,
            price=str(price),
            profit=str(profit),
            profit_pct=f"{profit_pct:.2f}%",
        )
        return trade

    def update_highest_price(self, ticker: str, price: Decimal) -> None:
        """Update highest price for trailing stop tracking."""
        if ticker in self.portfolio.positions:
            pos = self.portfolio.positions[ticker]
            if pos.status == PositionStatus.OPEN and (
                pos.highest_price is None or price > pos.highest_price
            ):
                pos.highest_price = price

    def get_open_positions(self) -> Dict[str, Position]:
        """Return all open positions."""
        return {
            t: p for t, p in self.portfolio.positions.items()
            if p.status == PositionStatus.OPEN
        }
