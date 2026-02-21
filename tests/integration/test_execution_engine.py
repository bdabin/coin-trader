"""Tests for the execution engine with paper trading."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytest

from coin_trader.config import AppConfig, RiskConfig, TradingConfig, load_config
from coin_trader.domain.models import Portfolio, Signal, SignalType
from coin_trader.domain.portfolio import PortfolioManager
from coin_trader.domain.risk import RiskManager
from coin_trader.domain.strategy import Strategy
from coin_trader.execution.engine import ExecutionEngine
from coin_trader.execution.paper import PaperTrader


class MockStrategy(Strategy):
    """Mock strategy that returns predefined signals."""

    def __init__(self, signals: Optional[Dict[str, Signal]] = None) -> None:
        self._signals = signals or {}

    @property
    def name(self) -> str:
        return "mock_strategy"

    @property
    def template(self) -> str:
        return "mock"

    async def evaluate(
        self, ticker: str, market_data: Dict[str, Any]
    ) -> Optional[Signal]:
        return self._signals.get(ticker)


@pytest.fixture
def config():
    return load_config()


class TestExecutionEngine:
    @pytest.mark.asyncio
    async def test_buy_on_signal(self, config):
        buy_signal = Signal(
            strategy_name="mock_strategy",
            ticker="KRW-BTC",
            signal_type=SignalType.BUY,
            strength=0.8,
            reason="Test buy",
        )
        strategy = MockStrategy(signals={"KRW-BTC": buy_signal})

        portfolio = Portfolio(krw_balance=Decimal("1000000"))
        pm = PortfolioManager(portfolio, config.risk.fee_rate)
        rm = RiskManager(config.risk)

        engine = ExecutionEngine(
            config=config,
            portfolio_manager=pm,
            risk_manager=rm,
            strategies=[strategy],
        )

        tick = {"ticker": "KRW-BTC", "price": 50000000}
        trades = await engine.process_tick(tick)
        assert len(trades) == 1
        assert trades[0].ticker == "KRW-BTC"
        assert portfolio.krw_balance < Decimal("1000000")

    @pytest.mark.asyncio
    async def test_stop_loss_trigger(self, config):
        strategy = MockStrategy()
        portfolio = Portfolio(krw_balance=Decimal("900000"))

        from coin_trader.domain.models import Position
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            highest_price=Decimal("50000000"),
        )
        portfolio.positions["KRW-BTC"] = pos

        pm = PortfolioManager(portfolio, config.risk.fee_rate)
        rm = RiskManager(config.risk)

        engine = ExecutionEngine(
            config=config,
            portfolio_manager=pm,
            risk_manager=rm,
            strategies=[strategy],
        )

        # Price drops 6% → stop-loss at -5%
        tick = {"ticker": "KRW-BTC", "price": 47000000}
        trades = await engine.process_tick(tick)
        assert len(trades) == 1
        assert "Stop-loss" in trades[0].reason

    @pytest.mark.asyncio
    async def test_take_profit_trigger(self, config):
        strategy = MockStrategy()
        portfolio = Portfolio(krw_balance=Decimal("900000"))

        from coin_trader.domain.models import Position
        pos = Position(
            strategy_name="test",
            ticker="KRW-BTC",
            entry_price=Decimal("50000000"),
            quantity=Decimal("0.002"),
            highest_price=Decimal("50000000"),
        )
        portfolio.positions["KRW-BTC"] = pos

        pm = PortfolioManager(portfolio, config.risk.fee_rate)
        rm = RiskManager(config.risk)

        engine = ExecutionEngine(
            config=config,
            portfolio_manager=pm,
            risk_manager=rm,
            strategies=[strategy],
        )

        # Price up 11% → take-profit at +10%
        tick = {"ticker": "KRW-BTC", "price": 55500000}
        trades = await engine.process_tick(tick)
        assert len(trades) == 1
        assert "Take-profit" in trades[0].reason

    @pytest.mark.asyncio
    async def test_no_action_on_empty_tick(self, config):
        strategy = MockStrategy()
        portfolio = Portfolio(krw_balance=Decimal("1000000"))
        pm = PortfolioManager(portfolio, config.risk.fee_rate)
        rm = RiskManager(config.risk)

        engine = ExecutionEngine(
            config=config,
            portfolio_manager=pm,
            risk_manager=rm,
            strategies=[strategy],
        )

        trades = await engine.process_tick({})
        assert len(trades) == 0

    @pytest.mark.asyncio
    async def test_summary(self, config):
        strategy = MockStrategy()
        portfolio = Portfolio(krw_balance=Decimal("1000000"))
        pm = PortfolioManager(portfolio, config.risk.fee_rate)
        rm = RiskManager(config.risk)

        engine = ExecutionEngine(
            config=config,
            portfolio_manager=pm,
            risk_manager=rm,
            strategies=[strategy],
        )

        summary = engine.get_summary()
        assert summary["total_trades"] == 0
        assert summary["win_rate"] == 0.0


class TestPaperTrader:
    @pytest.mark.asyncio
    async def test_paper_trader_init(self, config):
        strategies = [MockStrategy()]
        trader = PaperTrader(config, strategies)
        portfolio = trader.get_portfolio()
        assert portfolio.krw_balance == Decimal(str(config.trading.initial_krw))

    @pytest.mark.asyncio
    async def test_paper_trader_summary(self, config):
        strategies = [MockStrategy()]
        trader = PaperTrader(config, strategies)
        summary = trader.get_summary()
        assert "krw_balance" in summary
