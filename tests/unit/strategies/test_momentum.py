"""Tests for Momentum strategy."""

from __future__ import annotations

import pytest

from coin_trader.domain.models import SignalType
from coin_trader.strategies.momentum import MomentumStrategy


@pytest.fixture
def strategy():
    return MomentumStrategy(lookback_hours=12, entry_threshold=5.0, exit_threshold=-3.0)


class TestMomentumBuy:
    @pytest.mark.asyncio
    async def test_buy_on_strong_momentum(self, strategy):
        prices = [100.0] * 10 + [105.5]  # +5.5% gain
        market_data = {
            "price_history": prices,
            "current_price": 105.5,
            "has_position": False,
            "entry_price": 0,
        }
        signal = await strategy.evaluate("KRW-BTC", market_data)
        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert "Momentum" in signal.reason

    @pytest.mark.asyncio
    async def test_no_buy_below_threshold(self, strategy):
        prices = [100.0] * 10 + [103.0]  # +3% only
        market_data = {
            "price_history": prices,
            "current_price": 103.0,
            "has_position": False,
            "entry_price": 0,
        }
        signal = await strategy.evaluate("KRW-BTC", market_data)
        assert signal is None


class TestMomentumSell:
    @pytest.mark.asyncio
    async def test_sell_on_reversal(self, strategy):
        prices = [105.0] * 10 + [101.0]
        market_data = {
            "price_history": prices,
            "current_price": 101.0,
            "has_position": True,
            "entry_price": 105.0,  # -3.8% from entry
        }
        signal = await strategy.evaluate("KRW-BTC", market_data)
        assert signal is not None
        assert signal.signal_type == SignalType.SELL

    @pytest.mark.asyncio
    async def test_no_sell_small_loss(self, strategy):
        prices = [105.0] * 10 + [103.0]
        market_data = {
            "price_history": prices,
            "current_price": 103.0,
            "has_position": True,
            "entry_price": 105.0,  # -1.9% only
        }
        signal = await strategy.evaluate("KRW-BTC", market_data)
        assert signal is None

    @pytest.mark.asyncio
    async def test_no_signal_empty_data(self, strategy):
        signal = await strategy.evaluate("KRW-BTC", {})
        assert signal is None
