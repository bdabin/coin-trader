"""Configuration loader: TOML defaults + .env overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import tomli
from pydantic import Field
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_TOML = _PROJECT_ROOT / "config" / "default.toml"


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomli.load(f)


class RiskConfig(BaseSettings):
    stop_loss_pct: float = -5.0
    take_profit_pct: float = 10.0
    trailing_stop_pct: float = 3.0
    max_daily_loss_pct: float = -3.0
    max_drawdown_pct: float = -15.0
    max_positions: int = 5
    fee_rate: float = 0.05


class StrategyParams(BaseSettings):
    enabled: bool = False
    params: dict[str, Any] = Field(default_factory=dict)


class TradingConfig(BaseSettings):
    initial_krw: int = 1_000_000
    buy_amount: int = 100_000
    target_coins: list[str] = Field(
        default_factory=lambda: [
            "KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE",
            "KRW-ADA", "KRW-AVAX", "KRW-LINK", "KRW-DOT", "KRW-MATIC",
        ]
    )


class DatabaseConfig(BaseSettings):
    postgres_dsn: str = "postgresql://trader:trader_local@localhost:5432/coin_trader"


class RedisConfig(BaseSettings):
    url: str = "redis://localhost:6379"


class GraphConfig(BaseSettings):
    falkordb_host: str = "localhost"
    falkordb_port: int = 6380


class WebSocketConfig(BaseSettings):
    reconnect_interval: int = 5


class AIConfig(BaseSettings):
    opus_model: str = "claude-opus-4-6"
    codex_model: str = "codex-5.3"


class AppConfig(BaseSettings):
    mode: str = "paper"
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategies: dict[str, StrategyParams] = Field(default_factory=dict)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    ai: AIConfig = Field(default_factory=AIConfig)

    # API keys from .env
    upbit_access_key: str = ""
    upbit_secret_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    lunarcrush_api_key: str = ""


def load_config(toml_path: Path | None = None) -> AppConfig:
    """Load config from TOML file with .env overrides."""
    toml_path = toml_path or _DEFAULT_TOML
    raw = _load_toml(toml_path)

    app_section = raw.get("app", {})
    trading_raw = raw.get("trading", {})
    risk_raw = raw.get("risk", {})
    strategies_raw = raw.get("strategies", {})
    db_raw = raw.get("database", {})
    redis_raw = raw.get("redis", {})
    graph_raw = raw.get("graph", {})
    ws_raw = raw.get("websocket", {})
    ai_raw = raw.get("ai", {})

    strategy_configs: dict[str, StrategyParams] = {}
    for name, cfg in strategies_raw.items():
        strategy_configs[name] = StrategyParams(**cfg)

    return AppConfig(
        mode=app_section.get("mode", "paper"),
        trading=TradingConfig(**trading_raw),
        risk=RiskConfig(**risk_raw),
        strategies=strategy_configs,
        database=DatabaseConfig(**db_raw),
        redis=RedisConfig(**redis_raw),
        graph=GraphConfig(**graph_raw),
        websocket=WebSocketConfig(**ws_raw),
        ai=AIConfig(**ai_raw),
        upbit_access_key=os.getenv("UPBIT_ACCESS_KEY", ""),
        upbit_secret_key=os.getenv("UPBIT_SECRET_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        lunarcrush_api_key=os.getenv("LUNARCRUSH_API_KEY", ""),
    )
