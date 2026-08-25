"""Tests for loading OHLCV CSV files."""

from pathlib import Path

import pandas as pd
import pytest

from app.config.settings import SAMPLE_CSV
from app.data.loader import DataLoadError, load_ohlcv_csv


def test_load_valid_sample_csv() -> None:
    """The bundled synthetic sample CSV should load and be sorted."""
    dataframe = load_ohlcv_csv(SAMPLE_CSV)

    assert not dataframe.empty
    assert list(dataframe.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert pd.api.types.is_datetime64_any_dtype(dataframe["timestamp"])
    assert dataframe["timestamp"].is_monotonic_increasing
    assert len(dataframe) == 8


def test_load_valid_csv_from_temp_file(tmp_path: Path) -> None:
    """A well-formed CSV written to a temp folder should load correctly."""
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-02-01 01:00:00,10,11,9,10.5,100\n"
        "2024-02-01 00:00:00,9,10,8,9.5,80\n",
        encoding="utf-8",
    )

    dataframe = load_ohlcv_csv(csv_path)

    assert len(dataframe) == 2
    assert dataframe.iloc[0]["timestamp"] < dataframe.iloc[1]["timestamp"]
    assert dataframe.iloc[0]["open"] == 9


def test_missing_file_raises_useful_error(tmp_path: Path) -> None:
    """A missing file should raise DataLoadError with the path in the message."""
    missing = tmp_path / "does_not_exist.csv"

    with pytest.raises(DataLoadError, match="not found"):
        load_ohlcv_csv(missing)
