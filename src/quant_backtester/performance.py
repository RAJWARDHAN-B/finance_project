"""Performance and risk statistics for backtest equity and trade ledgers."""

from __future__ import annotations

from collections import deque
from math import isfinite, sqrt
from typing import Deque

import pandas as pd


def _closed_trade_pnls(trades: pd.DataFrame) -> list[float]:
    if trades.empty:
        return []

    required = {"side", "quantity", "execution_price", "commission"}
    if not required.issubset(trades.columns):
        raise ValueError(f"Trade ledger must contain: {', '.join(sorted(required))}")

    lots: dict[str, Deque[list[float]]] = {}
    realized: list[float] = []
    for trade in trades.to_dict("records"):
        symbol = str(trade.get("symbol", ""))
        quantity = int(trade["quantity"])
        price = float(trade["execution_price"])
        commission_per_share = float(trade["commission"]) / quantity
        symbol_lots = lots.setdefault(symbol, deque())

        if trade["side"] == "BUY":
            symbol_lots.append([float(quantity), price + commission_per_share])
            continue
        if trade["side"] != "SELL":
            raise ValueError("Trade side must be BUY or SELL")

        remaining = float(quantity)
        sell_proceeds_per_share = price - commission_per_share
        while remaining > 0:
            if not symbol_lots:
                raise ValueError(f"Trade ledger sells more {symbol} shares than it buys")
            lot = symbol_lots[0]
            matched = min(remaining, lot[0])
            realized.append(matched * (sell_proceeds_per_share - lot[1]))
            remaining -= matched
            lot[0] -= matched
            if lot[0] <= 1e-12:
                symbol_lots.popleft()

    return realized


def drawdown_series(equity_curve: pd.DataFrame) -> pd.Series:
    """Return percentage drawdown from the running equity peak."""
    if "equity" not in equity_curve.columns:
        raise ValueError("Equity curve must contain an 'equity' column")
    equity = equity_curve["equity"].astype(float)
    if equity.empty or not equity.map(isfinite).all() or (equity <= 0).any():
        raise ValueError("Equity values must be finite, positive, and non-empty")
    return (equity / equity.cummax() - 1.0).rename("drawdown")


def performance_report(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> dict[str, float | int | None]:
    """Calculate annualized performance, risk, drawdown, and closed-trade stats."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if not isfinite(risk_free_rate):
        raise ValueError("risk_free_rate must be finite")
    if len(equity_curve) < 2:
        raise ValueError("Equity curve must contain at least two observations")

    drawdowns = drawdown_series(equity_curve)
    equity = equity_curve["equity"].astype(float)
    returns = equity.pct_change().dropna()
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    annualized_return = (
        float((equity.iloc[-1] / equity.iloc[0]) ** (periods_per_year / len(returns)) - 1.0)
        if equity.iloc[-1] > 0
        else None
    )
    sample_volatility = float(returns.std(ddof=1)) if len(returns) > 1 else None
    volatility = (
        sample_volatility * sqrt(periods_per_year)
        if sample_volatility is not None
        else None
    )
    excess_returns = returns - risk_free_rate / periods_per_year
    sharpe = (
        float(excess_returns.mean() / sample_volatility * sqrt(periods_per_year))
        if sample_volatility is not None and sample_volatility > 0
        else None
    )

    underwater = drawdowns < 0
    durations: list[int] = []
    current_duration = 0
    for is_underwater in underwater:
        if is_underwater:
            current_duration += 1
        else:
            durations.append(current_duration)
            current_duration = 0
    durations.append(current_duration)

    trade_pnls = _closed_trade_pnls(trades)
    winners = [pnl for pnl in trade_pnls if pnl > 0]
    losers = [pnl for pnl in trade_pnls if pnl < 0]
    loss_total = abs(sum(losers))

    return {
        "start_equity": float(equity.iloc[0]),
        "final_equity": float(equity.iloc[-1]),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": float(drawdowns.min()),
        "max_drawdown_duration": max(durations, default=0),
        "observations": int(len(returns)),
        "trade_count": len(trade_pnls),
        "win_rate": len(winners) / len(trade_pnls) if trade_pnls else 0.0,
        "average_trade_pnl": sum(trade_pnls) / len(trade_pnls) if trade_pnls else None,
        "profit_factor": sum(winners) / loss_total if loss_total > 0 else None,
    }