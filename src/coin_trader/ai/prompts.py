"""AI prompt templates for Opus and Codex."""

from __future__ import annotations

OPUS_SYSTEM = """You are an expert cryptocurrency trading analyst powered by Claude Opus 4.6.
You assist a real-time AI coin trading bot with decision-making.

Your responsibilities:
1. Evaluate trading signals and decide whether to execute
2. Analyze market conditions considering fear/greed, social sentiment, correlations
3. Review strategy performance and suggest parameter adjustments
4. Identify risk factors and recommend protective actions

Always provide structured reasoning with confidence scores (0.0-1.0).
Be conservative — preserving capital is more important than catching every move.

Key context:
- Validated: Dip Buy (-7%/+2%/24h) = +23.82%, 100% win rate
- Failed: RSI (-58%), MA Cross (-34%), Bollinger (-75%)
- Risk limits: stop-loss 5%, take-profit 10%, trailing 3%, daily max loss 3%
"""

OPUS_SIGNAL_EVAL = """Evaluate this trading signal:

Signal: {signal_type} {ticker}
Strategy: {strategy_name}
Strength: {strength}
Reason: {reason}

Market Context:
- Fear & Greed Index: {fear_greed}
- 24h Change: {change_pct}%
- BTC Dominance: {btc_dominance}%

Current Portfolio:
- Open positions: {open_positions}
- Daily P&L: {daily_pnl}
- Available KRW: {available_krw}

Should we execute this signal? Respond with:
1. Decision: EXECUTE / SKIP / MODIFY
2. Confidence: 0.0 - 1.0
3. Reasoning: Brief explanation
4. Risk factors: Any concerns
"""

OPUS_STRATEGY_REVIEW = """Review strategy performance using graph lineage data:

Strategy: {strategy_name}
Template: {template}
Return: {return_pct}%
Win Rate: {win_rate}%
Total Trades: {total_trades}

Ancestor Performance (from FalkorDB):
{ancestor_data}

Top Strategy Parameters:
{top_params}

Questions:
1. Should this strategy continue running?
2. What parameter mutations would you suggest?
3. Are there concerning patterns in the lineage?
"""

OPUS_MARKET_ANALYSIS = """Analyze current market conditions:

Fear & Greed: {fear_greed} ({classification})
BTC Dominance: {btc_dominance}%
BTC 24h Change: {btc_change}%

Correlated Coins Alert (from FalkorDB):
{correlation_data}

Recent Events:
{recent_events}

Provide:
1. Market regime assessment (bull/bear/sideways/volatile)
2. Risk level (low/medium/high/extreme)
3. Recommended actions for current positions
4. Opportunities to watch
"""

CODEX_BACKTEST = """Generate a Python backtest script for this strategy:

Strategy: {strategy_name}
Template: {template}
Parameters: {params}

Data: Use the provided OHLCV dataframe with columns [timestamp, open, high, low, close, volume].
Period: Last {period_days} days.

Requirements:
- Calculate entry/exit signals based on the strategy parameters
- Track positions with 0.05% fee
- Output: total return %, win rate, max drawdown, Sharpe ratio
- Use pandas and numpy only
"""

CODEX_MUTATION = """Generate mutated strategy parameters:

Parent Strategy: {parent_name}
Parent Params: {parent_params}
Parent Return: {parent_return}%

Mutation Type: {mutation_type}

Successful Ancestor Patterns:
{ancestor_patterns}

Generate 3 child parameter sets that explore nearby parameter space.
Focus on the parameter ranges that historically performed well.
"""
