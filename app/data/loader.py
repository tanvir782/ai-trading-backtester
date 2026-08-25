"""Load historical OHLCV data from CSV files."""

from pathlib import Path

import pandas as pd

from app.config.settings import REQUIRED_COLUMNS


class DataLoadError(Exception):
    """Raised when an OHLCV CSV file cannot be loaded."""


def load_ohlcv_csv(csv_path: str | Path) -> pd.DataFrame:
    """Read an OHLCV CSV, parse timestamps, and sort oldest to newest.

    Expected columns: timestamp, open, high, low, close, volume.

    Args:
        csv_path: Path to a CSV file. Use pathlib.Path so this works on
            Windows, macOS, and Linux.

    Returns:
        A pandas DataFrame sorted by timestamp.

    Raises:
        DataLoadError: If the file is missing, unreadable, or empty of columns.
    """
    path = Path(csv_path)

    if not path.exists():
        raise DataLoadError(f"CSV file not found: {path}")

    if not path.is_file():
        raise DataLoadError(f"Path is not a file: {path}")

    try:
        dataframe = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError(f"CSV file is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise DataLoadError(f"Could not parse CSV file: {path}\n{exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Could not read CSV file: {path}\n{exc}") from exc

    if dataframe.columns.empty:
        raise DataLoadError(f"CSV file has no columns: {path}")

    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(
            dataframe["timestamp"],
            errors="coerce",
            format="mixed",
        )
        dataframe = dataframe.sort_values("timestamp", kind="mergesort").reset_index(
            drop=True
        )

    # Keep a stable column order when the expected names are present.
    present_required = [col for col in REQUIRED_COLUMNS if col in dataframe.columns]
    extra_columns = [col for col in dataframe.columns if col not in REQUIRED_COLUMNS]
    if present_required:
        dataframe = dataframe.loc[:, present_required + extra_columns]

    return dataframe
