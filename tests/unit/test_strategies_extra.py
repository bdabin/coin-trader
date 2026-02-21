"""Tests for additional strategies."""

from __future__ import annotations

import pytest

from coin_trader.domain.models import SignalType
from coin_trader.strategies.fear_greed import FearGreedStrategy
from coin_trader.strategies.notice_alpha import NoticeAlphaStrategy
from coin_trader.strategies.volatility_breakout import VolatilityBreakoutStrategy
from coin_trader.strategies.volume_surge import VolumeSurgeStrategy


class TestFearGreed:
    @pytest.mark.asyncio
    async def test_buy_on_extreme_fear(self):
        s = FearGreedStrategy(buy_threshold=25, sell_threshold=75)
        signal = await s.evaluate("KRW-BTC", {
            "fear_greed_value": 15,
            "has_position": False,
        })
        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert "Fear" in signal.reason

    @pytest.mark.asyncio
    async def test_sell_on_extreme_greed(self):
        s = FearGreedStrategy(buy_threshold=25, sell_threshold=75)
        signal = await s.evaluate("KRW-BTC", {
            "fear_greed_value": 85,
            "has_position": True,
        })
        assert signal is not None
        assert signal.signal_type == SignalType.SELL

    @pytest.mark.asyncio
    async def test_neutral_no_signal(self):
        s = FearGreedStrategy()
        signal = await s.evaluate("KRW-BTC", {
            "fear_greed_value": 50,
            "has_position": False,
        })
        assert signal is None

    @pytest.mark.asyncio
    async def test_no_fg_data(self):
        s = FearGreedStrategy()
        signal = await s.evaluate("KRW-BTC", {})
        assert signal is None

    def test_name(self):
        s = FearGreedStrategy(buy_threshold=20, sell_threshold=80)
        assert s.name == "fear_greed_20_80"


class TestVolatilityBreakout:
    @pytest.mark.asyncio
    async def test_breakout_buy(self):
        s = VolatilityBreakoutStrategy(k_factor=0.5)
        signal = await s.evaluate("KRW-BTC", {
            "current_price": 52000000,
            "open_price": 50000000,
            "prev_high": 51000000,
            "prev_low": 49000000,
            "has_position": False,
        })
        # target = 50M + 0.5 * (51M - 49M) = 50M + 1M = 51M
        # 52M > 51M → BUY
        assert signal is not None
        assert signal.signal_type == SignalType.BUY

    @pytest.mark.asyncio
    async def test_no_breakout(self):
        s = VolatilityBreakoutStrategy(k_factor=0.5)
        signal = await s.evaluate("KRW-BTC", {
            "current_price": 50500000,
            "open_price": 50000000,
            "prev_high": 51000000,
            "prev_low": 49000000,
            "has_position": False,
        })
        # target = 51M, 50.5M < 51M → no signal
        assert signal is None

    @pytest.mark.asyncio
    async def test_no_data(self):
        s = VolatilityBreakoutStrategy()
        signal = await s.evaluate("KRW-BTC", {})
        assert signal is None


class TestVolumeSurge:
    @pytest.mark.asyncio
    async def test_volume_spike_buy(self):
        s = VolumeSurgeStrategy(lookback_hours=5, volume_multiplier=3.0)
        signal = await s.evaluate("KRW-BTC", {
            "volume_history": [100.0] * 5,
            "volume": 400.0,  # 4x avg
            "change_pct": 2.0,
            "has_position": False,
        })
        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert "surge" in signal.reason.lower()

    @pytest.mark.asyncio
    async def test_no_spike(self):
        s = VolumeSurgeStrategy(lookback_hours=5, volume_multiplier=3.0)
        signal = await s.evaluate("KRW-BTC", {
            "volume_history": [100.0] * 5,
            "volume": 200.0,  # only 2x
            "change_pct": 2.0,
            "has_position": False,
        })
        assert signal is None

    @pytest.mark.asyncio
    async def test_spike_but_negative_price(self):
        s = VolumeSurgeStrategy(lookback_hours=5, volume_multiplier=3.0)
        signal = await s.evaluate("KRW-BTC", {
            "volume_history": [100.0] * 5,
            "volume": 400.0,
            "change_pct": -2.0,  # negative price
            "has_position": False,
        })
        assert signal is None


class TestNoticeAlpha:
    @pytest.mark.asyncio
    async def test_buy_on_listing_notice(self):
        s = NoticeAlphaStrategy()
        signal = await s.evaluate("KRW-NEWCOIN", {
            "notices": [{
                "id": 1,
                "title": "신규 디지털 자산 거래지원 안내 (NEWCOIN)",
                "matched_keywords": ["신규"],
                "tickers": ["KRW-NEWCOIN"],
            }],
            "has_position": False,
        })
        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.9  # Listing boost

    @pytest.mark.asyncio
    async def test_no_notice(self):
        s = NoticeAlphaStrategy()
        signal = await s.evaluate("KRW-BTC", {
            "notices": [],
            "has_position": False,
        })
        assert signal is None

    @pytest.mark.asyncio
    async def test_already_has_position(self):
        s = NoticeAlphaStrategy()
        signal = await s.evaluate("KRW-NEWCOIN", {
            "notices": [{"tickers": ["KRW-NEWCOIN"], "matched_keywords": ["신규"]}],
            "has_position": True,
        })
        assert signal is None

    @pytest.mark.asyncio
    async def test_ticker_not_in_notice(self):
        s = NoticeAlphaStrategy()
        signal = await s.evaluate("KRW-BTC", {
            "notices": [{"tickers": ["KRW-ETH"], "matched_keywords": ["상장"]}],
            "has_position": False,
        })
        assert signal is None
