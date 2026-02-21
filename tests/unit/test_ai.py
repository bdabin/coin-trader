"""Tests for AI components (mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coin_trader.ai.conversation import Conversation, Message
from coin_trader.ai.opus_analyst import OpusAnalyst
from coin_trader.ai.orchestrator import AIOrchestrator
from coin_trader.domain.models import Signal, SignalType


class TestConversation:
    def test_add_and_get_messages(self):
        conv = Conversation()
        conv.add_system("You are helpful")
        conv.add_user("Hello")
        conv.add_assistant("Hi there")

        messages = conv.to_api_format()
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_trim_history(self):
        conv = Conversation(max_history=3)
        conv.add_system("System")
        for i in range(5):
            conv.add_user(f"msg {i}")

        # Should keep system + last 3
        non_system = conv.get_non_system_messages()
        assert len(non_system) == 3

    def test_clear(self):
        conv = Conversation()
        conv.add_system("System")
        conv.add_user("Hello")
        conv.clear()
        assert len(conv.messages) == 1  # Only system remains
        assert conv.messages[0].role == "system"

    def test_get_system_message(self):
        conv = Conversation()
        conv.add_system("I am system")
        assert conv.get_system_message() == "I am system"

    def test_no_system_message(self):
        conv = Conversation()
        assert conv.get_system_message() == ""

    def test_system_replaced(self):
        conv = Conversation()
        conv.add_system("first")
        conv.add_system("second")
        assert conv.get_system_message() == "second"
        assert len([m for m in conv.messages if m.role == "system"]) == 1


class TestOpusAnalystParsing:
    def test_parse_execute_decision(self):
        response = """
Decision: EXECUTE
Confidence: 0.85
Reasoning: Strong dip buy signal with favorable conditions.
"""
        result = OpusAnalyst._parse_decision(response)
        assert result["decision"] == "EXECUTE"
        assert result["confidence"] == 0.85

    def test_parse_skip_decision(self):
        response = """I would SKIP this signal. Confidence: 0.3."""
        result = OpusAnalyst._parse_decision(response)
        assert result["decision"] == "SKIP"
        assert result["confidence"] == 0.3

    def test_parse_modify_decision(self):
        response = "I suggest we MODIFY the parameters. Confidence: 60%"
        result = OpusAnalyst._parse_decision(response)
        assert result["decision"] == "MODIFY"
        assert result["confidence"] == 0.6

    def test_parse_no_decision(self):
        response = "Market looks neutral overall."
        result = OpusAnalyst._parse_decision(response)
        assert result["decision"] == "SKIP"  # Default


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_no_ai_configured(self):
        orchestrator = AIOrchestrator()
        assert not orchestrator.enabled
        result = await orchestrator.discuss("hello")
        assert "not configured" in result

    @pytest.mark.asyncio
    async def test_no_codex_configured(self):
        orchestrator = AIOrchestrator()
        result = await orchestrator.generate_backtest("test", "dip_buy", {})
        assert "not configured" in result

    @pytest.mark.asyncio
    async def test_evaluate_without_opus(self):
        orchestrator = AIOrchestrator()
        signal = Signal(
            strategy_name="test",
            ticker="KRW-BTC",
            signal_type=SignalType.BUY,
            strength=0.5,
        )
        result = await orchestrator.evaluate_signal(signal, {})
        assert result is None
