import pandas as pd
import pytest

from quant_backtester.multi_asset import run_multi_asset_backtest
from quant_backtester.strategy import MeanReversionStrategy


def build_prices(scale: float) -> pd.DataFrame:
    close = [100.0, 100.0, 80.0, 100.0, 100.0, 100.0]
    open_prices = [100.0, 100.0, 80.0, 100.0, 100.0, 100.0]
    frame = pd.DataFrame(
        {
            "Open": [value * scale for value in open_prices],
            "High": [value * scale + scale for value in [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]],
            "Low": [value * scale - scale for value in [100.0, 100.0, 80.0, 100.0, 100.0, 100.0]],
            "Close": [value * scale for value in close],
            "Volume": [1000.0] * 6,
        },
        index=pd.date_range("2024-01-01", periods=6),
    )
    return frame


def test_multi_asset_backtest_shares_cash_and_marks_all_positions() -> None:
    result = run_multi_asset_backtest(
        {"AAA": build_prices(1.0), "BBB": build_prices(0.5)},
        strategies={
            "AAA": MeanReversionStrategy(lookback=3, z_threshold=1.0),
            "BBB": MeanReversionStrategy(lookback=3, z_threshold=1.0),
        },
        initial_cash=1000.0,
        max_position_size=5,
    )

    assert list(result.trades["symbol"].drop_duplicates()) == ["AAA", "BBB"]
    assert result.portfolio.cash == pytest.approx(1000.0)
    assert set(result.rejections["reason"]) == {"max_position_size"}
    assert result.equity_curve.index.is_monotonic_increasing
    assert result.final_equity == pytest.approx(1000.0)


def test_multi_asset_backtest_requires_matching_strategy_symbols() -> None:
    with pytest.raises(ValueError, match="symbol sets"):
        run_multi_asset_backtest(
            {"AAA": build_prices(1.0)},
            strategies={"BBB": MeanReversionStrategy()},
        )