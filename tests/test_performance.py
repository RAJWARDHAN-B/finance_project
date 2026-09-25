import pandas as pd
import pytest

from quant_backtester.performance import performance_report


def test_performance_report_calculates_return_risk_and_drawdown_metrics() -> None:
    equity = pd.DataFrame(
        {"equity": [100.0, 110.0, 99.0, 120.0]},
        index=pd.date_range("2024-01-01", periods=4),
    )

    report = performance_report(equity, pd.DataFrame(), periods_per_year=3)

    assert report["total_return"] == pytest.approx(0.2)
    assert report["max_drawdown"] == pytest.approx(-0.1)
    assert report["observations"] == 3
    assert report["trade_count"] == 0
    assert report["win_rate"] == 0.0


def test_performance_report_matches_completed_round_trip_pnl() -> None:
    equity = pd.DataFrame(
        {"equity": [1000.0, 1010.0, 1020.0]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    trades = pd.DataFrame(
        {
            "side": ["BUY", "SELL"],
            "quantity": [5, 5],
            "execution_price": [100.0, 110.0],
            "commission": [2.5, 2.5],
        }
    )

    report = performance_report(equity, trades)

    assert report["trade_count"] == 1
    assert report["win_rate"] == 1.0
    assert report["average_trade_pnl"] == pytest.approx(45.0)
    assert report["profit_factor"] is None


def test_performance_report_rejects_nonpositive_period_frequency() -> None:
    equity = pd.DataFrame({"equity": [100.0]})

    with pytest.raises(ValueError, match="periods_per_year"):
        performance_report(equity, pd.DataFrame(), periods_per_year=0)


def test_performance_report_uses_none_when_sample_volatility_is_undefined() -> None:
    equity = pd.DataFrame(
        {"equity": [100.0, 110.0]},
        index=pd.date_range("2024-01-01", periods=2),
    )

    report = performance_report(equity, pd.DataFrame())

    assert report["annualized_volatility"] is None
    assert report["sharpe_ratio"] is None