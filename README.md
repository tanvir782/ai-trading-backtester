# AI Trading Backtester (Educational)

This is a **historical backtesting and simulation** project for learning.

It does **not** connect to any broker (including Exness or MetaTrader), does **not** place demo or real trades, and does **not** use real money. All market rows in this repository are **synthetic / fictional**. They are only for testing the data pipeline.

## What Phase 1 means

Phase 1 is the **foundation only**:

- Project folders and Python package layout
- A CSV loader for OHLCV data (open, high, low, close, volume)
- A data validator
- A small synthetic sample file
- Automated tests with pytest

Stage 2 (indicators and signal-only strategy) is documented further below. A backtesting engine is still **not** part of this project yet.

## Current architecture

1. You point the loader at a CSV file.
2. The loader reads the file, converts `timestamp` to a pandas datetime, and sorts rows oldest to newest.
3. The validator checks that the DataFrame is usable (columns, timestamps, numbers, no empties/duplicates/missing values).
4. Indicators add EMA and RSI columns using **only past and current** closes.
5. The strategy writes a `signal` column: `BUY`, `SELL`, or `HOLD`. It does **not** place trades.

```text
CSV
  -->  load_ohlcv_csv()
  -->  validate_ohlcv()
  -->  add_indicators()
  -->  EMA_RSI_TrendStrategy.generate_signals()
  -->  BUY / SELL / HOLD (labels only)
```

There is no broker connection, no order execution, no PnL engine, no database, no web UI, and no machine learning.

## Folder structure

```text
ai-trading-backtester/
├── app/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py      # paths and required column names
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py        # read and sort OHLCV CSV files
│   │   └── validator.py     # quality checks on the DataFrame
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── indicators.py    # EMA and RSI (no look-ahead)
│   └── strategy/
│       ├── __init__.py
│       ├── base.py          # Signal enum and StrategyConfig
│       └── trend_strategy.py
├── data/
│   └── sample/
│       └── sample_ohlcv.csv # fictional OHLCV rows for tests
├── tests/
│   ├── test_loader.py
│   ├── test_validator.py
│   ├── test_indicators.py
│   └── test_strategy.py
├── README.md
├── requirements.txt
└── .gitignore
```

## Create and activate the virtual environment

This project already includes a `.venv` folder on this machine. If you need to create one yourself (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

You should see `(.venv)` at the start of your prompt. Always use this environment so packages are not installed into your global Python.

## Install dependencies

With the virtual environment activated, from the project root:

```powershell
python -m pip install -r requirements.txt
```

Current stages only need:

- `pandas` — tables, EMA, and RSI
- `pytest` — run the tests

## Run the tests

From the project root, with `.venv` activated:

```powershell
python -m pytest -v
```

You should see Stage 1 tests (loader/validator) and Stage 2 tests (indicators and strategy signals).

## How the CSV data pipeline works

### Expected columns

Every OHLCV file must have:

| Column      | Meaning                                      |
| ----------- | -------------------------------------------- |
| `timestamp` | Date and time of the bar                     |
| `open`      | Opening price                                |
| `high`      | Highest price                                |
| `low`       | Lowest price                                 |
| `close`     | Closing price                                |
| `volume`    | Traded volume (synthetic in the sample file) |

### Loader (`app/data/loader.py`)

`load_ohlcv_csv(path)`:

1. Checks that the path exists and is a file
2. Reads the CSV with pandas
3. Converts `timestamp` to datetime (invalid values become `NaT` so the validator can report them)
4. Sorts by timestamp
5. Returns a `DataFrame`

If the file cannot be read, it raises `DataLoadError` with a short explanation.

### Validator (`app/data/validator.py`)

`validate_ohlcv(dataframe)` checks:

1. Required columns exist
2. Timestamps are valid
3. Data is sorted oldest to newest
4. Timestamps are unique
5. There are no missing values
6. OHLCV columns are numeric
7. The DataFrame is not empty

If something is wrong, it raises `DataValidationError` listing every problem. `collect_validation_errors(dataframe)` returns the same issues as a list of strings if you want to inspect them without raising.

### Sample data

`data/sample/sample_ohlcv.csv` is **made-up**. Use it to learn the pipeline, not as real market history.

### Tiny usage example (Stage 1 + Stage 2)

The bundled sample CSV has only 8 rows, so EMA 20 / EMA 50 / RSI 14 will still be empty (`NaN`) there. That is expected: those windows need more history. Use a longer synthetic series when you want actual indicator values.

```python
from app.config.settings import SAMPLE_CSV
from app.data.loader import load_ohlcv_csv
from app.data.validator import validate_ohlcv
from app.strategy.trend_strategy import EMA_RSI_TrendStrategy

df = load_ohlcv_csv(SAMPLE_CSV)
validate_ohlcv(df)

strategy = EMA_RSI_TrendStrategy()  # default 20 / 50 / 14
labeled = strategy.generate_signals(df)
print(labeled[["timestamp", "close", "ema_20", "ema_50", "rsi_14", "signal"]].head())
```

## Stage 2 — indicators and signals

Stage 2 still **does not trade**. It only adds numbers (indicators) and labels (`BUY` / `SELL` / `HOLD`) to historical candles.

### What EMA is

An **exponential moving average (EMA)** is a smoothed version of closing price. Recent closes count more than older closes.

- **EMA 20** (`ema_20`) uses a 20-candle window (faster — it turns sooner).
- **EMA 50** (`ema_50`) uses a 50-candle window (slower — it represents a longer trend).

This project uses the usual trading recurrence `multiplier = 2 / (period + 1)` via pandas `ewm(span=period, adjust=False)`. The first `period - 1` rows are `NaN` because there is not enough history yet.

### What RSI is

The **Relative Strength Index (RSI)** is a number from 0 to 100 that summarizes recent up-moves versus down-moves. This project uses **Wilder RSI with period 14** (`rsi_14`):

1. Compare each close to the previous close (never a future close).
2. Separate those changes into gains and losses.
3. Smooth them with Wilder's average (`alpha = 1 / 14`).
4. Convert the gain/loss ratio into 0–100.

Rough intuition (not a guarantee): higher RSI means recent candles have been stronger on the upside; lower RSI means the opposite. Values near 50 are more neutral.

### Why these indicators are used

Together they describe a **simple trend-plus-momentum filter**:

- Fast EMA vs slow EMA: is the short-term average above or below the longer-term average?
- Close vs fast EMA: is price still on the same side of that short-term average?
- RSI band: is momentum in a middle range rather than an extreme?

This is a teaching rule, not a claim that it is profitable.

### Exact BUY rule

On the **current** candle, all of the following must be true:

1. `EMA20 > EMA50`
2. `close > EMA20`
3. RSI is between **50 and 70** (inclusive), using the configured `buy_rsi_min` / `buy_rsi_max`

### Exact SELL rule

On the **current** candle, all of the following must be true:

1. `EMA20 < EMA50`
2. `close < EMA20`
3. RSI is between **30 and 50** (inclusive), using the configured `sell_rsi_min` / `sell_rsi_max`

### What HOLD means

`HOLD` means “do not label this candle as BUY or SELL.” That includes:

- The BUY and SELL rules are both false
- Indicators are still `NaN` (not enough candles yet)
- Fast and slow EMA are equal

HOLD is **not** an order and **not** a “stay in a position” instruction. There is no position tracking in Stage 2.

### How the strategy generates signals

`EMA_RSI_TrendStrategy.generate_signals()`:

1. Copies your OHLCV table
2. Calls `add_indicators()` with the strategy’s periods
3. Applies the BUY / SELL rules row by row (vectorized; each row uses that row only)
4. Writes a `signal` column whose values are the strings `BUY`, `SELL`, or `HOLD`

You can change defaults with `StrategyConfig` (`ema_fast_period`, `ema_slow_period`, `rsi_period`, and the four RSI band numbers). Column names follow the periods, for example `ema_20`, `ema_50`, `rsi_14`.

### Why look-ahead bias is dangerous

**Look-ahead bias** (using the future while pretending you are at time *t*) makes a research project look smarter than it could have been in real time. Examples of cheating:

- Computing an average that includes tomorrow’s close
- Labeling today using tomorrow’s RSI
- Centering a rolling window so “today” secretly includes later candles

If you do that, backtests later will be **too optimistic** and useless as practice. This codebase keeps windows left-aligned, never uses `shift(-1)` for signals, and has tests that compare a full series to a truncated prefix and that change only the last candle.
