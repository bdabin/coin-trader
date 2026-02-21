"""Daily performance report generation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

from coin_trader.domain.models import Portfolio, Trade


class DailyReport:
    """Generate daily trading performance reports."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def generate(
        self,
        portfolio: Portfolio,
        trades: List[Trade],
        prices: Dict[str, Decimal],
    ) -> Dict[str, Any]:
        """Generate report data."""
        total_value = portfolio.total_value(prices)
        initial = Decimal("1000000")
        return_pct = float((total_value - initial) / initial * 100)

        today_trades = [t for t in trades if t.timestamp.date() == datetime.utcnow().date()]
        today_sells = [t for t in today_trades if t.profit is not None]
        today_pnl = sum((t.profit for t in today_sells if t.profit), Decimal("0"))

        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "total_value": str(total_value),
            "return_pct": return_pct,
            "krw_balance": str(portfolio.krw_balance),
            "open_positions": len([
                p for p in portfolio.positions.values() if p.status.value == "OPEN"
            ]),
            "total_trades": portfolio.total_trades,
            "win_rate": portfolio.win_rate,
            "today_trades": len(today_trades),
            "today_pnl": str(today_pnl),
        }

    def print_report(
        self,
        portfolio: Portfolio,
        trades: List[Trade],
        prices: Dict[str, Decimal],
    ) -> None:
        """Print formatted report to console."""
        data = self.generate(portfolio, trades, prices)

        self.console.print("\n[bold]Daily Trading Report[/bold]")
        self.console.print(f"Date: {data['date']}")

        table = Table(show_header=True)
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        table.add_row("Total Value", f"{data['total_value']} KRW")
        table.add_row("Return", f"{data['return_pct']:.2f}%")
        table.add_row("KRW Balance", f"{data['krw_balance']} KRW")
        table.add_row("Open Positions", str(data['open_positions']))
        table.add_row("Total Trades", str(data['total_trades']))
        table.add_row("Win Rate", f"{data['win_rate']:.1%}")
        table.add_row("Today Trades", str(data['today_trades']))
        table.add_row("Today P&L", f"{data['today_pnl']} KRW")

        self.console.print(table)
