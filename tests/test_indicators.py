"""Tests for EMA, RSI, and add_indicators (no look-ahead)."""

import numpy as np
import pandas as pd
import pytest

from app.config.settings import SAMPLE_CSV
from app.data.loader import load_ohlcv_csv
from app.data.validator import validate_ohlcv
from app.indicators.indicators import add_indicators, calculate_ema, calculate_rsi


def _ohlcv_from_closes(closes: list[float]) -> pd.DataFrame:
    """Build a tiny synthetic OHLCV table from a list of close prices."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=len(closes), freq="h"),
            "open": closes,
            "high": [price + 1.0 for price in closes],
            "low": [price - 1.0 for price in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


def _recursive_ema(values: list[float], period: int) -> list[float]:
    """Independent EMA recurrence for checking pandas ewm(span, adjust=False)."""
    multiplier = 2.0 / (period + 1)
    ema = [values[0]]
    for price in values[1:]:
        ema.append(price * multiplier + ema[-1] * (1.0 - multiplier))
    return ema


def test_ema_matches_standard_recurrence() -> None:
    closes = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    period = 3
    actual = calculate_ema(closes, period)
    expected = _recursive_ema(closes.tolist(), period)

    assert pd.isna(actual.iloc[0])
    assert pd.isna(actual.iloc[1])
    for index in range(period - 1, len(closes)):
        assert actual.iloc[index] == pytest.approx(expected[index])


def test_ema_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        calculate_ema(pd.Series([1.0, 2.0, 3.0]), 0)


def test_rsi_is_100_on_a_steady_rise() -> None:
    closes = pd.Series([float(i) for i in range(1, 21)])
    rsi = calculate_rsi(closes, period=14)

    assert rsi.iloc[:14].isna().all()
    assert rsi.iloc[-1] == pytest.approx(100.0)


def test_rsi_is_0_on_a_steady_fall() -> None:
    closes = pd.Series([float(i) for i in range(20, 0, -1)])
    rsi = calculate_rsi(closes, period=14)

    assert rsi.iloc[-1] == pytest.approx(0.0)


def test_rsi_is_50_when_price_does_not_move() -> None:
    closes = pd.Series([10.0] * 20)
    rsi = calculate_rsi(closes, period=14)

    assert rsi.iloc[-1] == pytest.approx(50.0)


def test_add_indicators_appends_expected_columns() -> None:
    dataframe = load_ohlcv_csv(SAMPLE_CSV)
    validate_ohlcv(dataframe)
    result = add_indicators(dataframe)

    assert list(result.columns[:9]) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ema_20",
        "ema_50",
        "rsi_14",
    ]
    pd.testing.assert_frame_equal(
        result[["timestamp", "open", "high", "low", "close", "volume"]],
        dataframe,
    )


def test_add_indicators_uses_custom_periods_in_column_names() -> None:
    result = add_indicators(
        _ohlcv_from_closes([100.0, 101.0, 102.0, 103.0, 104.0]),
        ema_fast_period=2,
        ema_slow_period=3,
        rsi_period=2,
    )
    assert "ema_2" in result.columns
    assert "ema_3" in result.columns
    assert "rsi_2" in result.columns


def test_indicators_do_not_use_future_data() -> None:
    """Values at row i from the full series must match a prefix of length i+1."""
    closes = [100.0 + (i % 7) - 3.0 + i * 0.05 for i in range(80)]
    full = add_indicators(_ohlcv_from_closes(closes))
    cutoff = 60
    prefix = add_indicators(_ohlcv_from_closes(closes[:cutoff]))

    for column in ("ema_20", "ema_50", "rsi_14"):
        compared = pd.DataFrame(
            {
                "full": full[column].iloc[:cutoff].reset_index(drop=True),
                "prefix": prefix[column].reset_index(drop=True),
            }
        )
        both_valid = compared["full"].notna() & compared["prefix"].notna()
        assert both_valid.any()
        np.testing.assert_allclose(
            compared.loc[both_valid, "full"].to_numpy(),
            compared.loc[both_valid, "prefix"].to_numpy(),
            rtol=0.0,
            atol=1e-12,
        )
        # NaN locations in the prefix must also be NaN in the full series.
        assert full[column].iloc[:cutoff].isna().equals(prefix[column].isna())
