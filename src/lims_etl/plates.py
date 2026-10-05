"""Plate-reader layout parsing.

Plate readers export measurements in a plate grid layout:

    ,1,2,3,...,12
    A,0.11,0.12,...
    B,...

This module parses such grids (96-well: rows A-H x cols 1-12, 384-well:
rows A-P x cols 1-24) into tidy records of (well, row, col, value) that
join cleanly against sample metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PlateLayout:
    rows: int  # number of lettered rows, e.g. 8 for 96-well
    cols: int  # number of numbered columns, e.g. 12 for 96-well

    @property
    def name(self) -> str:
        if (self.rows, self.cols) == (8, 12):
            return "96-well"
        if (self.rows, self.cols) == (16, 24):
            return "384-well"
        return f"{self.rows}x{self.cols}"

    @property
    def row_labels(self) -> list[str]:
        return [chr(ord("A") + i) for i in range(self.rows)]

    @property
    def col_labels(self) -> list[str]:
        return [str(i + 1) for i in range(self.cols)]


PLATE_96 = PlateLayout(rows=8, cols=12)
PLATE_384 = PlateLayout(rows=16, cols=24)


def well_id(row_label: str, col: int | str) -> str:
    """Canonical well id, e.g. well_id('A', 1) -> 'A1'."""
    return f"{row_label.upper()}{int(col)}"


_WELL_RE = re.compile(r"^([A-P])(\d{1,2})$")


def split_well(well: str) -> tuple[str, int]:
    """split_well('B12') -> ('B', 12). Raises ValueError on bad input."""
    m = _WELL_RE.match(well.strip().upper())
    if not m:
        raise ValueError(f"not a well id: {well!r}")
    return m.group(1), int(m.group(2))


def parse_plate(
    grid: Sequence[Sequence[str]],
    layout: PlateLayout = PLATE_96,
    skip_header_row: bool = True,
) -> list[dict[str, str]]:
    """Parse a plate grid into tidy records.

    ``grid`` is a list of rows; each row is a list of cells where the first
    cell is the row label (A..) and the remaining cells are the column
    values. If ``skip_header_row`` is True and the first row starts with a
    blank/non-letter cell, it is treated as a column-number header.

    Returns records: {"well", "row", "col", "value"} as strings, in
    row-major (A1..H12) order. Empty cells are skipped.
    """
    rows = [list(r) for r in grid]
    if skip_header_row and rows:
        first = (rows[0][0] if rows[0] else "").strip().upper()
        if not (len(first) == 1 and first.isalpha()):
            rows = rows[1:]
    row_labels = layout.row_labels
    records: list[dict[str, str]] = []
    for r_idx, row in enumerate(rows):
        if r_idx >= layout.rows:
            break
        row_label = row_labels[r_idx]
        for c_idx in range(min(layout.cols, len(row) - 1)):
            value = row[c_idx + 1].strip()
            if value == "":
                continue
            col = c_idx + 1
            records.append(
                {
                    "well": well_id(row_label, col),
                    "row": row_label,
                    "col": str(col),
                    "value": value,
                }
            )
    return records


def attach_metadata(
    records: Iterable[dict[str, str]],
    metadata: Sequence[dict[str, str]],
    on: str = "well",
) -> list[dict[str, str]]:
    """Left-join plate records to sample metadata (e.g. well -> sample_id).

    ``metadata`` rows must carry the join key in column ``on``.
    """
    lookup = {str(m.get(on, "")).strip().upper(): m for m in metadata}
    out: list[dict[str, str]] = []
    for rec in records:
        key = str(rec.get(on, "")).strip().upper()
        merged = dict(rec)
        meta = lookup.get(key)
        if meta:
            for k, v in meta.items():
                if k != on:
                    merged.setdefault(k, v)
        out.append(merged)
    return out
