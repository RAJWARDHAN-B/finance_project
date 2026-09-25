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
    slippage_bps: float = 0.0
    market_impact_bps: float = 0.0
    volume: Optional[float] = None

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise ValueError(f"Side must be one of {SIDES}")
        if self.quantity <= 0:
            raise ValueError("Fill quantity must be positive")
        if self.price <= 0:
            raise ValueError("Fill price must be positive")
        if self.commission < 0:
            raise ValueError("Commission cannot be negative")
        if self.slippage_bps < 0:
            raise ValueError("Slippage cannot be negative")
        if self.market_impact_bps < 0:
            raise ValueError("Market impact cannot be negative")
        if self.volume is not None and self.volume < 0:
            raise ValueError("Volume cannot be negative")

    @property
    def impact_bps(self) -> float:
        """Return impact scaled by this order's share of the bar volume."""
        if self.volume is None or self.volume == 0:
            return 0.0
        return float(self.market_impact_bps * self.quantity / self.volume)

    @property
    def execution_price(self) -> float:
        """Execution price after slippage adjustment."""
        if self.slippage_bps == 0 and self.impact_bps == 0:
            return float(self.price)
        slippage_fraction = (self.slippage_bps + self.impact_bps) / 10000.0
        if self.side == "BUY":
            return float(self.price * (1.0 + slippage_fraction))
        return float(self.price * (1.0 - slippage_fraction))

    @property
    def effective_cost(self) -> float:
        """Actual notional cost including commission for the fill."""
        notional = self.quantity * self.execution_price
        if self.side == "BUY":
            return notional + self.commission
        return notional - self.commission

    @property
    def cash_impact(self) -> float:
        """Signed change in cash, including commission and slippage."""
        if self.side == "BUY":
            return -self.effective_cost
        return self.effective_cost


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
