"""Market data loading and validation helpers."""

from pathlib import Path
from typing import Optional, Union

import pandas as pd
import yfinance as yf


REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned OHLCV frame or raise ValueError for invalid data."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data]
    if missing_columns:
        raise ValueError(f"Missing OHLCV columns: {', '.join(missing_columns)}")

    cleaned = data.loc[:, REQUIRED_COLUMNS].copy()
    cleaned.index = pd.to_datetime(cleaned.index)
    cleaned = cleaned.sort_index()

    if cleaned.index.has_duplicates:
        raise ValueError("Market data index contains duplicate timestamps")
    if cleaned[list(REQUIRED_COLUMNS)].isnull().any().any():
        raise ValueError("Market data contains missing values")
    if (cleaned["High"] < cleaned[["Open", "Close", "Low"]].max(axis=1)).any():
        raise ValueError("High prices must be at least as large as Open, Close, and Low")
    if (cleaned["Low"] > cleaned[["Open", "Close", "High"]].min(axis=1)).any():
        raise ValueError("Low prices must be no larger than Open, Close, and High")
    if (cleaned["Volume"] < 0).any():
        raise ValueError("Volume cannot be negative")

    return cleaned


def load_csv(path: Union[str, Path]) -> pd.DataFrame:
    """Load and validate OHLCV data from a CSV file."""
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    return validate_ohlcv(frame)


def download_history(
    ticker: str,
    start: str,
    end: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Download daily history from Yahoo Finance and optionally save it."""
    if not ticker.strip():
        raise ValueError("Ticker cannot be empty")

    downloaded = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    if downloaded.empty:
        raise ValueError(f"No market data returned for ticker {ticker!r}")
    if isinstance(downloaded.columns, pd.MultiIndex):
        downloaded.columns = downloaded.columns.get_level_values(0)

    cleaned = validate_ohlcv(downloaded)
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(destination)
    return cleaned
