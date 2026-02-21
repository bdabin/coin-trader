"""Migrate v1 trading-bot data to coin-trader PostgreSQL.

Reads JSON state from the old trading-bot and imports into the new schema.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

V1_DATA_PATH = Path("/Users/baedabin/clawd/trading-bot/data/multi_strategies.json")


async def migrate(dsn: str) -> None:
    import asyncpg

    if not V1_DATA_PATH.exists():
        print(f"V1 data not found at {V1_DATA_PATH}")
        return

    with open(V1_DATA_PATH) as f:
        v1_data = json.load(f)

    strategies = v1_data.get("strategies", {})
    print(f"Found {len(strategies)} v1 strategies")

    conn = await asyncpg.connect(dsn)

    try:
        for sid, s in strategies.items():
            strategy_id = uuid4()
            template = s.get("template", "unknown")
            params = s.get("params", {})

            # Calculate performance
            trades = s.get("trades", [])
            sells = [t for t in trades if t.get("side") == "SELL"]
            wins = [t for t in sells if t.get("profit", 0) > 0]
            win_rate = len(wins) / len(sells) if sells else 0.0

            portfolio = s.get("portfolio", {})
            krw = portfolio.get("krw", 1_000_000)
            positions = portfolio.get("positions", {})
            total_value = krw + sum(
                p.get("quantity", 0) * p.get("avg_price", 0)
                for p in positions.values()
            )
            return_pct = (total_value / 1_000_000 - 1) * 100

            # Insert strategy
            await conn.execute(
                """INSERT INTO strategies (id, name, template, params, status,
                   win_rate, return_pct, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                   ON CONFLICT (name) DO NOTHING""",
                strategy_id,
                sid,
                template,
                json.dumps(params),
                "ACTIVE" if return_pct > 0 else "DEPRECATED",
                win_rate,
                return_pct,
                datetime.utcnow(),
                datetime.utcnow(),
            )

            # Insert trades
            for trade in trades:
                await conn.execute(
                    """INSERT INTO trades (id, strategy_name, ticker, side, price,
                       quantity, total_krw, fee, reason, profit, profit_pct, timestamp)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
                    uuid4(),
                    sid,
                    trade.get("ticker", ""),
                    trade.get("side", "BUY"),
                    Decimal(str(trade.get("price", 0))),
                    Decimal(str(trade.get("quantity", 0))),
                    Decimal(str(trade.get("total_krw", 0))),
                    Decimal(str(trade.get("total_krw", 0) * 0.0005)),
                    trade.get("reason", ""),
                    Decimal(str(trade.get("profit", 0))) if trade.get("profit") else None,
                    trade.get("profit_pct"),
                    datetime.fromisoformat(trade["timestamp"]) if trade.get("timestamp") else datetime.utcnow(),
                )

            print(f"  Migrated: {sid} (return={return_pct:.2f}%, trades={len(trades)})")

    finally:
        await conn.close()

    print("Migration complete!")


if __name__ == "__main__":
    dsn = sys.argv[1] if len(sys.argv) > 1 else "postgresql://trader:trader_local@localhost:5432/coin_trader"
    asyncio.run(migrate(dsn))
