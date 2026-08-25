"""Tests for OHLCV DataFrame validation."""

from pathlib import Path

import pandas as pd
import pytest

from app.data.loader import load_ohlcv_csv
from app.data.validator import DataValidationError, validate_ohlcv


def _write_csv(tmp_path: Path, body: str) -> Path:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(body, encoding="utf-8")
    return csv_path


def test_valid_csv_passes_validation(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01 00:00:00,1,2,0.5,1.5,10\n"
        "2024-01-01 01:00:00,1.5,2.5,1.4,2.0,12\n",
    )
    dataframe = load_ohlcv_csv(csv_path)

    validate_ohlcv(dataframe)


def test_missing_column_detection(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "timestamp,open,high,low,close\n"
        "2024-01-01 00:00:00,1,2,0.5,1.5\n",
    )
    dataframe = load_ohlcv_csv(csv_path)

    with pytest.raises(DataValidationError, match="Missing required column"):
        validate_ohlcv(dataframe)


def test_invalid_timestamp_detection(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "timestamp,open,high,low,close,volume\n"
        "not-a-date,1,2,0.5,1.5,10\n"
        "2024-01-01 01:00:00,1.5,2.5,1.4,2.0,12\n",
    )
    dataframe = load_ohlcv_csv(csv_path)

    with pytest.raises(DataValidationError, match="Invalid or missing timestamp"):
        validate_ohlcv(dataframe)


def test_duplicate_timestamp_detection(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01 00:00:00,1,2,0.5,1.5,10\n"
        "2024-01-01 00:00:00,1.5,2.5,1.4,2.0,12\n",
    )
    dataframe = load_ohlcv_csv(csv_path)

    with pytest.raises(DataValidationError, match="Duplicate timestamps"):
        validate_ohlcv(dataframe)


def test_missing_value_detection(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01 00:00:00,1,2,0.5,1.5,10\n"
        "2024-01-01 01:00:00,1.5,,1.4,2.0,12\n",
    )
    dataframe = load_ohlcv_csv(csv_path)

    with pytest.raises(DataValidationError, match="Missing values detected"):
        validate_ohlcv(dataframe)


def test_invalid_numeric_data_detection(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path,
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01 00:00:00,1,2,0.5,1.5,10\n"
        "2024-01-01 01:00:00,abc,2.5,1.4,2.0,12\n",
    )
    dataframe = load_ohlcv_csv(csv_path)

    with pytest.raises(DataValidationError, match="non-numeric"):
        validate_ohlcv(dataframe)


def test_empty_dataframe_is_rejected() -> None:
    dataframe = pd.DataFrame(
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    with pytest.raises(DataValidationError, match="empty"):
        validate_ohlcv(dataframe)
