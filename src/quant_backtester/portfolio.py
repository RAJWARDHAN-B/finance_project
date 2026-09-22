"""Portfolio accounting for a simple long-only backtester."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pandas as pd

from quant_backtester.events import FillEvent


@dataclass
class Portfolio:
    """Tracks cash, positions, and equity for one symbol or a small basket."""

    initial_cash: float = 10000.0
    cash: float = 10000.0
    positions: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("Initial cash must be positive")
        self.cash = float(self.initial_cash)

    def update_from_fill(self, fill: FillEvent) -> None:
        """Apply a fill to the portfolio accounts."""
        if fill.quantity <= 0:
            raise ValueError("Fill quantity must be positive")

        if fill.side == "BUY":
            self.cash += fill.cash_impact
            self.positions[fill.symbol] = self.positions.get(fill.symbol, 0) + fill.quantity
        elif fill.side == "SELL":
            self.cash += fill.cash_impact
            current_quantity = self.positions.get(fill.symbol, 0)
            new_quantity = current_quantity - fill.quantity
            if new_quantity < 0:
                raise ValueError(f"Cannot sell more than owned quantity for {fill.symbol}")
            self.positions[fill.symbol] = new_quantity
            if new_quantity == 0:
                self.positions.pop(fill.symbol, None)
        else:
            raise ValueError(f"Unsupported fill side: {fill.side}")

    def position_value(self, symbol: str, price: float) -> float:
        """Value of a symbol position at a given price."""
        return self.positions.get(symbol, 0) * price

    def total_equity(self, prices: Dict[str, float]) -> float:
        """Compute total equity as cash plus position values."""
        market_value = sum(self.position_value(symbol, price) for symbol, price in prices.items())
        return self.cash + market_value

    def as_dataframe(self) -> pd.DataFrame:
        """Return the current portfolio state as a row-like DataFrame."""
        return pd.DataFrame(
            [{
                "cash": self.cash,
                "positions": dict(self.positions),
                "total_positions": sum(self.positions.values()),
            }]
        )
