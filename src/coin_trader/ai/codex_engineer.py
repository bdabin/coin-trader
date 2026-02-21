"""Codex 5.3 AI engineer — code generation and backtesting."""

from __future__ import annotations

from typing import Any, Dict

import structlog

from coin_trader.ai.prompts import CODEX_BACKTEST, CODEX_MUTATION

logger = structlog.get_logger()


class CodexEngineer:
    """OpenAI Codex 5.3 for code generation and analysis."""

    def __init__(self, api_key: str, model: str = "codex-5.3") -> None:
        self.api_key = api_key
        self.model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    async def generate_backtest(
        self,
        strategy_name: str,
        template: str,
        params: Dict[str, Any],
        period_days: int = 30,
    ) -> str:
        """Generate backtest code for a strategy."""
        prompt = CODEX_BACKTEST.format(
            strategy_name=strategy_name,
            template=template,
            params=str(params),
            period_days=period_days,
        )
        return await self._complete(prompt)

    async def generate_mutations(
        self,
        parent_name: str,
        parent_params: Dict[str, Any],
        parent_return: float,
        mutation_type: str = "exploration",
        ancestor_patterns: str = "",
    ) -> str:
        """Generate mutated strategy parameters."""
        prompt = CODEX_MUTATION.format(
            parent_name=parent_name,
            parent_params=str(parent_params),
            parent_return=parent_return,
            mutation_type=mutation_type,
            ancestor_patterns=ancestor_patterns,
        )
        return await self._complete(prompt)

    async def analyze_code(self, code: str, question: str) -> str:
        """Analyze code and answer questions about it."""
        prompt = f"Analyze this code:\n\n```python\n{code}\n```\n\n{question}"
        return await self._complete(prompt)

    async def _complete(self, prompt: str) -> str:
        """Send completion request to Codex."""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("codex.error", error=str(e))
            return f"Error: {e}"
