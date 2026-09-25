"""Time-ordered data splitting helpers for strategy research."""

from __future__ import annotations

from collections.abc import Iterator

import pandas as pd


def chronological_split(
    data: pd.DataFrame,
    train_fraction: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split data by time order; the trailing observations are held out."""
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be strictly between 0 and 1")
    if len(data) < 2:
        raise ValueError("At least two observations are required")

    split_index = int(len(data) * train_fraction)
    split_index = min(max(split_index, 1), len(data) - 1)
    return data.iloc[:split_index].copy(), data.iloc[split_index:].copy()


def walk_forward_splits(
    data: pd.DataFrame,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> Iterator[tuple[pd.DataFrame, pd.DataFrame]]:
    """Yield expanding training windows followed by non-overlapping test windows."""
    if train_size <= 0:
        raise ValueError("train_size must be positive")
    if test_size <= 0:
        raise ValueError("test_size must be positive")
    step = test_size if step_size is None else step_size
    if step <= 0:
        raise ValueError("step_size must be positive")
    if train_size >= len(data):
        raise ValueError("train_size must be smaller than the number of observations")

    test_start = train_size
    while test_start < len(data):
        test_end = min(test_start + test_size, len(data))
        yield data.iloc[:test_start].copy(), data.iloc[test_start:test_end].copy()
        test_start += step