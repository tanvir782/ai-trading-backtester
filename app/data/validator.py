"""Validate historical OHLCV DataFrames before they are used in later stages."""

import pandas as pd

from app.config.settings import NUMERIC_COLUMNS, REQUIRED_COLUMNS


class DataValidationError(Exception):
    """Raised when OHLCV data fails one or more validation checks."""


def collect_validation_errors(dataframe: pd.DataFrame) -> list[str]:
    """Return a list of human-readable problems found in the DataFrame.

    An empty list means the data passed every check.
    """
    errors: list[str] = []

    if dataframe.empty:
        errors.append("The DataFrame is empty. OHLCV data must contain at least one row.")
        return errors

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in dataframe.columns]
    if missing_columns:
        errors.append(
            "Missing required column(s): "
            + ", ".join(missing_columns)
            + f". Expected columns: {', '.join(REQUIRED_COLUMNS)}."
        )
        return errors

    timestamp = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    invalid_timestamps = timestamp.isna()
    if invalid_timestamps.any():
        bad_rows = [str(index) for index in dataframe.index[invalid_timestamps]]
        errors.append(
            "Invalid or missing timestamp values at row index(es): "
            + ", ".join(bad_rows)
            + "."
        )

    duplicate_mask = timestamp.duplicated(keep=False) & timestamp.notna()
    if duplicate_mask.any():
        duplicate_values = timestamp[duplicate_mask].dt.strftime("%Y-%m-%d %H:%M:%S")
        unique_duplicates = sorted(set(duplicate_values.tolist()))
        errors.append(
            "Duplicate timestamps detected: " + ", ".join(unique_duplicates) + "."
        )

    comparable = timestamp.dropna()
    if not comparable.empty and not comparable.is_monotonic_increasing:
        errors.append("Timestamps are not sorted in chronological (oldest to newest) order.")

    missing_values = dataframe[list(REQUIRED_COLUMNS)].isna()
    for column in REQUIRED_COLUMNS:
        missing_count = int(missing_values[column].sum())
        if missing_count > 0:
            errors.append(
                f"Missing values detected in column '{column}' ({missing_count} row(s))."
            )

    for column in NUMERIC_COLUMNS:
        converted = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_numeric = converted.isna() & dataframe[column].notna()
        if invalid_numeric.any():
            bad_rows = [str(index) for index in dataframe.index[invalid_numeric]]
            errors.append(
                f"Column '{column}' contains non-numeric values at row index(es): "
                + ", ".join(bad_rows)
                + "."
            )

    return errors


def validate_ohlcv(dataframe: pd.DataFrame) -> None:
    """Validate an OHLCV DataFrame.

    Checks:
        1. Required columns exist.
        2. Timestamps can be parsed.
        3. Rows are sorted oldest to newest.
        4. Timestamps are unique.
        5. There are no missing values.
        6. OHLCV columns are numeric.
        7. The DataFrame is not empty.

    Raises:
        DataValidationError: If any check fails. The message lists every issue.
    """
    errors = collect_validation_errors(dataframe)
    if errors:
        details = "\n".join(f"- {item}" for item in errors)
        raise DataValidationError("OHLCV data failed validation:\n" + details)
