import pytest

from lims_etl.units import (
    can_convert,
    convert,
    convert_units,
    normalize_unit,
    split_header_units,
    split_value_unit,
)


def test_split_header_units_parens():
    assert split_header_units("Concentration (mg/mL)") == ("Concentration", "mg/mL")


def test_split_header_units_brackets():
    assert split_header_units("Volume [uL]") == ("Volume", "uL")


def test_split_header_units_no_unit():
    assert split_header_units("sample_id") == ("sample_id", None)


def test_normalize_unit_micro_variants():
    assert normalize_unit("µg/mL") == "ug/ml"
    assert normalize_unit("UG/ML") == "ug/ml"
    assert normalize_unit(None) is None


def test_convert_mgml_to_gl():
    assert convert(2.5, "mg/mL", "g/L") == pytest.approx(2.5)


def test_convert_ugml_to_mgml():
    assert convert(1000, "ug/ml", "mg/ml") == pytest.approx(1.0)


def test_convert_min_to_s():
    assert convert(2, "min", "s") == pytest.approx(120.0)


def test_convert_unknown_unit_raises():
    with pytest.raises(ValueError):
        convert(1, "furlongs", "ml")


def test_convert_incompatible_raises():
    with pytest.raises(ValueError):
        convert(1, "mg", "ml")


def test_can_convert():
    assert can_convert("ng/ml", "ug/ml")
    assert not can_convert("mg", "ml")
    assert not can_convert(None, "ml")


def test_split_value_unit():
    assert split_value_unit("2.5 mg/mL") == (2.5, "mg/mL")
    assert split_value_unit("ND") == (None, None)
    assert split_value_unit("100") == (100.0, None)


def test_convert_units_with_unit_column():
    rows = [{"value": "1000", "unit": "ug/ml"}, {"value": "2", "unit": "mg/ml"}]
    out = convert_units(rows, "value", "mg/ml", unit_column="unit")
    assert out[0]["value"] == pytest.approx(1.0)
    assert out[1]["value"] == pytest.approx(2.0)


def test_convert_units_inline_unit():
    rows = [{"value": "2500 ug/ml"}]
    out = convert_units(rows, "value", "mg/ml")
    assert out[0]["value"] == pytest.approx(2.5)


def test_convert_units_passthrough_unparseable():
    rows = [{"value": "ND", "unit": "mg/ml"}]
    out = convert_units(rows, "value", "g/L", unit_column="unit")
    assert out[0]["value"] == "ND"
