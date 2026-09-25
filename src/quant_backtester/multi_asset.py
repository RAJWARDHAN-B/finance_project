"""Shared-cash event-driven backtests across multiple symbols."""

from __future__ import annotations

from heapq import merge
from itertools import groupby
from math import floor

import pandas as pd

from quant_backtester.backtest import BacktestResult, ExecutionConfig, _order_from_signal
from quant_backtester.data import validate_ohlcv
from quant_backtester.events import FillEvent, OrderEvent, stream_market_events
from quant_backtester.portfolio import Portfolio
from quant_backtester.strategy import MeanReversionStrategy


def run_multi_asset_backtest(
    prices: dict[str, pd.DataFrame],
    strategies: dict[str, MeanReversionStrategy],
    initial_cash: float = 10000.0,
    commission: float = 0.0,
    slippage_bps: float = 0.0,
    max_position_size: int | None = None,
) -> BacktestResult:
    """Replay per-symbol bars in timestamp order against one shared portfolio."""
    if not prices:
        raise ValueError("At least one symbol is required")
    if set(prices) != set(strategies):
        raise ValueError("Price and strategy symbol sets must match")

    execution = ExecutionConfig(
        commission=commission,
        slippage_bps=slippage_bps,
        max_position_size=max_position_size,
    )
    portfolio = Portfolio(initial_cash=initial_cash)
    cleaned = {symbol: validate_ohlcv(frame) for symbol, frame in prices.items()}
    market_events = merge(
        *(stream_market_events(frame, symbol) for symbol, frame in cleaned.items()),
        key=lambda event: (event.timestamp, event.symbol),
    )
    close_history = {symbol: pd.Series(dtype=float) for symbol in cleaned}
    pending_orders: dict[str, OrderEvent] = {}
    latest_prices: dict[str, float] = {}
    equity_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []
    rejection_rows: list[dict[str, object]] = []

    for timestamp, timestamp_events in groupby(market_events, key=lambda event: event.timestamp):
        for market_event in timestamp_events:
            symbol = market_event.symbol
            order = pending_orders.pop(symbol, None)
            if order is not None:
                rejection_reason = ""
                if order.side == "BUY":
                    execution_price = market_event.open * (1.0 + execution.slippage_bps / 10000.0)
                    affordable = max(0, floor((portfolio.cash - execution.commission) / execution_price))
                    quantity = min(order.quantity, affordable)
                    if quantity < order.quantity:
                        rejection_reason = "insufficient_cash_after_execution_costs"
                    if execution.max_position_size is not None:
                        available_position = max(
                            0,
                            execution.max_position_size - portfolio.positions.get(symbol, 0),
                        )
                        capped_quantity = min(quantity, available_position)
                        if capped_quantity < quantity:
                            rejection_reason = "max_position_size"
                        quantity = capped_quantity
                else:
                    quantity = min(order.quantity, portfolio.positions.get(symbol, 0))
                    if quantity < order.quantity:
                        rejection_reason = "insufficient_position"

                if quantity < order.quantity:
                    rejection_rows.append(
                        {
                            "timestamp": market_event.timestamp,
                            "symbol": symbol,
                            "side": order.side,
                            "requested_quantity": order.quantity,
                            "filled_quantity": quantity,
                            "rejected_quantity": order.quantity - quantity,
                            "reason": rejection_reason,
                        }
                    )

                if quantity > 0:
                    fill = FillEvent(
                        timestamp=market_event.timestamp,
                        symbol=symbol,
                        side=order.side,
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

            latest_prices[symbol] = market_event.close
            close_history[symbol].loc[market_event.timestamp] = market_event.close
            signal = strategies[symbol].generate_signal(
                market_event,
                close_history[symbol],
                position=portfolio.positions.get(symbol, 0),
            )
            if signal is not None:
                next_order = _order_from_signal(signal, portfolio, market_event.close)
                if next_order is not None:
                    pending_orders[symbol] = next_order

        equity_row: dict[str, object] = {
            "timestamp": timestamp,
            "cash": portfolio.cash,
            "equity": portfolio.total_equity(latest_prices),
        }
        for symbol in cleaned:
            equity_row[f"position_{symbol}"] = portfolio.positions.get(symbol, 0)
            equity_row[f"close_{symbol}"] = latest_prices.get(symbol)
        equity_rows.append(equity_row)

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