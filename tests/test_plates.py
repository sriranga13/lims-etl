import pytest

from lims_etl.plates import (
    PLATE_96,
    PLATE_384,
    PlateLayout,
    attach_metadata,
    parse_plate,
    split_well,
    well_id,
)

GRID_96 = [
    ["", "1", "2", "3"],
    ["A", "0.11", "0.12", "0.13"],
    ["B", "0.21", "", "0.23"],
    ["C", "0.31", "0.32", "0.33"],
]


def test_well_id():
    assert well_id("A", 1) == "A1"
    assert well_id("h", 12) == "H12"


def test_split_well():
    assert split_well("B12") == ("B", 12)
    with pytest.raises(ValueError):
        split_well("not-a-well")


def test_parse_plate_basic():
    recs = parse_plate(GRID_96)
    by_well = {r["well"]: r["value"] for r in recs}
    assert by_well["A1"] == "0.11"
    assert by_well["B3"] == "0.23"
    assert by_well["C2"] == "0.32"
    assert "B2" not in by_well  # empty cell skipped


def test_parse_plate_record_shape():
    recs = parse_plate(GRID_96)
    assert recs[0] == {"well": "A1", "row": "A", "col": "1", "value": "0.11"}


def test_parse_plate_no_header_row():
    grid = [["A", "0.1"], ["B", "0.2"]]
    recs = parse_plate(grid, layout=PlateLayout(2, 1), skip_header_row=True)
    assert [r["well"] for r in recs] == ["A1", "B1"]


def test_parse_plate_384_layout():
    assert PLATE_384.row_labels[15] == "P"
    assert PLATE_384.col_labels[-1] == "24"
    assert PLATE_384.name == "384-well"
    assert PLATE_96.name == "96-well"


def test_parse_plate_truncates_to_layout():
    grid = [["A", "1"], ["B", "2"], ["C", "3"]]
    recs = parse_plate(grid, layout=PlateLayout(2, 1))
    assert len(recs) == 2


def test_attach_metadata():
    recs = [{"well": "A1", "row": "A", "col": "1", "value": "0.11"}]
    meta = [{"well": "A1", "sample_id": "S-100"}]
    out = attach_metadata(recs, meta)
    assert out[0]["sample_id"] == "S-100"


def test_attach_metadata_missing_key_no_crash():
    recs = [{"well": "A9", "value": "0.1"}]
    out = attach_metadata(recs, [{"well": "A1", "sample_id": "S"}])
    assert out[0]["value"] == "0.1"
