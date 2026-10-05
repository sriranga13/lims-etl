import os
import tempfile

import pytest

from lims_etl.io import (
    LoadedTable,
    find_header_row,
    load_table,
    normalize_headers,
)

MESSY = (
    "Instrument: PlateReader X\n"
    "Run ID: 2026-10-05_001\n"
    "Operator: sri\n"
    "sample_id, result (mg/L), flag\n"
    "S1, 12.5, pass\n"
    "S2, 13.1, pass\n"
    "\n"
)


def _tmp(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as fh:
        fh.write(content)
    return path


def test_find_header_row_skips_preamble():
    rows = [r.split(",") for r in MESSY.splitlines()]
    assert find_header_row(rows) == 3


def test_find_header_row_with_hint():
    rows = [["junk"], ["sample_id", "x"]]
    assert find_header_row(rows, candidates=["sample_id"]) == 1


def test_find_header_row_empty_raises():
    with pytest.raises(ValueError):
        find_header_row([])


def test_load_table_parses_and_strips():
    path = _tmp(MESSY)
    try:
        table = load_table(path)
        assert isinstance(table, LoadedTable)
        assert table.skipped_lines == 3
        assert table.headers == ["sample_id", "result (mg/L)", "flag"]
        assert len(table.rows) == 2
        assert table.rows[0]["sample_id"] == "S1"
        assert table.rows[1]["result (mg/L)"] == "13.1"
    finally:
        os.unlink(path)


def test_load_table_pads_short_rows():
    path = _tmp("a,b,c\n1,2\n")
    try:
        table = load_table(path)
        assert table.rows[0] == {"a": "1", "b": "2", "c": ""}
    finally:
        os.unlink(path)


def test_normalize_headers():
    assert normalize_headers(["Sample ID", "Concentration (mg/mL)", "Sample ID", ""]) == [
        "sample_id",
        "concentration_mgml",
        "sample_id_2",
        "column",
    ]


def test_load_table_whitespace_stripped():
    path = _tmp(" a , b \n 1 , 2 \n")
    try:
        table = load_table(path)
        assert table.headers == ["a", "b"]
        assert table.rows[0] == {"a": "1", "b": "2"}
    finally:
        os.unlink(path)
