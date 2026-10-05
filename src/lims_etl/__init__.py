"""lims-etl: tidy normalization for messy lab data exports.

Lab instruments and LIMS export CSVs that are not analysis-ready:
preamble metadata lines, units embedded in headers, 96-well plate
layouts, transposed layouts, censored values (ND, BQL, <0.01).

This package gives you small composable building blocks to turn those
exports into tidy, analysis-ready tables, plus a CLI for CI/script use.

stdlib-only runtime (no third-party dependencies).
"""

from .io import find_header_row, load_table, normalize_headers, read_csv_rows
from .plates import PlateLayout, parse_plate, well_id
from .tidy import coerce_column, melt_wide_to_long
from .units import CONVERSION_FACTORS, convert_units, split_header_units

__version__ = "0.1.0"

__all__ = [
    "CONVERSION_FACTORS",
    "PlateLayout",
    "coerce_column",
    "convert_units",
    "find_header_row",
    "load_table",
    "melt_wide_to_long",
    "normalize_headers",
    "parse_plate",
    "read_csv_rows",
    "split_header_units",
    "well_id",
]
