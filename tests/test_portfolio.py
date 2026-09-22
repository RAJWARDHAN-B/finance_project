import pandas as pd
import pytest

from quant_backtester.events import FillEvent
from quant_backtester.portfolio import Portfolio


def test_portfolio_tracks_cash_and_positions_after_buy_fill() -> None:
    portfolio = Portfolio(initial_cash=10000.0)
    fill = FillEvent(
        timestamp=pd.Timestamp("2024-01-02"),
        symbol="TEST",
        side="BUY",
        quantity=10,
        price=100.0,
        commission=5.0,
    )

    portfolio.update_from_fill(fill)

    assert portfolio.cash == 8995.0
    assert portfolio.positions["TEST"] == 10
    assert portfolio.total_equity({"TEST": 110.0}) == pytest.approx(10095.0)


def test_portfolio_updates_positions_on_sell_fill() -> None:
    portfolio = Portfolio(initial_cash=10000.0)
    portfolio.update_from_fill(
        FillEvent(
            timestamp=pd.Timestamp("2024-01-01"),
            symbol="TEST",
            side="BUY",
            quantity=20,
            price=50.0,
            commission=0.0,
        )
    )

    portfolio.update_from_fill(
        FillEvent(
            timestamp=pd.Timestamp("2024-01-02"),
            symbol="TEST",
            side="SELL",
            quantity=5,
            price=60.0,
            commission=0.0,
        )
    )

    assert portfolio.positions["TEST"] == 15
    assert portfolio.cash == 9300.0


def test_portfolio_rejects_negative_or_zero_quantity() -> None:
    portfolio = Portfolio(initial_cash=10000.0)

    try:
        portfolio.update_from_fill(
            FillEvent(
                timestamp=pd.Timestamp("2024-01-02"),
                symbol="TEST",
                side="BUY",
                quantity=0,
                price=100.0,
            )
        )
        assert False, "Expected ValueError for invalid fill quantity"
    except ValueError:
        pass
