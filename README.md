# lims-etl

Normalize messy lab CSV exports into tidy, analysis-ready tables. stdlib-only, no third-party dependencies.

Lab instruments and LIMS exports are never analysis-ready: preamble metadata lines, units embedded in headers (`result (mg/L)`), 96/384-well plate grids, wide transposed layouts, and censored values (`ND`, `BQL`, `<0.01`). `lims-etl` gives you small composable blocks for each of these, plus a CLI for scripts and CI.

## Install

```bash
pip install lims-etl
```

Or from source:

```bash
pip install -e .
```

## Library

```python
from lims_etl import load_table, parse_plate, melt_wide_to_long, convert_units

# 1. Skip instrument preamble, find the real header
table = load_table("examples/instrument_export.csv")
print(table.skipped_lines, table.headers)

# 2. Parse a 96-well plate grid into tidy (well, row, col, value) records
grid = ...  # list of CSV rows
records = parse_plate(grid)  # [{"well": "A1", "row": "A", "col": "1", "value": "0.11"}, ...]

# 3. Melt wide time-series columns into long form
long = melt_wide_to_long(table.rows, id_columns=["sample_id"])

# 4. Convert mg/L -> g/L, ug/ml -> mg/ml, etc.
rows = convert_units(table.rows, "result", "g/L", unit_column="unit")
```

## CLI

```bash
# Load a messy export (preamble skipped), normalize headers, split units
lims-etl load examples/instrument_export.csv --normalize --split-units -o tidy.csv

# Parse a 96-well plate grid, join sample metadata
lims-etl plate examples/plate_reader.csv --metadata examples/sample_metadata.csv -o wells.csv

# Melt wide columns into long form
lims-etl melt examples/wide_measurements.csv --id sample_id -o long.csv

# Convert a unit column (ug/ml -> mg/ml)
lims-etl units readings.csv value --to mg/ml --unit-column unit -o converted.csv
```

Output can be CSV (default), JSON (`-o out.json`), SQLite (`-o out.db`), or stdout (`-o -`).

## What's inside

| Module | Does |
|---|---|
| `io` | Find the real header row under instrument preambles; clean CSV loading |
| `units` | Split `Name (unit)` headers; convert mg/mL, ug/mL, uL, mmol, min, ... |
| `plates` | Parse 96/384-well grids into tidy well records; join sample metadata |
| `tidy` | Coerce dtypes (censored-value aware), wide-to-long melts, drop empty columns |
| `sinks` | Write CSV / JSON / SQLite |
| `cli` | `load`, `plate`, `melt`, `units` subcommands |

Censored tokens (`ND`, `BQL`, `TNTC`, `<0.01`, `>TNTC`, ...) are never silently coerced to numbers; coercion preserves them as strings or maps them to `None` on request.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

## License

MIT. See [LICENSE](LICENSE).
