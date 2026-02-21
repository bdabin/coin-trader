"""Tests for risk management."""

from decimal import Decimal

from coin_trader.domain.models import (
    Portfolio,
    Position,
    PositionStatus,
    Signal,
    SignalType,
)


class TestRiskManagerBuy:
    def test_allows_valid_buy(self, risk_manager, empty_portfolio, buy_signal):
        result = risk_manager.check_buy(buy_signal, empty_portfolio, Decimal("100000"))
        assert result.allowed is True

    def test_rejects_sell_signal_as_buy(self, risk_manager, empty_portfolio, sell_signal):
        result = risk_manager.check_buy(sell_signal, empty_portfolio, Decimal("100000"))
        assert result.allowed is False
        assert "Not a BUY" in result.reason

    def test_rejects_when_max_positions(self, risk_manager, buy_signal):
        positions = {}
        for i in range(5):
            ticker = f"KRW-COIN{i}"
            positions[ticker] = Position(
                strategy_name="test",
                ticker=ticker,
                entry_price=Decimal("1000"),
                quantity=Decimal("1"),
            )
        portfolio = Portfolio(krw_balance=Decimal("500000"), positions=positions)

        signal = Signal(
            strategy_name="test",
            ticker="KRW-NEW",
            signal_type=SignalType.BUY,
            strength=0.5,
        )
        result = risk_manager.check_buy(signal, portfolio, Decimal("100000"))
        assert result.allowed is False
        assert "Max positions" in result.reason

    def test_rejects_insufficient_balance(self, risk_manager, buy_signal):
        portfolio = Portfolio(krw_balance=Decimal("50000"))
        result = risk_manager.check_buy(buy_signal, portfolio, Decimal("100000"))
        assert result.allowed is False
        assert "Insufficient" in result.reason

    def test_rejects_duplicate_position(self, risk_manager, buy_signal, portfolio_with_position):
        result = risk_manager.check_buy(
            buy_signal, portfolio_with_position, Decimal("100000")
        )
        assert result.allowed is False
        assert "Already have" in result.reason

    def test_rejects_when_daily_loss_limit(self, risk_manager, empty_portfolio, buy_signal):
        risk_manager.record_trade_pnl(Decimal("-35000"))
        result = risk_manager.check_buy(buy_signal, empty_portfolio, Decimal("100000"))
        assert result.allowed is False
        assert "Daily loss" in result.reason

    def test_rejects_when_max_drawdown(self, risk_manager, buy_signal):
        portfolio = Portfolio(
            krw_balance=Decimal("800000"),
            total_trades=10,
            total_profit=Decimal("-160000"),
        )
        result = risk_manager.check_buy(buy_signal, portfolio, Decimal("100000"))
        assert result.allowed is False
        assert "drawdown" in result.reason


class TestRiskManagerSell:
    def test_allows_valid_sell(self, risk_manager, portfolio_with_position, sell_signal):
        result = risk_manager.check_sell(sell_signal, portfolio_with_position)
        assert result.allowed is True

    def test_rejects_buy_signal_as_sell(self, risk_manager, portfolio_with_position, buy_signal):
        result = risk_manager.check_sell(buy_signal, portfolio_with_position)
        assert result.allowed is False
        assert "Not a SELL" in result.reason

    def test_rejects_no_position(self, risk_manager, empty_portfolio, sell_signal):
        result = risk_manager.check_sell(sell_signal, empty_portfolio)
        assert result.allowed is False
        assert "No position" in result.reason

    def test_rejects_closed_position(self, risk_manager, sell_signal):
        pos = Position(
            strategy_name="dip_buy",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            status=PositionStatus.CLOSED,
        )
        portfolio = Portfolio(
            krw_balance=Decimal("1000000"),
            positions={"KRW-BTC": pos},
        )
        result = risk_manager.check_sell(sell_signal, portfolio)
        assert result.allowed is False
        assert "not open" in result.reason


class TestStopLoss:
    def test_triggers_at_threshold(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
        )
        # -5% = 47,500,000
        result = risk_manager.check_stop_loss(pos, Decimal("47500000"))
        assert result.allowed is True
        assert "Stop-loss" in result.reason

    def test_no_trigger_above_threshold(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
        )
        result = risk_manager.check_stop_loss(pos, Decimal("48000000"))
        assert result.allowed is False

    def test_closed_position(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            status=PositionStatus.CLOSED,
        )
        result = risk_manager.check_stop_loss(pos, Decimal("40000000"))
        assert result.allowed is False


class TestTakeProfit:
    def test_triggers_at_threshold(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
        )
        # +10% = 55,000,000
        result = risk_manager.check_take_profit(pos, Decimal("55000000"))
        assert result.allowed is True

    def test_no_trigger_below_threshold(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
        )
        result = risk_manager.check_take_profit(pos, Decimal("54000000"))
        assert result.allowed is False


class TestTrailingStop:
    def test_triggers_when_drops_from_high(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            highest_price=Decimal("60000000"),
        )
        # 3% drop from 60M = 58.2M
        result = risk_manager.check_trailing_stop(pos, Decimal("58000000"))
        assert result.allowed is True
        assert "Trailing stop" in result.reason

    def test_no_trigger_at_new_high(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            highest_price=Decimal("55000000"),
        )
        result = risk_manager.check_trailing_stop(pos, Decimal("56000000"))
        assert result.allowed is False
        assert "New high" in result.reason

    def test_no_trigger_small_drop(self, risk_manager):
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            highest_price=Decimal("55000000"),
        )
        # 1% drop from 55M = 54.45M
        result = risk_manager.check_trailing_stop(pos, Decimal("54500000"))
        assert result.allowed is False


class TestDailyPnL:
    def test_record_and_track(self, risk_manager):
        risk_manager.record_trade_pnl(Decimal("5000"))
        assert risk_manager.daily_pnl.realized_pnl == Decimal("5000")
        assert risk_manager.daily_pnl.trades_today == 1

        risk_manager.record_trade_pnl(Decimal("-2000"))
        assert risk_manager.daily_pnl.realized_pnl == Decimal("3000")
        assert risk_manager.daily_pnl.trades_today == 2
