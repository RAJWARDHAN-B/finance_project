"""Event-driven backtest orchestration for daily OHLCV data."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

import pandas as pd

from quant_backtester.data import validate_ohlcv
from quant_backtester.events import FillEvent, OrderEvent, SignalEvent, stream_market_events
from quant_backtester.portfolio import Portfolio
from quant_backtester.strategy import MeanReversionStrategy


@dataclass
class BacktestResult:
    """Outputs from one reproducible backtest run."""

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    portfolio: Portfolio

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
) -> BacktestResult:
    """Replay bars, execute signals on the following bar's open, and track equity."""
    cleaned = validate_ohlcv(prices)
    portfolio = Portfolio(initial_cash=initial_cash)
    close_history = pd.Series(dtype=float)
    pending_order: OrderEvent | None = None
    equity_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []

    for market_event in stream_market_events(cleaned, symbol):
        if pending_order is not None:
            if pending_order.side == "BUY":
                quantity = min(
                    pending_order.quantity,
                    floor(portfolio.cash / market_event.open),
                )
            else:
                quantity = min(
                    pending_order.quantity,
                    portfolio.positions.get(pending_order.symbol, 0),
                )

            if quantity > 0:
                fill = FillEvent(
                    timestamp=market_event.timestamp,
                    symbol=pending_order.symbol,
                    side=pending_order.side,
                    quantity=quantity,
                    price=market_event.open,
                    commission=commission,
                )
                portfolio.update_from_fill(fill)
                trade_rows.append(
                    {
                        "timestamp": fill.timestamp,
                        "symbol": fill.symbol,
                        "side": fill.side,
                        "quantity": fill.quantity,
                        "price": fill.price,
                        "commission": fill.commission,
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
        columns=["timestamp", "symbol", "side", "quantity", "price", "commission"],
    )
    return BacktestResult(equity_curve=equity_curve, trades=trades, portfolio=portfolio)