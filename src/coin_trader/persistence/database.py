"""PostgreSQL async connection management with asyncpg."""

from __future__ import annotations

from typing import Any, List, Optional

import asyncpg
import structlog

logger = structlog.get_logger()

# SQL schema for initial migration
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    total_krw NUMERIC(20, 2) NOT NULL,
    fee NUMERIC(20, 8) NOT NULL,
    reason TEXT DEFAULT '',
    profit NUMERIC(20, 2),
    profit_pct DOUBLE PRECISION,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN',
    entry_price NUMERIC(20, 8) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exit_price NUMERIC(20, 8),
    exit_time TIMESTAMPTZ,
    highest_price NUMERIC(20, 8),
    profit NUMERIC(20, 2),
    profit_pct DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    template VARCHAR(100) NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    sharpe_ratio DOUBLE PRECISION,
    win_rate DOUBLE PRECISION,
    return_pct DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY,
    model VARCHAR(50) NOT NULL,
    signal_id VARCHAR(100),
    ticker VARCHAR(20) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    reasoning TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    market_context JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    open_price NUMERIC(20, 8),
    high_price NUMERIC(20, 8),
    low_price NUMERIC(20, 8),
    volume NUMERIC(30, 8),
    change_pct DOUBLE PRECISION,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_ticker_ts ON market_snapshots(ticker, timestamp);
"""


class Database:
    """Async PostgreSQL connection pool."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        logger.info("database.connected", dsn=self.dsn.split("@")[-1])

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            logger.info("database.closed")

    async def init_schema(self) -> None:
        """Create tables if they don't exist."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
        logger.info("database.schema_initialized")

    async def execute(self, query: str, *args: Any) -> str:
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> List[asyncpg.Record]:
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        if not self.pool:
            raise RuntimeError("Database not connected")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
