import pandas as pd
import pytest

from quant_backtester.backtest import run_backtest
from quant_backtester.strategy import MeanReversionStrategy


def test_backtest_executes_signal_on_next_bar_open() -> None:
    prices = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0, 90.0],
            "High": [101.0, 101.0, 101.0, 121.0],
            "Low": [99.0, 99.0, 79.0, 89.0],
            "Close": [100.0, 100.0, 80.0, 120.0],
            "Volume": [1000.0] * 4,
        },
        index=pd.date_range("2024-01-01", periods=4),
    )

    result = run_backtest(
        prices,
        symbol="TEST",
        strategy=MeanReversionStrategy(lookback=3, z_threshold=1.0),
        initial_cash=1000.0,
    )

    assert list(result.trades["side"]) == ["BUY"]
    assert result.trades.iloc[0]["timestamp"] == pd.Timestamp("2024-01-04")
    assert result.trades.iloc[0]["price"] == pytest.approx(90.0)
    assert result.equity_curve.index.is_monotonic_increasing
    assert result.final_equity == pytest.approx(1330.0)