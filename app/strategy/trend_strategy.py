"""EMA + RSI trend rules that emit BUY / SELL / HOLD per candle.

Look-ahead bias is avoided because:

* Indicators are computed with left-aligned EWM windows (see
  ``app.indicators.indicators``).
* Each row's signal uses that row's close, EMA, and RSI only.
* We never call ``shift(-1)`` or look at ``iloc[i + 1]`` when labeling row *i*.

This class does **not** execute trades or calculate profit.
"""

from __future__ import annotations

import pandas as pd

from app.indicators.indicators import add_indicators
from app.strategy.base import BaseStrategy, Signal, StrategyConfig


class EMA_RSI_TrendStrategy(BaseStrategy):
    """Simple trend-following labels from fast/slow EMA and RSI.

    BUY when all of these are true on the **current** candle:

    * fast EMA > slow EMA
    * close > fast EMA
    * RSI is inside ``[buy_rsi_min, buy_rsi_max]`` (default 50–70)

    SELL when all of these are true on the **current** candle:

    * fast EMA < slow EMA
    * close < fast EMA
    * RSI is inside ``[sell_rsi_min, sell_rsi_max]`` (default 30–50)

    Otherwise HOLD, including rows where EMA/RSI are still NaN (not
    enough history yet).
    """

    def generate_signals(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Add indicator columns and a ``signal`` column; do not trade."""
        config: StrategyConfig = self.config
        result = add_indicators(
            dataframe,
            ema_fast_period=config.ema_fast_period,
            ema_slow_period=config.ema_slow_period,
            rsi_period=config.rsi_period,
        )

        ema_fast = result[f"ema_{config.ema_fast_period}"]
        ema_slow = result[f"ema_{config.ema_slow_period}"]
        rsi = result[f"rsi_{config.rsi_period}"]
        close = result["close"].astype(float)

        buy = (
            (ema_fast > ema_slow)
            & (close > ema_fast)
            & rsi.between(config.buy_rsi_min, config.buy_rsi_max, inclusive="both")
        )
        sell = (
            (ema_fast < ema_slow)
            & (close < ema_fast)
            & rsi.between(config.sell_rsi_min, config.sell_rsi_max, inclusive="both")
        )

        # NaN comparisons are False, so incomplete indicator rows become HOLD.
        result["signal"] = Signal.HOLD.value
        result.loc[buy, "signal"] = Signal.BUY.value
        result.loc[sell, "signal"] = Signal.SELL.value
        return result
