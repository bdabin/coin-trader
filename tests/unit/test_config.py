"""Tests for configuration loading."""

from __future__ import annotations

from coin_trader.config import load_config


class TestConfig:
    def test_load_default(self):
        config = load_config()
        assert config.mode == "paper"
        assert config.trading.initial_krw == 1_000_000
        assert config.trading.buy_amount == 100_000
        assert len(config.trading.target_coins) == 10

    def test_risk_config(self):
        config = load_config()
        assert config.risk.stop_loss_pct == -5.0
        assert config.risk.take_profit_pct == 10.0
        assert config.risk.trailing_stop_pct == 3.0
        assert config.risk.max_daily_loss_pct == -3.0
        assert config.risk.max_positions == 5
        assert config.risk.fee_rate == 0.05

    def test_strategies_loaded(self):
        config = load_config()
        assert "dip_buy" in config.strategies
        assert config.strategies["dip_buy"].enabled is True
        assert config.strategies["dip_buy"].params["drop_pct"] == -7

        # Disabled strategies
        assert config.strategies["rsi"].enabled is False
        assert config.strategies["ma_cross"].enabled is False
        assert config.strategies["bollinger"].enabled is False

    def test_database_config(self):
        config = load_config()
        assert "coin_trader" in config.database.postgres_dsn

    def test_redis_config(self):
        config = load_config()
        assert config.redis.url == "redis://localhost:6379"

    def test_graph_config(self):
        config = load_config()
        assert config.graph.falkordb_host == "localhost"
        assert config.graph.falkordb_port == 6380

    def test_ai_config(self):
        config = load_config()
        assert config.ai.opus_model == "claude-opus-4-6"
        assert config.ai.codex_model == "codex-5.3"
