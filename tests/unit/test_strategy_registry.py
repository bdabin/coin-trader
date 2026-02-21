"""Tests for strategy registry."""

from __future__ import annotations

import pytest

from coin_trader.strategies.registry import (
    create_strategy,
    get_strategy_class,
    list_strategies,
)

# Import strategies to trigger registration
from coin_trader.strategies import (  # noqa: F401
    dip_buy,
    fear_greed,
    momentum,
    notice_alpha,
    volatility_breakout,
    volume_surge,
)


class TestRegistry:
    def test_list_strategies(self):
        strategies = list_strategies()
        assert "dip_buy" in strategies
        assert "momentum" in strategies
        assert "fear_greed" in strategies
        assert "volatility_breakout" in strategies
        assert "volume_surge" in strategies
        assert "notice_alpha" in strategies

    def test_get_strategy_class(self):
        cls = get_strategy_class("dip_buy")
        assert cls is not None
        assert cls.__name__ == "DipBuyStrategy"

    def test_get_nonexistent(self):
        cls = get_strategy_class("nonexistent")
        assert cls is None

    def test_create_strategy(self):
        s = create_strategy("dip_buy", drop_pct=-7.0, recovery_pct=2.0, timeframe_hours=24)
        assert s.name == "dip_buy_-7_2_24"
        assert s.template == "dip_buy"

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            create_strategy("nonexistent_strategy")
