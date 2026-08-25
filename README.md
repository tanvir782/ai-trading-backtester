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

Later phases can add more features (indicators, strategy simulation, and eventually AI assistance). Those are **not** part of this stage.

## Current architecture

The flow is intentionally small:

1. You point the loader at a CSV file.
2. The loader reads the file, converts `timestamp` to a pandas datetime, and sorts rows oldest to newest.
3. The validator checks that the DataFrame is usable (columns, timestamps, numbers, no empties/duplicates/missing values).

```text
CSV file  -->  load_ohlcv_csv()  -->  DataFrame  -->  validate_ohlcv()
```

There is no trading engine, no database, no web UI, and no machine learning in Phase 1.

## Folder structure

```text
ai-trading-backtester/
├── app/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py      # paths and required column names
│   └── data/
│       ├── __init__.py
│       ├── loader.py        # read and sort OHLCV CSV files
│       └── validator.py     # quality checks on the DataFrame
├── data/
│   └── sample/
│       └── sample_ohlcv.csv # fictional OHLCV rows for tests
├── tests/
│   ├── test_loader.py
│   └── test_validator.py
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

Phase 1 only needs:

- `pandas` — load and work with CSV tables
- `pytest` — run the tests

## Run the tests

From the project root, with `.venv` activated:

```powershell
python -m pytest -v
```

You should see tests for valid loading plus detection of missing columns, invalid timestamps, duplicate timestamps, missing values, and invalid numbers.

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

### Tiny usage example

```python
from app.config.settings import SAMPLE_CSV
from app.data.loader import load_ohlcv_csv
from app.data.validator import validate_ohlcv

df = load_ohlcv_csv(SAMPLE_CSV)
validate_ohlcv(df)
print(df.head())
```
