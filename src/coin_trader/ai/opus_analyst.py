"""Opus 4.6 AI analyst — strategic decision maker."""

from __future__ import annotations

from typing import Any, Dict

import structlog

from coin_trader.ai.conversation import Conversation
from coin_trader.ai.prompts import OPUS_MARKET_ANALYSIS, OPUS_SIGNAL_EVAL, OPUS_SYSTEM
from coin_trader.domain.models import AIDecision, Signal

logger = structlog.get_logger()


class OpusAnalyst:
    """Claude Opus 4.6 for strategic trading decisions."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-6") -> None:
        self.api_key = api_key
        self.model = model
        self.conversation = Conversation()
        self.conversation.add_system(OPUS_SYSTEM)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    async def evaluate_signal(
        self,
        signal: Signal,
        market_context: Dict[str, Any],
    ) -> AIDecision:
        """Ask Opus to evaluate a trading signal."""
        prompt = OPUS_SIGNAL_EVAL.format(
            signal_type=signal.signal_type.value,
            ticker=signal.ticker,
            strategy_name=signal.strategy_name,
            strength=signal.strength,
            reason=signal.reason,
            fear_greed=market_context.get("fear_greed", "N/A"),
            change_pct=market_context.get("change_pct", 0),
            btc_dominance=market_context.get("btc_dominance", "N/A"),
            open_positions=market_context.get("open_positions", 0),
            daily_pnl=market_context.get("daily_pnl", "0"),
            available_krw=market_context.get("available_krw", "N/A"),
        )

        response = await self._chat(prompt)
        decision = self._parse_decision(response)

        return AIDecision(
            model=self.model,
            ticker=signal.ticker,
            decision=decision.get("decision", "SKIP"),
            reasoning=decision.get("reasoning", response),
            confidence=decision.get("confidence", 0.5),
            market_context=market_context,
        )

    async def analyze_market(self, context: Dict[str, Any]) -> str:
        """Get market analysis from Opus."""
        prompt = OPUS_MARKET_ANALYSIS.format(
            fear_greed=context.get("fear_greed", "N/A"),
            classification=context.get("classification", "N/A"),
            btc_dominance=context.get("btc_dominance", "N/A"),
            btc_change=context.get("btc_change", 0),
            correlation_data=context.get("correlation_data", "No data"),
            recent_events=context.get("recent_events", "No events"),
        )
        return await self._chat(prompt)

    async def discuss(self, message: str) -> str:
        """Free-form discussion with Opus."""
        return await self._chat(message)

    async def _chat(self, message: str) -> str:
        """Send message to Opus and get response."""
        self.conversation.add_user(message)

        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self.conversation.get_system_message(),
                messages=self.conversation.get_non_system_messages(),
            )
            text = response.content[0].text
            self.conversation.add_assistant(text)
            return text
        except Exception as e:
            logger.error("opus.error", error=str(e))
            return f"Error: {e}"

    @staticmethod
    def _parse_decision(response: str) -> Dict[str, Any]:
        """Parse structured decision from Opus response."""
        result: Dict[str, Any] = {
            "decision": "SKIP",
            "confidence": 0.5,
            "reasoning": response,
        }

        response_upper = response.upper()
        if "EXECUTE" in response_upper:
            result["decision"] = "EXECUTE"
        elif "MODIFY" in response_upper:
            result["decision"] = "MODIFY"

        # Try to extract confidence
        for line in response.split("\n"):
            line_lower = line.lower()
            if "confidence" in line_lower:
                import re
                numbers = re.findall(r"(\d+\.?\d*)", line)
                if numbers:
                    val = float(numbers[0])
                    if val > 1:
                        val = val / 100
                    result["confidence"] = min(max(val, 0.0), 1.0)
                    break

        return result
