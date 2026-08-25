"""Shared paths and column names for the historical data pipeline."""

from pathlib import Path

# app/config/settings.py -> project root is two levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
SAMPLE_CSV = SAMPLE_DATA_DIR / "sample_ohlcv.csv"

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
NUMERIC_COLUMNS = ("open", "high", "low", "close", "volume")
