"""Shared test fixtures."""

from __future__ import annotations

from decimal import Decimal

import pytest

from coin_trader.config import RiskConfig, load_config
from coin_trader.domain.models import Portfolio, Position, Signal, SignalType
from coin_trader.domain.risk import RiskManager


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def risk_config():
    return RiskConfig(
        stop_loss_pct=-5.0,
        take_profit_pct=10.0,
        trailing_stop_pct=3.0,
        max_daily_loss_pct=-3.0,
        max_drawdown_pct=-15.0,
        max_positions=5,
        fee_rate=0.05,
    )


@pytest.fixture
def risk_manager(risk_config):
    return RiskManager(risk_config)


@pytest.fixture
def empty_portfolio():
    return Portfolio(krw_balance=Decimal("1000000"))


@pytest.fixture
def portfolio_with_position():
    pos = Position(
        strategy_name="dip_buy",
        ticker="KRW-BTC",
        entry_price=Decimal("50000000"),
        quantity=Decimal("0.002"),
    )
    return Portfolio(
        krw_balance=Decimal("900000"),
        positions={"KRW-BTC": pos},
    )


@pytest.fixture
def buy_signal():
    return Signal(
        strategy_name="dip_buy",
        ticker="KRW-BTC",
        signal_type=SignalType.BUY,
        strength=0.8,
        reason="Dip -7.2% <= -7%",
    )


@pytest.fixture
def sell_signal():
    return Signal(
        strategy_name="dip_buy",
        ticker="KRW-BTC",
        signal_type=SignalType.SELL,
        strength=0.9,
        reason="Recovery +2.5% >= +2%",
    )
