"""Tests for reporting modules."""

from __future__ import annotations

from decimal import Decimal

import pytest

from coin_trader.domain.models import Portfolio, Position, PositionStatus
from coin_trader.reporting.daily_report import DailyReport
from coin_trader.reporting.leaderboard import Leaderboard


class TestDailyReport:
    def test_generate_empty_portfolio(self):
        report = DailyReport()
        portfolio = Portfolio()
        data = report.generate(portfolio, [], {})
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0.0
        assert data["open_positions"] == 0

    def test_generate_with_positions(self):
        report = DailyReport()
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
        )
        portfolio = Portfolio(
            krw_balance=Decimal("900000"),
            positions={"KRW-BTC": pos},
            total_trades=5,
            winning_trades=3,
        )
        prices = {"KRW-BTC": Decimal("55000000")}
        data = report.generate(portfolio, [], prices)
        assert data["open_positions"] == 1
        assert data["total_trades"] == 5
        assert data["win_rate"] == 0.6


class TestLeaderboard:
    def test_rank(self):
        board = Leaderboard()
        strategies = [
            {"name": "a", "return_pct": 5.0},
            {"name": "b", "return_pct": 23.82},
            {"name": "c", "return_pct": -10.0},
        ]
        ranked = board.rank(strategies)
        assert ranked[0]["name"] == "b"
        assert ranked[-1]["name"] == "c"

    def test_rank_empty(self):
        board = Leaderboard()
        assert board.rank([]) == []
