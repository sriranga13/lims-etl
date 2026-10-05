from lims_etl.tidy import (
    coerce_column,
    drop_empty_columns,
    is_censored,
    melt_wide_to_long,
)


def test_is_censored():
    assert is_censored("ND")
    assert is_censored("BQL")
    assert is_censored("<0.01")
    assert is_censored(">TNTC")
    assert is_censored("")
    assert not is_censored("12.5")
    assert not is_censored("<hello")


def test_coerce_column_float():
    assert coerce_column(["1.5", "2", "ND"]) == [1.5, 2.0, "ND"]


def test_coerce_column_int():
    assert coerce_column(["1.0", "2.9"], target="int") == [1, 2]


def test_coerce_column_censored_to_none():
    assert coerce_column(["<0.01"], keep_censored=False) == [None]


def test_coerce_column_bad_value_to_none():
    assert coerce_column(["abc"]) == [None]


def test_coerce_column_commas():
    assert coerce_column(["1,234.5"]) == [1234.5]


def test_melt_wide_to_long():
    rows = [
        {"sample": "S1", "day1": "10", "day2": "20"},
        {"sample": "S2", "day1": "30", "day2": ""},
    ]
    out = melt_wide_to_long(rows, id_columns=["sample"])
    assert len(out) == 3
    assert out[0] == {"sample": "S1", "variable": "day1", "value": "10"}
    assert out[-1]["sample"] == "S2"


def test_melt_custom_names():
    rows = [{"id": "x", "t0": "1"}]
    out = melt_wide_to_long(rows, ["id"], value_name="conc", variable_name="timepoint")
    assert out[0] == {"id": "x", "timepoint": "t0", "conc": "1"}


def test_drop_empty_columns():
    rows = [{"a": "1", "b": "", "c": "x"}, {"a": "2", "b": "", "c": "y"}]
    headers, pruned = drop_empty_columns(rows)
    assert headers == ["a", "c"]
    assert pruned[0] == {"a": "1", "c": "x"}
