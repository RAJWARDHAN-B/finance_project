import pandas as pd

from quant_backtester.events import MarketEvent
from quant_backtester.strategy import MeanReversionStrategy


def build_market_event(close_value: float, timestamp: str = "2024-01-05") -> MarketEvent:
    return MarketEvent(
        timestamp=pd.Timestamp(timestamp),
        symbol="TEST",
        open=close_value,
        high=close_value + 1,
        low=close_value - 1,
        close=close_value,
        volume=1000.0,
    )


def test_strategy_generates_long_signal_when_price_is_far_below_mean() -> None:
    prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0])
    strategy = MeanReversionStrategy(lookback=20, z_threshold=1.5)
    event = build_market_event(80.0, timestamp="2024-01-21")

    signal = strategy.generate_signal(event, prices, position=0)

    assert signal is not None
    assert signal.direction == "LONG"


def test_strategy_generates_exit_signal_when_price_recovers() -> None:
    prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0])
    strategy = MeanReversionStrategy(lookback=20, z_threshold=1.5)
    event = build_market_event(118.0, timestamp="2024-01-21")

    signal = strategy.generate_signal(event, prices, position=1)

    assert signal is not None
    assert signal.direction == "EXIT"


def test_strategy_returns_none_when_not_enough_data() -> None:
    strategy = MeanReversionStrategy(lookback=20)
    prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0])
    event = build_market_event(90.0, timestamp="2024-01-10")

    assert strategy.generate_signal(event, prices, position=0) is None
