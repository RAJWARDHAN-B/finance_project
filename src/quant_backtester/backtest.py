"""Event-driven backtest orchestration for daily OHLCV data."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

import pandas as pd

from quant_backtester.data import validate_ohlcv
from quant_backtester.events import FillEvent, OrderEvent, SignalEvent, stream_market_events
from quant_backtester.portfolio import Portfolio
from quant_backtester.strategy import MeanReversionStrategy


@dataclass(frozen=True)
class ExecutionConfig:
    """Execution assumptions applied while converting signals into fills."""

    commission: float = 0.0
    slippage_bps: float = 0.0
    max_position_size: int | None = None

    def __post_init__(self) -> None:
        if self.commission < 0:
            raise ValueError("Commission cannot be negative")
        if self.slippage_bps < 0:
            raise ValueError("Slippage basis points cannot be negative")
        if self.max_position_size is not None and self.max_position_size <= 0:
            raise ValueError("Max position size must be positive when provided")


@dataclass
class BacktestResult:
    """Outputs from one reproducible backtest run."""

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    portfolio: Portfolio
    rejections: pd.DataFrame

    @property
    def final_equity(self) -> float:
        """Return the final marked-to-market portfolio value."""
        return float(self.equity_curve["equity"].iloc[-1])


def _order_from_signal(signal: SignalEvent, portfolio: Portfolio, price: float) -> OrderEvent | None:
    if signal.direction == "LONG" and portfolio.positions.get(signal.symbol, 0) == 0:
        quantity = floor(portfolio.cash / price)
        if quantity > 0:
            return OrderEvent(signal.timestamp, signal.symbol, "BUY", quantity)
    if signal.direction == "EXIT":
        quantity = portfolio.positions.get(signal.symbol, 0)
        if quantity > 0:
            return OrderEvent(signal.timestamp, signal.symbol, "SELL", quantity)
    return None


def run_backtest(
    prices: pd.DataFrame,
    symbol: str,
    strategy: MeanReversionStrategy,
    initial_cash: float = 10000.0,
    commission: float = 0.0,
    slippage_bps: float = 0.0,
    max_position_size: int | None = None,
) -> BacktestResult:
    """Replay bars, execute signals on the following bar's open, and track equity."""
    execution = ExecutionConfig(
        commission=commission,
        slippage_bps=slippage_bps,
        max_position_size=max_position_size,
    )
    cleaned = validate_ohlcv(prices)
    portfolio = Portfolio(initial_cash=initial_cash)
    close_history = pd.Series(dtype=float)
    pending_order: OrderEvent | None = None
    equity_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []
    rejection_rows: list[dict[str, object]] = []

    for market_event in stream_market_events(cleaned, symbol):
        if pending_order is not None:
            rejection_reason = ""
            if pending_order.side == "BUY":
                execution_price = market_event.open * (1.0 + (execution.slippage_bps / 10000.0))
                affordable_quantity = max(0, floor((portfolio.cash - execution.commission) / execution_price))
                quantity = min(pending_order.quantity, affordable_quantity)
                if quantity < pending_order.quantity:
                    rejection_reason = "insufficient_cash_after_execution_costs"
                if execution.max_position_size is not None:
                    capped_quantity = min(quantity, execution.max_position_size)
                    if capped_quantity < quantity:
                        rejection_reason = "max_position_size"
                    quantity = capped_quantity
            else:
                quantity = min(
                    pending_order.quantity,
                    portfolio.positions.get(pending_order.symbol, 0),
                )
                if quantity < pending_order.quantity:
                    rejection_reason = "insufficient_position"

            if quantity < pending_order.quantity:
                rejection_rows.append(
                    {
                        "timestamp": market_event.timestamp,
                        "symbol": pending_order.symbol,
                        "side": pending_order.side,
                        "requested_quantity": pending_order.quantity,
                        "filled_quantity": quantity,
                        "rejected_quantity": pending_order.quantity - quantity,
                        "reason": rejection_reason,
                    }
                )

            if quantity > 0:
                fill = FillEvent(
                    timestamp=market_event.timestamp,
                    symbol=pending_order.symbol,
                    side=pending_order.side,
                    quantity=quantity,
                    price=market_event.open,
                    commission=execution.commission,
                    slippage_bps=execution.slippage_bps,
                )
                portfolio.update_from_fill(fill)
                trade_rows.append(
                    {
                        "timestamp": fill.timestamp,
                        "symbol": fill.symbol,
                        "side": fill.side,
                        "quantity": fill.quantity,
                        "price": fill.execution_price,
                        "commission": fill.commission,
                        "execution_price": fill.execution_price,
                        "effective_cost": fill.effective_cost,
                    }
                )
            pending_order = None

        close_history.loc[market_event.timestamp] = market_event.close
        signal = strategy.generate_signal(
            market_event,
            close_history,
            position=portfolio.positions.get(symbol, 0),
        )
        if signal is not None:
            pending_order = _order_from_signal(signal, portfolio, market_event.close)

        equity_rows.append(
            {
                "timestamp": market_event.timestamp,
                "cash": portfolio.cash,
                "position": portfolio.positions.get(symbol, 0),
                "close": market_event.close,
                "equity": portfolio.total_equity({symbol: market_event.close}),
            }
        )

    equity_curve = pd.DataFrame(equity_rows).set_index("timestamp")
    trades = pd.DataFrame(
        trade_rows,
        columns=[
            "timestamp",
            "symbol",
            "side",
            "quantity",
            "price",
            "commission",
            "execution_price",
            "effective_cost",
        ],
    )
    rejections = pd.DataFrame(
        rejection_rows,
        columns=[
            "timestamp",
            "symbol",
            "side",
            "requested_quantity",
            "filled_quantity",
            "rejected_quantity",
            "reason",
        ],
    )
    return BacktestResult(
        equity_curve=equity_curve,
        trades=trades,
        portfolio=portfolio,
        rejections=rejections,
    )