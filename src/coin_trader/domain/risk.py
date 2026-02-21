"""Risk management engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from coin_trader.config import RiskConfig
from coin_trader.domain.models import Portfolio, Position, PositionStatus, Signal, SignalType


@dataclass
class RiskCheck:
    """Result of a risk check."""

    allowed: bool
    reason: str = ""


@dataclass
class DailyPnL:
    """Daily profit/loss tracker."""

    date: date = field(default_factory=lambda: datetime.utcnow().date())
    realized_pnl: Decimal = Decimal("0")
    trades_today: int = 0


class RiskManager:
    """Enforces risk rules on trading decisions."""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.daily_pnl = DailyPnL()

    def _reset_daily_if_needed(self) -> None:
        today = datetime.utcnow().date()
        if self.daily_pnl.date != today:
            self.daily_pnl = DailyPnL(date=today)

    def check_buy(
        self,
        signal: Signal,
        portfolio: Portfolio,
        buy_amount: Decimal,
    ) -> RiskCheck:
        """Check if a buy signal passes all risk rules."""
        self._reset_daily_if_needed()

        if signal.signal_type != SignalType.BUY:
            return RiskCheck(allowed=False, reason="Not a BUY signal")

        # Max positions check
        open_count = sum(
            1 for p in portfolio.positions.values() if p.status == PositionStatus.OPEN
        )
        if open_count >= self.config.max_positions:
            return RiskCheck(
                allowed=False,
                reason=f"Max positions reached ({self.config.max_positions})",
            )

        # Sufficient balance
        if portfolio.krw_balance < buy_amount:
            return RiskCheck(
                allowed=False,
                reason=f"Insufficient balance: {portfolio.krw_balance} < {buy_amount}",
            )

        # Daily loss limit
        initial = Decimal("1000000")
        daily_loss_pct = float(self.daily_pnl.realized_pnl / initial * 100) if initial else 0.0
        if daily_loss_pct <= self.config.max_daily_loss_pct:
            return RiskCheck(
                allowed=False,
                reason=f"Daily loss limit hit: {daily_loss_pct:.2f}%",
            )

        # Max drawdown
        if portfolio.total_trades > 0:
            return_pct = float(portfolio.total_profit / initial * 100)
            if return_pct <= self.config.max_drawdown_pct:
                return RiskCheck(
                    allowed=False,
                    reason=f"Max drawdown hit: {return_pct:.2f}%",
                )

        # Duplicate position check
        if signal.ticker in portfolio.positions:
            pos = portfolio.positions[signal.ticker]
            if pos.status == PositionStatus.OPEN:
                return RiskCheck(
                    allowed=False,
                    reason=f"Already have open position in {signal.ticker}",
                )

        return RiskCheck(allowed=True)

    def check_sell(self, signal: Signal, portfolio: Portfolio) -> RiskCheck:
        """Check if a sell signal is valid."""
        if signal.signal_type != SignalType.SELL:
            return RiskCheck(allowed=False, reason="Not a SELL signal")

        if signal.ticker not in portfolio.positions:
            return RiskCheck(allowed=False, reason=f"No position in {signal.ticker}")

        pos = portfolio.positions[signal.ticker]
        if pos.status != PositionStatus.OPEN:
            return RiskCheck(allowed=False, reason=f"Position in {signal.ticker} is not open")

        return RiskCheck(allowed=True)

    def check_stop_loss(self, position: Position, current_price: Decimal) -> RiskCheck:
        """Check if stop-loss should trigger."""
        if position.status != PositionStatus.OPEN:
            return RiskCheck(allowed=False, reason="Position not open")

        change_pct = float((current_price - position.entry_price) / position.entry_price * 100)
        if change_pct <= self.config.stop_loss_pct:
            return RiskCheck(
                allowed=True,
                reason=f"Stop-loss triggered: {change_pct:.2f}% <= {self.config.stop_loss_pct}%",
            )
        return RiskCheck(allowed=False)

    def check_take_profit(self, position: Position, current_price: Decimal) -> RiskCheck:
        """Check if take-profit should trigger."""
        if position.status != PositionStatus.OPEN:
            return RiskCheck(allowed=False, reason="Position not open")

        change_pct = float((current_price - position.entry_price) / position.entry_price * 100)
        if change_pct >= self.config.take_profit_pct:
            return RiskCheck(
                allowed=True,
                reason=(
                    f"Take-profit triggered: {change_pct:.2f}% >= {self.config.take_profit_pct}%"
                ),
            )
        return RiskCheck(allowed=False)

    def check_trailing_stop(self, position: Position, current_price: Decimal) -> RiskCheck:
        """Check if trailing stop should trigger."""
        if position.status != PositionStatus.OPEN:
            return RiskCheck(allowed=False, reason="Position not open")

        highest = position.highest_price or position.entry_price
        if current_price > highest:
            return RiskCheck(allowed=False, reason="New high, no trailing stop")

        drop_from_high = float((highest - current_price) / highest * 100)
        if drop_from_high >= self.config.trailing_stop_pct:
            return RiskCheck(
                allowed=True,
                reason=(
                    f"Trailing stop: dropped {drop_from_high:.2f}% from high "
                    f">= {self.config.trailing_stop_pct}%"
                ),
            )
        return RiskCheck(allowed=False)

    def record_trade_pnl(self, pnl: Decimal) -> None:
        """Record realized P&L for daily tracking."""
        self._reset_daily_if_needed()
        self.daily_pnl.realized_pnl += pnl
        self.daily_pnl.trades_today += 1
