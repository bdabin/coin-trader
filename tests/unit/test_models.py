"""Tests for domain models."""

from decimal import Decimal

import pytest

from coin_trader.domain.models import (
    AIDecision,
    MarketSnapshot,
    Portfolio,
    Position,
    PositionStatus,
    Side,
    Signal,
    SignalType,
    StrategyConfig,
    StrategyStatus,
    Trade,
)


class TestSignal:
    def test_create_buy_signal(self):
        signal = Signal(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            signal_type=SignalType.BUY,
            strength=0.8,
            reason="Dip -7%",
        )
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.8
        assert signal.ticker == "KRW-BTC"

    def test_strength_bounds(self):
        with pytest.raises(ValueError):
            Signal(
                strategy_name="test",
                ticker="KRW-BTC",
                signal_type=SignalType.BUY,
                strength=1.5,
            )
        with pytest.raises(ValueError):
            Signal(
                strategy_name="test",
                ticker="KRW-BTC",
                signal_type=SignalType.BUY,
                strength=-0.1,
            )

    def test_signal_with_params(self):
        signal = Signal(
            strategy_name="dip_buy",
            ticker="KRW-ETH",
            signal_type=SignalType.SELL,
            strength=0.6,
            params={"drop_pct": -7, "recovery_pct": 2},
        )
        assert signal.params["drop_pct"] == -7


class TestTrade:
    def test_create_buy_trade(self):
        trade = Trade(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            side=Side.BUY,
            price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            total_krw=Decimal("100000"),
            fee=Decimal("50"),
            reason="Dip buy triggered",
        )
        assert trade.side == Side.BUY
        assert trade.total_krw == Decimal("100000")
        assert trade.id is not None

    def test_sell_trade_with_profit(self):
        trade = Trade(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            side=Side.SELL,
            price=Decimal("52000000"),
            quantity=Decimal("0.002"),
            total_krw=Decimal("104000"),
            fee=Decimal("52"),
            profit=Decimal("3948"),
            profit_pct=3.95,
        )
        assert trade.profit == Decimal("3948")
        assert trade.profit_pct == 3.95


class TestPosition:
    def test_create_position(self):
        pos = Position(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
        )
        assert pos.status == PositionStatus.OPEN
        assert pos.cost == Decimal("100000")

    def test_cost_calculation(self):
        pos = Position(
            strategy_name="momentum",
            ticker="KRW-ETH",
            entry_price=Decimal("4000000"),
            quantity=Decimal("0.025"),
        )
        assert pos.cost == Decimal("100000")


class TestPortfolio:
    def test_empty_portfolio(self, empty_portfolio):
        assert empty_portfolio.krw_balance == Decimal("1000000")
        assert empty_portfolio.win_rate == 0.0
        assert empty_portfolio.total_value({}) == Decimal("1000000")

    def test_portfolio_with_position(self, portfolio_with_position):
        prices = {"KRW-BTC": Decimal("55000000")}
        pos_value = portfolio_with_position.position_value(prices)
        assert pos_value == Decimal("110000")

        total = portfolio_with_position.total_value(prices)
        assert total == Decimal("1010000")

    def test_win_rate(self):
        portfolio = Portfolio(
            krw_balance=Decimal("1000000"),
            total_trades=10,
            winning_trades=7,
        )
        assert portfolio.win_rate == 0.7

    def test_position_value_uses_entry_price_as_fallback(self, portfolio_with_position):
        # No current price provided → uses entry_price
        pos_value = portfolio_with_position.position_value({})
        assert pos_value == Decimal("100000")


class TestMarketSnapshot:
    def test_create_snapshot(self):
        snap = MarketSnapshot(
            ticker="KRW-BTC",
            price=Decimal("50000000"),
            change_pct=-2.5,
        )
        assert snap.ticker == "KRW-BTC"
        assert snap.change_pct == -2.5


class TestAIDecision:
    def test_create_decision(self):
        decision = AIDecision(
            model="claude-opus-4-6",
            ticker="KRW-BTC",
            decision="EXECUTE",
            reasoning="Strong dip buy signal with favorable market conditions",
            confidence=0.85,
            market_context={"fear_greed": "25", "btc_dominance": "42.5"},
        )
        assert decision.confidence == 0.85
        assert decision.decision == "EXECUTE"

    def test_confidence_bounds(self):
        with pytest.raises(ValueError):
            AIDecision(
                model="test",
                ticker="KRW-BTC",
                decision="SKIP",
                reasoning="test",
                confidence=1.5,
            )


class TestStrategyConfig:
    def test_create_config(self):
        cfg = StrategyConfig(
            name="dip_buy_-7_2_24",
            template="dip_buy",
            params={"drop_pct": -7, "recovery_pct": 2, "timeframe_hours": 24},
        )
        assert cfg.status == StrategyStatus.ACTIVE
        assert cfg.params["drop_pct"] == -7
