"""OHLCV technical indicators (historical candles only — no look-ahead).

Every value at row *i* is computed from closes at rows *0..i*. pandas
rolling/EWM windows are left-aligned (the default). We never set
``center=True`` and never shift data backward to peek at the future.
"""

from __future__ import annotations

import pandas as pd

from app.config.settings import REQUIRED_COLUMNS


def calculate_ema(close: pd.Series, period: int) -> pd.Series:
    """Return the exponential moving average of ``close``.

    Uses the common trading EMA recurrence:

        multiplier = 2 / (period + 1)
        EMA[i] = close[i] * multiplier + EMA[i - 1] * (1 - multiplier)

    pandas ``ewm(span=period, adjust=False)`` implements that formula.
    ``min_periods=period`` leaves the first ``period - 1`` rows as NaN
    so we do not treat a half-formed average as a real signal.

    Args:
        close: Closing prices in chronological order (oldest first).
        period: EMA lookback length (for example 20 or 50).

    Returns:
        A Series aligned to ``close``. Early rows are NaN until enough
        history exists.
    """
    if period < 1:
        raise ValueError(f"EMA period must be at least 1, got {period}.")

    return close.astype(float).ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Return Wilder's Relative Strength Index of ``close``.

    Steps (standard RSI, period *N*, default 14):

    1. ``change[i] = close[i] - close[i - 1]`` (no future close is used).
    2. Gain is the positive part of that change; loss is the absolute
       value of the negative part.
    3. Average gain and average loss with Wilder smoothing
       (``alpha = 1 / period``, ``adjust=False``). This is an EMA that
       only looks at the current and past gains/losses.
    4. ``RS = average_gain / average_loss``
    5. ``RSI = 100 - (100 / (1 + RS))``

    Special cases after enough history exists:

    - Average loss is 0 and average gain > 0 → RSI = 100 (only advances).
    - Average gain is 0 and average loss > 0 → RSI = 0 (only declines).
    - Both averages are 0 → RSI = 50 (no movement; treated as neutral).

    Args:
        close: Closing prices in chronological order (oldest first).
        period: RSI lookback length (default 14).

    Returns:
        A Series aligned to ``close``. Values are NaN until ``period``
        average-gain/loss observations exist.
    """
    if period < 1:
        raise ValueError(f"RSI period must be at least 1, got {period}.")

    price = close.astype(float)
    change = price.diff()
    gain = change.clip(lower=0.0)
    loss = (-change).clip(lower=0.0)

    average_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rsi = pd.Series(index=price.index, dtype="float64")

    both_zero = (average_gain == 0) & (average_loss == 0)
    no_loss = (average_loss == 0) & (average_gain > 0)
    no_gain = (average_gain == 0) & (average_loss > 0)
    ratio_ok = average_loss > 0

    rsi[both_zero] = 50.0
    rsi[no_loss] = 100.0
    rsi[no_gain] = 0.0
    relative_strength = average_gain[ratio_ok] / average_loss[ratio_ok]
    rsi[ratio_ok] = 100.0 - (100.0 / (1.0 + relative_strength))

    return rsi


def add_indicators(
    dataframe: pd.DataFrame,
    ema_fast_period: int = 20,
    ema_slow_period: int = 50,
    rsi_period: int = 14,
) -> pd.DataFrame:
    """Return a copy of OHLCV data with EMA and RSI columns added.

    Default column names match Stage 2: ``ema_20``, ``ema_50``, ``rsi_14``.
    If you change the periods, the names follow ``ema_{period}`` and
    ``rsi_{period}``.

    The original OHLCV columns are not modified. Indicator values at row
    *i* do not use rows after *i*.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in dataframe.columns]
    if missing:
        raise ValueError(
            "DataFrame is missing required OHLCV column(s): " + ", ".join(missing)
        )

    result = dataframe.copy()
    close = result["close"]
    ema_fast_name = f"ema_{ema_fast_period}"
    ema_slow_name = f"ema_{ema_slow_period}"
    rsi_name = f"rsi_{rsi_period}"

    result[ema_fast_name] = calculate_ema(close, ema_fast_period)
    result[ema_slow_name] = calculate_ema(close, ema_slow_period)
    result[rsi_name] = calculate_rsi(close, rsi_period)

    preferred = list(REQUIRED_COLUMNS) + [ema_fast_name, ema_slow_name, rsi_name]
    extra = [col for col in result.columns if col not in preferred]
    return result.loc[:, preferred + extra]
