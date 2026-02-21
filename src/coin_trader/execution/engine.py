"""Event-driven execution engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

from coin_trader.config import AppConfig
from coin_trader.domain.models import Signal, SignalType, Trade
from coin_trader.domain.portfolio import PortfolioManager
from coin_trader.domain.risk import RiskManager
from coin_trader.domain.strategy import Strategy

logger = structlog.get_logger()


class ExecutionEngine:
    """Core trading engine: evaluates strategies, checks risk, executes trades."""

    def __init__(
        self,
        config: AppConfig,
        portfolio_manager: PortfolioManager,
        risk_manager: RiskManager,
        strategies: List[Strategy],
    ) -> None:
        self.config = config
        self.portfolio = portfolio_manager
        self.risk = risk_manager
        self.strategies = strategies
        self.trade_log: List[Trade] = []

    async def process_tick(self, tick: Dict[str, Any]) -> List[Trade]:
        """Process a single tick through all strategies."""
        ticker = tick.get("ticker", "")
        price = tick.get("price", 0)
        if not ticker or not price:
            return []

        trades: List[Trade] = []
        current_price = Decimal(str(price))

        # Update highest price for trailing stop
        self.portfolio.update_highest_price(ticker, current_price)

        # Check risk-based exits (stop-loss, take-profit, trailing stop)
        exit_trade = self._check_risk_exits(ticker, current_price)
        if exit_trade:
            trades.append(exit_trade)
            return trades  # Don't evaluate entry if we just exited

        # Evaluate each strategy
        for strategy in self.strategies:
            signal = await strategy.evaluate(ticker, self._build_market_data(ticker, tick))
            if signal is None:
                continue

            trade = self._execute_signal(signal, current_price)
            if trade:
                trades.append(trade)

        return trades

    def _check_risk_exits(self, ticker: str, current_price: Decimal) -> Optional[Trade]:
        """Check stop-loss, take-profit, and trailing stop."""
        open_positions = self.portfolio.get_open_positions()
        if ticker not in open_positions:
            return None

        position = open_positions[ticker]

        # Stop-loss
        sl_check = self.risk.check_stop_loss(position, current_price)
        if sl_check.allowed:
            return self.portfolio.execute_sell(
                position.strategy_name, ticker, current_price, reason=sl_check.reason
            )

        # Take-profit
        tp_check = self.risk.check_take_profit(position, current_price)
        if tp_check.allowed:
            return self.portfolio.execute_sell(
                position.strategy_name, ticker, current_price, reason=tp_check.reason
            )

        # Trailing stop
        ts_check = self.risk.check_trailing_stop(position, current_price)
        if ts_check.allowed:
            return self.portfolio.execute_sell(
                position.strategy_name, ticker, current_price, reason=ts_check.reason
            )

        return None

    def _execute_signal(self, signal: Signal, current_price: Decimal) -> Optional[Trade]:
        """Execute a signal after risk checks."""
        if signal.signal_type == SignalType.BUY:
            buy_amount = Decimal(str(self.config.trading.buy_amount))
            risk_check = self.risk.check_buy(signal, self.portfolio.portfolio, buy_amount)
            if not risk_check.allowed:
                logger.info("engine.buy_blocked", ticker=signal.ticker, reason=risk_check.reason)
                return None
            trade = self.portfolio.execute_buy(
                signal.strategy_name, signal.ticker, current_price, buy_amount, signal.reason
            )
            if trade:
                self.trade_log.append(trade)
                self.risk.record_trade_pnl(Decimal("0"))
            return trade

        elif signal.signal_type == SignalType.SELL:
            risk_check = self.risk.check_sell(signal, self.portfolio.portfolio)
            if not risk_check.allowed:
                logger.info("engine.sell_blocked", ticker=signal.ticker, reason=risk_check.reason)
                return None
            trade = self.portfolio.execute_sell(
                signal.strategy_name, signal.ticker, current_price, signal.reason
            )
            if trade and trade.profit:
                self.trade_log.append(trade)
                self.risk.record_trade_pnl(trade.profit)
            return trade

        return None

    def _build_market_data(self, ticker: str, tick: Dict[str, Any]) -> Dict[str, Any]:
        """Build market data dict for strategy evaluation."""
        open_positions = self.portfolio.get_open_positions()
        has_position = ticker in open_positions

        data: Dict[str, Any] = {
            "current_price": tick.get("price", 0),
            "volume": tick.get("volume", 0),
            "change_pct": tick.get("change_pct", 0),
            "high_price": tick.get("high_price", 0),
            "low_price": tick.get("low_price", 0),
            "has_position": has_position,
            "entry_price": 0,
            "price_history": tick.get("price_history", []),
        }

        if has_position:
            data["entry_price"] = float(open_positions[ticker].entry_price)

        return data

    def get_summary(self) -> Dict[str, Any]:
        """Return execution summary."""
        portfolio = self.portfolio.portfolio
        return {
            "krw_balance": str(portfolio.krw_balance),
            "total_trades": portfolio.total_trades,
            "winning_trades": portfolio.winning_trades,
            "win_rate": portfolio.win_rate,
            "total_profit": str(portfolio.total_profit),
            "open_positions": len(self.portfolio.get_open_positions()),
            "trade_log_count": len(self.trade_log),
        }
