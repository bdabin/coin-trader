"""Repository pattern for database operations."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from coin_trader.domain.models import (
    AIDecision,
    MarketSnapshot,
    Position,
    PositionStatus,
    Side,
    StrategyConfig,
    StrategyStatus,
    Trade,
)
from coin_trader.persistence.database import Database


class TradeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, trade: Trade) -> None:
        await self.db.execute(
            """INSERT INTO trades (id, strategy_name, ticker, side, price, quantity,
               total_krw, fee, reason, profit, profit_pct, timestamp)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
            trade.id,
            trade.strategy_name,
            trade.ticker,
            trade.side.value,
            trade.price,
            trade.quantity,
            trade.total_krw,
            trade.fee,
            trade.reason,
            trade.profit,
            trade.profit_pct,
            trade.timestamp,
        )

    async def get_by_strategy(self, strategy_name: str, limit: int = 100) -> List[Trade]:
        rows = await self.db.fetch(
            """SELECT * FROM trades WHERE strategy_name = $1
               ORDER BY timestamp DESC LIMIT $2""",
            strategy_name,
            limit,
        )
        return [self._to_model(r) for r in rows]

    async def get_by_ticker(self, ticker: str, limit: int = 100) -> List[Trade]:
        rows = await self.db.fetch(
            "SELECT * FROM trades WHERE ticker = $1 ORDER BY timestamp DESC LIMIT $2",
            ticker,
            limit,
        )
        return [self._to_model(r) for r in rows]

    async def get_recent(self, limit: int = 50) -> List[Trade]:
        rows = await self.db.fetch(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT $1", limit
        )
        return [self._to_model(r) for r in rows]

    @staticmethod
    def _to_model(row: Any) -> Trade:
        return Trade(
            id=row["id"],
            strategy_name=row["strategy_name"],
            ticker=row["ticker"],
            side=Side(row["side"]),
            price=Decimal(str(row["price"])),
            quantity=Decimal(str(row["quantity"])),
            total_krw=Decimal(str(row["total_krw"])),
            fee=Decimal(str(row["fee"])),
            reason=row["reason"] or "",
            profit=Decimal(str(row["profit"])) if row["profit"] is not None else None,
            profit_pct=row["profit_pct"],
            timestamp=row["timestamp"],
        )


class PositionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, position: Position) -> None:
        await self.db.execute(
            """INSERT INTO positions (id, strategy_name, ticker, status, entry_price,
               quantity, entry_time, exit_price, exit_time, highest_price, profit, profit_pct)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
               ON CONFLICT (id) DO UPDATE SET
               status = $4, exit_price = $8, exit_time = $9, highest_price = $10,
               profit = $11, profit_pct = $12""",
            position.id,
            position.strategy_name,
            position.ticker,
            position.status.value,
            position.entry_price,
            position.quantity,
            position.entry_time,
            position.exit_price,
            position.exit_time,
            position.highest_price,
            position.profit,
            position.profit_pct,
        )

    async def get_open(self, strategy_name: Optional[str] = None) -> List[Position]:
        if strategy_name:
            rows = await self.db.fetch(
                "SELECT * FROM positions WHERE status = 'OPEN' AND strategy_name = $1",
                strategy_name,
            )
        else:
            rows = await self.db.fetch("SELECT * FROM positions WHERE status = 'OPEN'")
        return [self._to_model(r) for r in rows]

    async def get_by_ticker(self, ticker: str, status: str = "OPEN") -> Optional[Position]:
        row = await self.db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = $2 LIMIT 1",
            ticker,
            status,
        )
        return self._to_model(row) if row else None

    @staticmethod
    def _to_model(row: Any) -> Position:
        return Position(
            id=row["id"],
            strategy_name=row["strategy_name"],
            ticker=row["ticker"],
            status=PositionStatus(row["status"]),
            entry_price=Decimal(str(row["entry_price"])),
            quantity=Decimal(str(row["quantity"])),
            entry_time=row["entry_time"],
            exit_price=(
                Decimal(str(row["exit_price"])) if row["exit_price"] is not None else None
            ),
            exit_time=row["exit_time"],
            highest_price=(
                Decimal(str(row["highest_price"])) if row["highest_price"] is not None else None
            ),
            profit=Decimal(str(row["profit"])) if row["profit"] is not None else None,
            profit_pct=row["profit_pct"],
        )


class StrategyRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, strategy: StrategyConfig) -> None:
        await self.db.execute(
            """INSERT INTO strategies (id, name, template, params, status,
               sharpe_ratio, win_rate, return_pct, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               ON CONFLICT (id) DO UPDATE SET
               params = $4, status = $5, sharpe_ratio = $6, win_rate = $7,
               return_pct = $8, updated_at = $10""",
            strategy.id,
            strategy.name,
            strategy.template,
            json.dumps({k: v for k, v in strategy.params.items()}),
            strategy.status.value,
            strategy.sharpe_ratio,
            strategy.win_rate,
            strategy.return_pct,
            strategy.created_at,
            strategy.updated_at,
        )

    async def get_active(self) -> List[StrategyConfig]:
        rows = await self.db.fetch(
            "SELECT * FROM strategies WHERE status = 'ACTIVE' ORDER BY return_pct DESC NULLS LAST"
        )
        return [self._to_model(r) for r in rows]

    async def get_by_name(self, name: str) -> Optional[StrategyConfig]:
        row = await self.db.fetchrow("SELECT * FROM strategies WHERE name = $1", name)
        return self._to_model(row) if row else None

    @staticmethod
    def _to_model(row: Any) -> StrategyConfig:
        params_raw = row["params"]
        if isinstance(params_raw, str):
            params_raw = json.loads(params_raw)
        return StrategyConfig(
            id=row["id"],
            name=row["name"],
            template=row["template"],
            params=params_raw,
            status=StrategyStatus(row["status"]),
            sharpe_ratio=row["sharpe_ratio"],
            win_rate=row["win_rate"],
            return_pct=row["return_pct"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class MarketSnapshotRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, snapshot: MarketSnapshot) -> None:
        await self.db.execute(
            """INSERT INTO market_snapshots (ticker, price, open_price, high_price,
               low_price, volume, change_pct, timestamp)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            snapshot.ticker,
            snapshot.price,
            snapshot.open_price,
            snapshot.high_price,
            snapshot.low_price,
            snapshot.volume,
            snapshot.change_pct,
            snapshot.timestamp,
        )

    async def get_latest(self, ticker: str) -> Optional[MarketSnapshot]:
        row = await self.db.fetchrow(
            "SELECT * FROM market_snapshots WHERE ticker = $1 ORDER BY timestamp DESC LIMIT 1",
            ticker,
        )
        if not row:
            return None
        return MarketSnapshot(
            ticker=row["ticker"],
            price=Decimal(str(row["price"])),
            open_price=(
                Decimal(str(row["open_price"])) if row["open_price"] is not None else None
            ),
            high_price=(
                Decimal(str(row["high_price"])) if row["high_price"] is not None else None
            ),
            low_price=Decimal(str(row["low_price"])) if row["low_price"] is not None else None,
            volume=Decimal(str(row["volume"])) if row["volume"] is not None else None,
            change_pct=row["change_pct"],
            timestamp=row["timestamp"],
        )

    async def get_history(
        self, ticker: str, since: datetime, limit: int = 1000
    ) -> List[MarketSnapshot]:
        rows = await self.db.fetch(
            """SELECT * FROM market_snapshots
               WHERE ticker = $1 AND timestamp >= $2
               ORDER BY timestamp ASC LIMIT $3""",
            ticker,
            since,
            limit,
        )
        return [
            MarketSnapshot(
                ticker=r["ticker"],
                price=Decimal(str(r["price"])),
                change_pct=r["change_pct"],
                timestamp=r["timestamp"],
            )
            for r in rows
        ]


class AIDecisionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, decision: AIDecision) -> None:
        await self.db.execute(
            """INSERT INTO ai_decisions (id, model, signal_id, ticker, decision,
               reasoning, confidence, market_context, timestamp)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            decision.id,
            decision.model,
            decision.signal_id,
            decision.ticker,
            decision.decision,
            decision.reasoning,
            decision.confidence,
            json.dumps(decision.market_context),
            decision.timestamp,
        )

    async def get_recent(self, limit: int = 20) -> List[AIDecision]:
        rows = await self.db.fetch(
            "SELECT * FROM ai_decisions ORDER BY timestamp DESC LIMIT $1", limit
        )
        results = []
        for r in rows:
            ctx = r["market_context"]
            if isinstance(ctx, str):
                ctx = json.loads(ctx)
            results.append(
                AIDecision(
                    id=r["id"],
                    model=r["model"],
                    signal_id=r["signal_id"],
                    ticker=r["ticker"],
                    decision=r["decision"],
                    reasoning=r["reasoning"],
                    confidence=r["confidence"],
                    market_context=ctx or {},
                    timestamp=r["timestamp"],
                )
            )
        return results
