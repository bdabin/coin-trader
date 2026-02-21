"""Tests for portfolio management."""

from __future__ import annotations

from decimal import Decimal

import pytest

from coin_trader.domain.models import Portfolio, PositionStatus, Side
from coin_trader.domain.portfolio import PortfolioManager


@pytest.fixture
def pm():
    portfolio = Portfolio(krw_balance=Decimal("1000000"))
    return PortfolioManager(portfolio, fee_rate=0.05)


class TestBuy:
    def test_execute_buy(self, pm):
        trade = pm.execute_buy(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            price=Decimal("50000000"),
            krw_amount=Decimal("100000"),
            reason="Dip -7%",
        )
        assert trade is not None
        assert trade.side == Side.BUY
        assert trade.fee == Decimal("50")  # 0.05% of 100k
        assert trade.quantity == Decimal("99950") / Decimal("50000000")
        assert pm.portfolio.krw_balance == Decimal("900000")
        assert "KRW-BTC" in pm.portfolio.positions

    def test_buy_insufficient_funds(self, pm):
        pm.portfolio.krw_balance = Decimal("50000")
        trade = pm.execute_buy(
            strategy_name="test",
            ticker="KRW-BTC",
            price=Decimal("50000000"),
            krw_amount=Decimal("100000"),
        )
        assert trade is None

    def test_multiple_buys(self, pm):
        pm.execute_buy("s1", "KRW-BTC", Decimal("50000000"), Decimal("100000"))
        pm.execute_buy("s1", "KRW-ETH", Decimal("4000000"), Decimal("100000"))
        assert pm.portfolio.krw_balance == Decimal("800000")
        assert len(pm.portfolio.positions) == 2


class TestSell:
    def test_execute_sell(self, pm):
        pm.execute_buy("dip_buy", "KRW-BTC", Decimal("50000000"), Decimal("100000"))
        trade = pm.execute_sell(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            price=Decimal("55000000"),  # +10% gain
            reason="Recovery +10%",
        )
        assert trade is not None
        assert trade.side == Side.SELL
        assert trade.profit is not None
        assert trade.profit > 0
        assert pm.portfolio.total_trades == 1
        assert pm.portfolio.winning_trades == 1
        pos = pm.portfolio.positions["KRW-BTC"]
        assert pos.status == PositionStatus.CLOSED

    def test_sell_no_position(self, pm):
        trade = pm.execute_sell("test", "KRW-BTC", Decimal("50000000"))
        assert trade is None

    def test_sell_losing_trade(self, pm):
        pm.execute_buy("test", "KRW-BTC", Decimal("50000000"), Decimal("100000"))
        trade = pm.execute_sell("test", "KRW-BTC", Decimal("45000000"))
        assert trade is not None
        assert trade.profit is not None
        assert trade.profit < 0
        assert pm.portfolio.winning_trades == 0


class TestHighestPrice:
    def test_update_highest(self, pm):
        pm.execute_buy("test", "KRW-BTC", Decimal("50000000"), Decimal("100000"))
        pm.update_highest_price("KRW-BTC", Decimal("55000000"))
        assert pm.portfolio.positions["KRW-BTC"].highest_price == Decimal("55000000")

    def test_no_update_lower(self, pm):
        pm.execute_buy("test", "KRW-BTC", Decimal("50000000"), Decimal("100000"))
        pm.update_highest_price("KRW-BTC", Decimal("55000000"))
        pm.update_highest_price("KRW-BTC", Decimal("53000000"))
        assert pm.portfolio.positions["KRW-BTC"].highest_price == Decimal("55000000")

    def test_update_nonexistent(self, pm):
        # Should not raise
        pm.update_highest_price("KRW-BTC", Decimal("50000000"))


class TestOpenPositions:
    def test_get_open(self, pm):
        pm.execute_buy("test", "KRW-BTC", Decimal("50000000"), Decimal("100000"))
        pm.execute_buy("test", "KRW-ETH", Decimal("4000000"), Decimal("100000"))
        pm.execute_sell("test", "KRW-BTC", Decimal("51000000"))
        open_pos = pm.get_open_positions()
        assert len(open_pos) == 1
        assert "KRW-ETH" in open_pos
