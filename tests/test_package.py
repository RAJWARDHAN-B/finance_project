from quant_backtester import __version__
from quant_backtester.data import validate_ohlcv
import pandas as pd
import pytest


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
