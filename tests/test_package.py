from quant_backtester import __version__
from quant_backtester.data import validate_ohlcv
import pandas as pd
import pytest
import numpy as np
from quant_backtester.returns import buy_and_hold, cumulative_returns, log_returns, simple_returns


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"


def test_validate_ohlcv_sorts_and_selects_required_columns() -> None:
    data = pd.DataFrame(
        {
            "Close": [101, 100],
            "Open": [100, 99],
            "High": [102, 101],
            "Low": [99, 98],
            "Volume": [1000, 1100],
            "Extra": ["ignore", "ignore"],
        },
        index=["2024-01-02", "2024-01-01"],
    )

    cleaned = validate_ohlcv(data)

    assert list(cleaned.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert cleaned.index[0] == pd.Timestamp("2024-01-01")


def test_validate_ohlcv_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="Missing OHLCV columns"):
        validate_ohlcv(pd.DataFrame({"Close": [100]}))


def test_return_calculations_use_close_prices() -> None:
    prices = pd.Series([100.0, 110.0, 99.0], index=pd.date_range("2024-01-01", periods=3))

    simple = simple_returns(prices)
    logarithmic = log_returns(prices)

    assert pd.isna(simple.iloc[0])
    assert simple.iloc[1] == pytest.approx(0.10)
    assert logarithmic.iloc[1] == pytest.approx(np.log(1.10))
    assert cumulative_returns(prices).iloc[-1] == pytest.approx(0.99)


def test_buy_and_hold_builds_equity_curve() -> None:
    prices = pd.Series([100.0, 110.0, 120.0], index=pd.date_range("2024-01-01", periods=3))

    result = buy_and_hold(prices, initial_capital=1000.0)

    assert list(result.columns) == ["close", "simple_return", "cumulative_return", "equity"]
    assert result["equity"].iloc[0] == pytest.approx(1000.0)
    assert result["equity"].iloc[-1] == pytest.approx(1200.0)
