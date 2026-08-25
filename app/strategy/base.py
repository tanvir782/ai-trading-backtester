"""Shared signal labels, strategy settings, and a tiny strategy base class.

Strategies in this project only **label** candles. They never place orders,
compute profit, or talk to a broker.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Signal(str, Enum):
    """Allowed values written to the ``signal`` column."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class StrategyConfig:
    """Tunable indicator and RSI-band settings.

    Defaults match the Stage 2 EMA/RSI trend rules.
    """

    ema_fast_period: int = 20
    ema_slow_period: int = 50
    rsi_period: int = 14
    buy_rsi_min: float = 50.0
    buy_rsi_max: float = 70.0
    sell_rsi_min: float = 30.0
    sell_rsi_max: float = 50.0

    def validate(self) -> None:
        """Raise ValueError if periods or RSI bands are not usable."""
        if self.ema_fast_period < 1 or self.ema_slow_period < 1 or self.rsi_period < 1:
            raise ValueError("Indicator periods must be at least 1.")
        if self.buy_rsi_min > self.buy_rsi_max:
            raise ValueError("buy_rsi_min cannot be greater than buy_rsi_max.")
        if self.sell_rsi_min > self.sell_rsi_max:
            raise ValueError("sell_rsi_min cannot be greater than sell_rsi_max.")


class BaseStrategy(ABC):
    """Map a historical OHLCV table to a ``signal`` column (BUY / SELL / HOLD)."""

    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config if config is not None else StrategyConfig()
        self.config.validate()

    @abstractmethod
    def generate_signals(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of ``dataframe`` with indicators and a ``signal`` column.

        Implementations must use only information available at each row
        (no future candles, prices, or indicator values).
        """
