"""E2E test: full trading cycle — signal → risk check → execution → reporting."""

from __future__ import annotations

from decimal import Decimal

import pytest

from coin_trader.config import load_config
from coin_trader.execution.paper import PaperTrader
from coin_trader.reporting.daily_report import DailyReport
from coin_trader.strategies.dip_buy import DipBuyStrategy


@pytest.mark.e2e
class TestFullTradingCycle:
    """Test complete trading cycle: detect dip → buy → recover → sell → report."""

    @pytest.mark.asyncio
    async def test_dip_buy_cycle(self):
        """Simulate a full dip buy → recovery cycle."""
        config = load_config()
        strategy = DipBuyStrategy(drop_pct=-7.0, recovery_pct=2.0, timeframe_hours=24)
        trader = PaperTrader(config, [strategy])

        # Phase 1: Market is stable — no trades
        stable_tick = {
            "ticker": "KRW-BTC",
            "price": 50000000,
            "price_history": [50000000.0] * 20 + [50000000.0],
        }
        trades = await trader.process_tick(stable_tick)
        assert len(trades) == 0

        # Phase 2: Market dips -8% — should BUY
        dip_tick = {
            "ticker": "KRW-BTC",
            "price": 46000000,
            "price_history": [50000000.0] * 20 + [46000000.0],
        }
        trades = await trader.process_tick(dip_tick)
        assert len(trades) == 1
        assert trades[0].side.value == "BUY"
        assert trades[0].ticker == "KRW-BTC"

        portfolio = trader.get_portfolio()
        assert "KRW-BTC" in portfolio.positions
        assert portfolio.krw_balance < Decimal(str(config.trading.initial_krw))

        # Phase 3: Price recovers +3% from entry — should SELL
        recovery_tick = {
            "ticker": "KRW-BTC",
            "price": 47380000,  # +3% from 46M
            "price_history": [46000000.0] * 20 + [47380000.0],
            "high_price": 47380000,
        }
        trades = await trader.process_tick(recovery_tick)
        assert len(trades) == 1
        assert trades[0].side.value == "SELL"
        assert trades[0].profit is not None
        assert trades[0].profit > 0

        # Verify portfolio state
        portfolio = trader.get_portfolio()
        assert portfolio.total_trades == 1
        assert portfolio.winning_trades == 1
        assert portfolio.win_rate == 1.0

        # Phase 4: Generate report
        report = DailyReport()
        data = report.generate(portfolio, [], {})
        assert data["total_trades"] == 1
        assert data["win_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_risk_blocks_over_position_limit(self):
        """Test that risk manager blocks buys when max positions reached."""
        config = load_config()
        strategy = DipBuyStrategy(drop_pct=-7.0, recovery_pct=2.0, timeframe_hours=24)
        trader = PaperTrader(config, [strategy])

        # Fill up to max positions (5)
        tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE"]
        for ticker in tickers:
            dip_tick = {
                "ticker": ticker,
                "price": 1000000,
                "price_history": [1100000.0] * 20 + [1000000.0],  # ~-9% dip
            }
            trades = await trader.process_tick(dip_tick)
            assert len(trades) == 1, f"Should buy {ticker}"

        # 6th position should be blocked
        dip_tick = {
            "ticker": "KRW-ADA",
            "price": 1000,
            "price_history": [1100.0] * 20 + [1000.0],
        }
        trades = await trader.process_tick(dip_tick)
        assert len(trades) == 0  # Blocked by max positions

    @pytest.mark.asyncio
    async def test_stop_loss_in_full_cycle(self):
        """Test stop-loss triggers during a full cycle."""
        config = load_config()
        strategy = DipBuyStrategy(drop_pct=-7.0, recovery_pct=2.0, timeframe_hours=24)
        trader = PaperTrader(config, [strategy])

        # Buy on dip
        dip_tick = {
            "ticker": "KRW-BTC",
            "price": 46000000,
            "price_history": [50000000.0] * 20 + [46000000.0],
        }
        trades = await trader.process_tick(dip_tick)
        assert len(trades) == 1

        # Price crashes further — 6% below entry → stop-loss at -5%
        crash_tick = {
            "ticker": "KRW-BTC",
            "price": 43000000,  # ~-6.5% from 46M entry
            "price_history": [46000000.0] * 20 + [43000000.0],
        }
        trades = await trader.process_tick(crash_tick)
        assert len(trades) == 1
        assert "Stop-loss" in trades[0].reason
        assert trades[0].profit is not None
        assert trades[0].profit < 0

    @pytest.mark.asyncio
    async def test_multiple_strategies_same_ticker(self):
        """Test that only one buy per ticker goes through."""
        config = load_config()
        s1 = DipBuyStrategy(drop_pct=-7.0, recovery_pct=2.0, timeframe_hours=24)
        s2 = DipBuyStrategy(drop_pct=-5.0, recovery_pct=3.0, timeframe_hours=12, name_suffix="alt")
        trader = PaperTrader(config, [s1, s2])

        dip_tick = {
            "ticker": "KRW-BTC",
            "price": 46000000,
            "price_history": [50000000.0] * 20 + [46000000.0],
        }
        trades = await trader.process_tick(dip_tick)
        # First strategy buys, second is blocked (duplicate position)
        assert len(trades) == 1
