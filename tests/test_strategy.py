"""Tests for EMA_RSI_TrendStrategy signal generation."""

import pandas as pd
import pytest

from app.strategy.base import Signal, StrategyConfig
from app.strategy.trend_strategy import EMA_RSI_TrendStrategy


def _ohlcv_from_closes(closes: list[float]) -> pd.DataFrame:
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


def test_default_strategy_parameters() -> None:
    strategy = EMA_RSI_TrendStrategy()
    config = strategy.config

    assert config.ema_fast_period == 20
    assert config.ema_slow_period == 50
    assert config.rsi_period == 14
    assert config.buy_rsi_min == 50.0
    assert config.buy_rsi_max == 70.0
    assert config.sell_rsi_min == 30.0
    assert config.sell_rsi_max == 50.0


def test_custom_strategy_parameters_change_indicator_columns() -> None:
    config = StrategyConfig(ema_fast_period=3, ema_slow_period=5, rsi_period=4)
    strategy = EMA_RSI_TrendStrategy(config)
    result = strategy.generate_signals(_ohlcv_from_closes([10.0, 11.0, 12.0, 13.0, 14.0, 15.0]))

    assert "ema_3" in result.columns
    assert "ema_5" in result.columns
    assert "rsi_4" in result.columns
    assert "ema_20" not in result.columns


def test_invalid_parameter_ranges_are_rejected() -> None:
    with pytest.raises(ValueError, match="buy_rsi_min"):
        EMA_RSI_TrendStrategy(StrategyConfig(buy_rsi_min=80, buy_rsi_max=50))


def test_buy_signal_generation() -> None:
    """A mild, persistent uptrend should produce at least one BUY."""
    closes = [100.0 + i * 0.15 for i in range(40)]
    config = StrategyConfig(
        ema_fast_period=3,
        ema_slow_period=8,
        rsi_period=5,
        buy_rsi_min=50.0,
        buy_rsi_max=100.0,
        sell_rsi_min=0.0,
        sell_rsi_max=20.0,
    )
    result = EMA_RSI_TrendStrategy(config).generate_signals(_ohlcv_from_closes(closes))
    buy_rows = result[result["signal"] == Signal.BUY.value]

    assert not buy_rows.empty
    last_buy = buy_rows.iloc[-1]
    assert last_buy["ema_3"] > last_buy["ema_8"]
    assert last_buy["close"] > last_buy["ema_3"]
    assert 50.0 <= last_buy["rsi_5"] <= 100.0


def test_sell_signal_generation() -> None:
    """A mild, persistent downtrend should produce at least one SELL."""
    closes = [100.0 - i * 0.15 for i in range(40)]
    config = StrategyConfig(
        ema_fast_period=3,
        ema_slow_period=8,
        rsi_period=5,
        buy_rsi_min=80.0,
        buy_rsi_max=100.0,
        sell_rsi_min=0.0,
        sell_rsi_max=50.0,
    )
    result = EMA_RSI_TrendStrategy(config).generate_signals(_ohlcv_from_closes(closes))
    sell_rows = result[result["signal"] == Signal.SELL.value]

    assert not sell_rows.empty
    last_sell = sell_rows.iloc[-1]
    assert last_sell["ema_3"] < last_sell["ema_8"]
    assert last_sell["close"] < last_sell["ema_3"]
    assert 0.0 <= last_sell["rsi_5"] <= 50.0


def test_hold_when_rules_are_not_met() -> None:
    """Flat prices do not show a trend, so every row should be HOLD."""
    closes = [100.0] * 30
    config = StrategyConfig(ema_fast_period=3, ema_slow_period=8, rsi_period=5)
    result = EMA_RSI_TrendStrategy(config).generate_signals(_ohlcv_from_closes(closes))

    assert set(result["signal"].unique()) == {Signal.HOLD.value}


def test_hold_while_indicators_are_warming_up() -> None:
    """The first slow-EMA-period rows cannot have a complete slow EMA."""
    closes = [100.0 + i for i in range(12)]
    config = StrategyConfig(ema_fast_period=3, ema_slow_period=8, rsi_period=5)
    result = EMA_RSI_TrendStrategy(config).generate_signals(_ohlcv_from_closes(closes))

    warmup = result.iloc[:7]
    assert (warmup["signal"] == Signal.HOLD.value).all()
    assert warmup["ema_8"].isna().all()


def test_rsi_band_can_block_an_otherwise_valid_buy() -> None:
    closes = [100.0 + i * 0.15 for i in range(40)]
    open_band = StrategyConfig(
        ema_fast_period=3,
        ema_slow_period=8,
        rsi_period=5,
        buy_rsi_min=0.0,
        buy_rsi_max=100.0,
    )
    closed_band = StrategyConfig(
        ema_fast_period=3,
        ema_slow_period=8,
        rsi_period=5,
        buy_rsi_min=0.0,
        buy_rsi_max=1.0,
    )
    with_buys = EMA_RSI_TrendStrategy(open_band).generate_signals(_ohlcv_from_closes(closes))
    blocked = EMA_RSI_TrendStrategy(closed_band).generate_signals(_ohlcv_from_closes(closes))

    assert Signal.BUY.value in set(with_buys["signal"])
    assert Signal.BUY.value not in set(blocked["signal"])


def test_every_row_has_exactly_one_signal() -> None:
    closes = [100.0 + ((-1) ** i) * i * 0.2 for i in range(25)]
    result = EMA_RSI_TrendStrategy(
        StrategyConfig(ema_fast_period=3, ema_slow_period=8, rsi_period=5)
    ).generate_signals(_ohlcv_from_closes(closes))

    assert len(result) == 25
    assert result["signal"].isin([s.value for s in Signal]).all()


def test_strategy_does_not_use_future_candles() -> None:
    """Changing only the last close must not change earlier signals."""
    closes = [100.0 + (i % 5) - 2.0 + i * 0.08 for i in range(50)]
    config = StrategyConfig(ema_fast_period=3, ema_slow_period=8, rsi_period=5)
    strategy = EMA_RSI_TrendStrategy(config)

    original = strategy.generate_signals(_ohlcv_from_closes(closes))
    mutated_closes = list(closes)
    mutated_closes[-1] = 10_000.0
    mutated = strategy.generate_signals(_ohlcv_from_closes(mutated_closes))

    compared_columns = ["ema_3", "ema_8", "rsi_5", "signal"]
    pd.testing.assert_frame_equal(
        original[compared_columns].iloc[:-1].reset_index(drop=True),
        mutated[compared_columns].iloc[:-1].reset_index(drop=True),
    )
