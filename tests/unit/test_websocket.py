"""Tests for WebSocket message parsing."""

from __future__ import annotations

import json

from coin_trader.stream.websocket import UpbitWebSocket


class TestParseMessage:
    def test_parse_valid_message(self):
        data = {
            "cd": "KRW-BTC",
            "tp": 50000000,
            "tv": 0.5,
            "scr": -0.02,
            "hp": 51000000,
            "lp": 49000000,
            "tms": 1708488000000,
        }
        result = UpbitWebSocket._parse_message(json.dumps(data))
        assert result is not None
        assert result["ticker"] == "KRW-BTC"
        assert result["price"] == 50000000
        assert result["volume"] == 0.5
        assert result["change_pct"] == -2.0
        assert result["high_price"] == 51000000

    def test_parse_bytes(self):
        data = {"cd": "KRW-ETH", "tp": 4000000, "tv": 1.0, "scr": 0.01, "hp": 0, "lp": 0, "tms": 0}
        result = UpbitWebSocket._parse_message(json.dumps(data).encode("utf-8"))
        assert result is not None
        assert result["ticker"] == "KRW-ETH"

    def test_parse_invalid_json(self):
        result = UpbitWebSocket._parse_message("not json")
        assert result is None

    def test_build_payload(self):
        ws = UpbitWebSocket(tickers=["KRW-BTC", "KRW-ETH"])
        payload = json.loads(ws._build_payload())
        assert len(payload) == 3
        assert payload[1]["type"] == "ticker"
        assert "KRW-BTC" in payload[1]["codes"]
