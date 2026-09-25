import pandas as pd
import pytest

from quant_backtester.events import (
    EventQueue,
    FillEvent,
    MarketEvent,
    OrderEvent,
    SignalEvent,
    stream_market_events,
)


def sample_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 100.0],
            "Close": [104.0, 102.0],
            "Volume": [1000.0, 1200.0],
        },
        index=pd.date_range("2024-01-01", periods=2),
    )


def test_stream_market_events_replays_bars_in_order() -> None:
    events = list(stream_market_events(sample_bars(), symbol="TEST"))

    assert [event.timestamp for event in events] == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
    ]
    assert events[0].close == pytest.approx(104.0)
    assert events[0].symbol == "TEST"


def test_event_queue_is_first_in_first_out() -> None:
    queue = EventQueue()
    timestamp = pd.Timestamp("2024-01-01")

    queue.put(MarketEvent(timestamp, "TEST", 100.0, 101.0, 99.0, 100.5, 10.0))
    queue.put(SignalEvent(timestamp, "TEST", "LONG"))
    queue.put(OrderEvent(timestamp, "TEST", "BUY", 5))

    assert isinstance(queue.get(), MarketEvent)
    assert isinstance(queue.get(), SignalEvent)
    assert isinstance(queue.get(), OrderEvent)
    assert queue.get() is None


def test_fill_cash_impact_signs_and_commission() -> None:
    timestamp = pd.Timestamp("2024-01-01")

    buy = FillEvent(timestamp, "TEST", "BUY", 10, 100.0, commission=1.0)
    sell = FillEvent(timestamp, "TEST", "SELL", 10, 100.0, commission=1.0)

    assert buy.cash_impact == pytest.approx(-1001.0)
    assert sell.cash_impact == pytest.approx(999.0)


def test_fill_market_impact_scales_with_volume_participation() -> None:
    timestamp = pd.Timestamp("2024-01-01")

    liquid = FillEvent(timestamp, "TEST", "BUY", 10, 100.0, market_impact_bps=100.0, volume=1000.0)
    illiquid = FillEvent(timestamp, "TEST", "BUY", 10, 100.0, market_impact_bps=100.0, volume=100.0)

    assert liquid.impact_bps == pytest.approx(1.0)
    assert liquid.execution_price == pytest.approx(100.01)
    assert illiquid.impact_bps == pytest.approx(10.0)
    assert illiquid.execution_price == pytest.approx(100.10)


def test_events_reject_invalid_values() -> None:
    timestamp = pd.Timestamp("2024-01-01")

    with pytest.raises(ValueError, match="Direction must be"):
        SignalEvent(timestamp, "TEST", "SIDEWAYS")
    with pytest.raises(ValueError, match="Order quantity must be positive"):
        OrderEvent(timestamp, "TEST", "BUY", 0)
    with pytest.raises(ValueError, match="Fill price must be positive"):
        FillEvent(timestamp, "TEST", "BUY", 1, 0.0)
