"""Strategy leaderboard ranking."""

from __future__ import annotations

from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table


class Leaderboard:
    """Rank and display strategy performance."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def rank(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank strategies by return percentage."""
        return sorted(strategies, key=lambda s: s.get("return_pct", 0), reverse=True)

    def print_leaderboard(self, strategies: List[Dict[str, Any]], top_n: int = 10) -> None:
        """Print leaderboard table."""
        ranked = self.rank(strategies)[:top_n]

        table = Table(title="Strategy Leaderboard", show_header=True)
        table.add_column("#", justify="right", width=3)
        table.add_column("Strategy")
        table.add_column("Template")
        table.add_column("Return %", justify="right")
        table.add_column("Win Rate", justify="right")
        table.add_column("Trades", justify="right")
        table.add_column("Status")

        for i, s in enumerate(ranked, 1):
            return_pct = s.get("return_pct", 0)
            color = "green" if return_pct > 0 else "red"
            table.add_row(
                str(i),
                s.get("name", "?"),
                s.get("template", "?"),
                f"[{color}]{return_pct:.2f}%[/{color}]",
                f"{s.get('win_rate', 0):.1%}",
                str(s.get("total_trades", 0)),
                s.get("status", "ACTIVE"),
            )

        self.console.print(table)
