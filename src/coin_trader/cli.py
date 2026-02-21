"""Typer CLI for coin-trader."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Optional

import structlog
import typer
from rich.console import Console

from coin_trader.config import load_config

app = typer.Typer(name="coin-trader", help="Real-time AI coin trading bot")
console = Console()
logger = structlog.get_logger()


def _get_strategies(config):
    """Instantiate enabled strategies from config."""
    # Import strategies to trigger registration
    from coin_trader.strategies import dip_buy, fear_greed, momentum  # noqa: F401
    from coin_trader.strategies import notice_alpha, volatility_breakout, volume_surge  # noqa: F401
    from coin_trader.strategies.registry import create_strategy

    strategies = []
    for name, scfg in config.strategies.items():
        if scfg.enabled:
            try:
                s = create_strategy(name, **scfg.params)
                strategies.append(s)
            except (ValueError, TypeError) as e:
                logger.warning("cli.strategy_skip", name=name, error=str(e))
    return strategies


@app.command()
def run(
    mode: str = typer.Option("paper", help="Trading mode: paper or live"),
    once: bool = typer.Option(False, help="Run single cycle then exit"),
) -> None:
    """Run the trading bot."""
    config = load_config()
    config.mode = mode
    strategies = _get_strategies(config)

    console.print(f"[bold]coin-trader[/bold] v0.1.0 | mode={mode} | strategies={len(strategies)}")

    if mode == "paper":
        from coin_trader.execution.paper import PaperTrader
        trader = PaperTrader(config, strategies)

        async def _run():
            # Single cycle: evaluate all tickers
            for ticker in config.trading.target_coins:
                tick = {
                    "ticker": ticker,
                    "price": 0,  # Would come from WebSocket/API
                    "price_history": [],
                }
                trades = await trader.process_tick(tick)
                for t in trades:
                    console.print(f"  Trade: {t.side.value} {t.ticker} @ {t.price}")

            summary = trader.get_summary()
            console.print(f"\nSummary: {summary}")

        asyncio.run(_run())
    else:
        console.print("[red]Live mode requires Phase 2 validation[/red]")


@app.command()
def leaderboard(top: int = typer.Option(10, help="Number of strategies to show")) -> None:
    """Show strategy leaderboard."""
    from coin_trader.reporting.leaderboard import Leaderboard

    board = Leaderboard(console)
    # Would load from DB in full implementation
    board.print_leaderboard([], top_n=top)
    console.print("(Load from database for real data)")


@app.command()
def report() -> None:
    """Generate daily report."""
    from coin_trader.domain.models import Portfolio
    from coin_trader.reporting.daily_report import DailyReport

    reporter = DailyReport(console)
    portfolio = Portfolio()
    reporter.print_report(portfolio, [], {})


@app.command()
def evolve(
    strategy: str = typer.Argument(..., help="Strategy template to evolve"),
    generations: int = typer.Option(3, help="Number of mutation generations"),
) -> None:
    """Evolve a strategy using AI + graph lineage."""
    from coin_trader.domain.evolution import StrategyEvolver

    evolver = StrategyEvolver()
    config = load_config()

    scfg = config.strategies.get(strategy)
    if not scfg:
        console.print(f"[red]Strategy '{strategy}' not found in config[/red]")
        raise typer.Exit(1)

    console.print(f"Evolving [bold]{strategy}[/bold] for {generations} generations")
    params = dict(scfg.params)

    for gen in range(generations):
        mutated = evolver.mutate_params(params)
        console.print(f"  Gen {gen + 1}: {mutated}")
        params = mutated


@app.command(name="ai")
def ai_cmd(
    action: str = typer.Argument(..., help="discuss|market|backtest"),
    message: str = typer.Option("", help="Message for discussion"),
) -> None:
    """AI commands: discuss, market analysis, backtest generation."""
    config = load_config()

    if not config.anthropic_api_key:
        console.print("[red]ANTHROPIC_API_KEY not set[/red]")
        raise typer.Exit(1)

    from coin_trader.ai.orchestrator import AIOrchestrator
    from coin_trader.ai.opus_analyst import OpusAnalyst

    opus = OpusAnalyst(api_key=config.anthropic_api_key, model=config.ai.opus_model)
    orchestrator = AIOrchestrator(opus=opus)

    async def _run():
        if action == "discuss":
            msg = message or "What's the current market outlook?"
            response = await orchestrator.discuss(msg)
            console.print(response)
        elif action == "market":
            response = await orchestrator.analyze_market({})
            console.print(response)
        else:
            console.print(f"Unknown action: {action}")

    asyncio.run(_run())


@app.command()
def graph(
    action: str = typer.Argument(..., help="lineage|correlations|events"),
    strategy_name: str = typer.Option("", "--strategy", help="Strategy name"),
    ticker: str = typer.Option("KRW-BTC", "--ticker", help="Ticker symbol"),
) -> None:
    """Graph database commands."""
    config = load_config()

    from coin_trader.graph.client import GraphClient
    from coin_trader.graph.coin_network import CoinNetwork
    from coin_trader.graph.strategy_lineage import StrategyLineage

    try:
        client = GraphClient(host=config.graph.falkordb_host, port=config.graph.falkordb_port)
        client.connect()

        if action == "lineage":
            lineage = StrategyLineage(client)
            if strategy_name:
                ancestors = lineage.get_ancestors(strategy_name)
                console.print(f"Ancestors of {strategy_name}: {ancestors}")
            else:
                top = lineage.get_top_strategies()
                console.print(f"Top strategies: {top}")

        elif action == "correlations":
            network = CoinNetwork(client)
            correlated = network.get_correlated_coins(ticker)
            console.print(f"Coins correlated with {ticker}: {correlated}")

        elif action == "events":
            console.print("Event propagation analysis - use with specific event type")

        else:
            console.print(f"Unknown graph action: {action}")

    except Exception as e:
        console.print(f"[red]Graph error: {e}[/red]")


@app.command()
def version() -> None:
    """Show version."""
    console.print("coin-trader v0.1.0")


if __name__ == "__main__":
    app()
