"""Upbit WebSocket real-time ticker stream."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

import structlog
import websockets
from websockets.exceptions import ConnectionClosed

logger = structlog.get_logger()

UPBIT_WS_URL = "wss://api.upbit.com/websocket/v1"


class UpbitWebSocket:
    """Manages Upbit WebSocket connection for real-time ticker data."""

    def __init__(
        self,
        tickers: List[str],
        on_tick: Optional[Callable[[Dict[str, Any]], Any]] = None,
        reconnect_interval: int = 5,
    ) -> None:
        self.tickers = tickers
        self.on_tick = on_tick
        self.reconnect_interval = reconnect_interval
        self._running = False
        self._ws: Any = None

    def _build_payload(self) -> str:
        return json.dumps([
            {"ticket": "coin-trader"},
            {"type": "ticker", "codes": self.tickers, "isOnlyRealtime": True},
            {"format": "SIMPLE"},
        ])

    async def start(self) -> None:
        """Start WebSocket connection with auto-reconnect."""
        self._running = True
        while self._running:
            try:
                async with websockets.connect(UPBIT_WS_URL, ping_interval=30) as ws:
                    self._ws = ws
                    logger.info("websocket.connected", tickers=len(self.tickers))
                    await ws.send(self._build_payload())

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        data = self._parse_message(raw_msg)
                        if data and self.on_tick:
                            await self.on_tick(data)

            except ConnectionClosed as e:
                logger.warning("websocket.disconnected", code=e.code)
            except Exception as e:
                logger.error("websocket.error", error=str(e))

            if self._running:
                logger.info("websocket.reconnecting", wait=self.reconnect_interval)
                await asyncio.sleep(self.reconnect_interval)

    async def stop(self) -> None:
        """Stop WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            logger.info("websocket.stopped")

    @staticmethod
    def _parse_message(raw: Any) -> Optional[Dict[str, Any]]:
        """Parse WebSocket message into tick dict."""
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            return {
                "ticker": data.get("cd", ""),           # code
                "price": float(data.get("tp", 0)),      # trade_price
                "volume": float(data.get("tv", 0)),     # trade_volume
                "change_pct": float(data.get("scr", 0)) * 100,  # signed_change_rate
                "high_price": float(data.get("hp", 0)),  # high_price
                "low_price": float(data.get("lp", 0)),   # low_price
                "timestamp": data.get("tms", 0),          # timestamp
            }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("websocket.parse_error", error=str(e))
            return None
