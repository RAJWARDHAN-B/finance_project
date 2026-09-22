"""Return calculations and a buy-and-hold benchmark."""

from typing import Union

import numpy as np
import pandas as pd


PriceInput = Union[pd.Series, pd.DataFrame]


def _close_prices(prices: PriceInput) -> pd.Series:
    """Extract and validate a one-dimensional close-price series."""
    if isinstance(prices, pd.DataFrame):
        if "Close" not in prices:
            raise ValueError("Price data must contain a Close column")
        prices = prices["Close"]

    if not isinstance(prices, pd.Series):
        raise TypeError("Prices must be a pandas Series or DataFrame")
    if prices.empty:
        raise ValueError("Price data cannot be empty")
    if prices.isnull().any() or (prices <= 0).any():
        raise ValueError("Close prices must be positive and non-null")

    return prices.astype(float).sort_index()


def simple_returns(prices: PriceInput) -> pd.Series:
    """Calculate percentage change between consecutive closing prices."""
    return _close_prices(prices).pct_change().rename("simple_return")


def log_returns(prices: PriceInput) -> pd.Series:
    """Calculate continuously compounded returns between closing prices."""
    close_prices = _close_prices(prices)
    return np.log(close_prices / close_prices.shift(1)).rename("log_return")


def cumulative_returns(prices: PriceInput) -> pd.Series:
    """Calculate growth of one unit invested at the first available price."""
    returns = simple_returns(prices).fillna(0.0)
    return (1.0 + returns).cumprod().rename("cumulative_return")


def buy_and_hold(prices: PriceInput, initial_capital: float = 10000.0) -> pd.DataFrame:
    """Create an equity curve for buying at the first close and holding."""
    if initial_capital <= 0:
        raise ValueError("Initial capital must be positive")

    close_prices = _close_prices(prices)
    cumulative = cumulative_returns(close_prices)
    equity = (initial_capital * cumulative).rename("equity")
    return pd.concat(
        [close_prices.rename("close"), simple_returns(close_prices), cumulative, equity],
        axis=1,
    )
