"""Event objects and the queue that moves them through the backtester."""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterator, Optional

import pandas as pd


DIRECTIONS = ("LONG", "EXIT")
SIDES = ("BUY", "SELL")


@dataclass(frozen=True)
class MarketEvent:
    """A new OHLCV bar became available."""

    timestamp: pd.Timestamp
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class SignalEvent:
    """A strategy's opinion, expressed without any knowledge of cash or size."""

    timestamp: pd.Timestamp
    symbol: str
    direction: str
    strength: float = 1.0

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            raise ValueError(f"Direction must be one of {DIRECTIONS}")


@dataclass(frozen=True)
class OrderEvent:
    """A concrete instruction produced by the portfolio."""

    timestamp: pd.Timestamp
    symbol: str
    side: str
    quantity: int

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise ValueError(f"Side must be one of {SIDES}")
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")


@dataclass(frozen=True)
class FillEvent:
    """A simulated broker's confirmation that an order executed."""

    timestamp: pd.Timestamp
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float = 0.0

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise ValueError(f"Side must be one of {SIDES}")
        if self.quantity <= 0:
            raise ValueError("Fill quantity must be positive")
        if self.price <= 0:
            raise ValueError("Fill price must be positive")

    @property
    def cash_impact(self) -> float:
        """Signed change in cash, including commission."""
        notional = self.quantity * self.price
        if self.side == "BUY":
            return -(notional + self.commission)
        return notional - self.commission


@dataclass
class EventQueue:
    """First-in, first-out queue so events are handled in the order created."""

    _events: Deque[object] = field(default_factory=deque)

    def put(self, event: object) -> None:
        self._events.append(event)

    def get(self) -> Optional[object]:
        return self._events.popleft() if self._events else None

    def __len__(self) -> int:
        return len(self._events)


def stream_market_events(prices: pd.DataFrame, symbol: str) -> Iterator[MarketEvent]:
    """Replay a validated OHLCV frame one bar at a time, oldest bar first."""
    for timestamp, bar in prices.iterrows():
        yield MarketEvent(
            timestamp=pd.Timestamp(timestamp),
            symbol=symbol,
            open=float(bar["Open"]),
            high=float(bar["High"]),
            low=float(bar["Low"]),
            close=float(bar["Close"]),
            volume=float(bar["Volume"]),
        )
