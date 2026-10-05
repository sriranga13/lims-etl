"""Unit handling for lab measurement headers and values.

Lab exports embed units in headers ("Concentration (mg/mL)") or cells
("2.5 mg/mL"). This module splits headers into (name, unit) and converts
values between common concentration/volume/mass units.
"""

from __future__ import annotations

import re
from typing import Sequence

# conversion factors to the canonical unit within each family
CONVERSION_FACTORS: dict[str, tuple[str, float]] = {
    # mass per volume (canonical: g/L)
    "g/l": ("g/l", 1.0),
    "mg/ml": ("g/l", 1.0),
    "ug/ml": ("g/l", 1e-3),
    "ng/ml": ("g/l", 1e-6),
    "mg/l": ("g/l", 1e-3),
    "ug/l": ("g/l", 1e-6),
    "%": ("g/l", 10.0),  # % w/v -> g/L (density ~1 g/mL)
    # volume (canonical: ml)
    "ml": ("ml", 1.0),
    "ul": ("ml", 1e-3),
    "l": ("ml", 1e3),
    # mass (canonical: mg)
    "mg": ("mg", 1.0),
    "ug": ("mg", 1e-3),
    "ng": ("mg", 1e-6),
    "g": ("mg", 1e3),
    # amount of substance (canonical: umol)
    "mmol": ("umol", 1e3),
    "umol": ("umol", 1.0),
    "nmol": ("umol", 1e-3),
    # temperature / time / others have no conversions here
    "c": ("c", 1.0),
    "s": ("s", 1.0),
    "min": ("s", 60.0),
    "h": ("s", 3600.0),
}

_HEADER_UNIT_RE = re.compile(r"^(?P<name>.+?)\s*[\(\[](?P<unit>[^()\[\]]+)[\)\]]\s*$")
_VALUE_UNIT_RE = re.compile(r"^(?P<value>[-+.\d]+(?:[eE][-+]?\d+)?)\s*(?P<unit>[a-zA-Zµ/%]+)?$")


def split_header_units(header: str) -> tuple[str, str | None]:
    """Split 'Concentration (mg/mL)' -> ('Concentration', 'mg/mL').

    Returns (stripped_name, unit or None). Case-insensitive 'µ' is left as-is.
    """
    m = _HEADER_UNIT_RE.match(header.strip())
    if not m:
        return header.strip(), None
    return m.group("name").strip(), m.group("unit").strip()


def normalize_unit(unit: str | None) -> str | None:
    """Lowercase a unit and normalize micro variants (µ, μg, ug) to 'u' form."""
    if unit is None:
        return None
    u = unit.strip().lower().replace("µ", "u")
    return u or None


def can_convert(from_unit: str, to_unit: str) -> bool:
    """True when both units share a conversion family."""
    f, t = normalize_unit(from_unit), normalize_unit(to_unit)
    if f is None or t is None:
        return False
    ff, tf = CONVERSION_FACTORS.get(f), CONVERSION_FACTORS.get(t)
    return ff is not None and tf is not None and ff[0] == tf[0]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert ``value`` from one unit to another in the same family.

    Raises:
        ValueError: for unknown or incompatible units.
    """
    f, t = normalize_unit(from_unit), normalize_unit(to_unit)
    ff = CONVERSION_FACTORS.get(f) if f else None
    tf = CONVERSION_FACTORS.get(t) if t else None
    if ff is None:
        raise ValueError(f"unknown unit: {from_unit!r}")
    if tf is None:
        raise ValueError(f"unknown unit: {to_unit!r}")
    if ff[0] != tf[0]:
        raise ValueError(f"incompatible units: {from_unit!r} -> {to_unit!r}")
    return value * ff[1] / tf[1]


def split_value_unit(cell: str) -> tuple[float | None, str | None]:
    """Split '2.5 mg/mL' -> (2.5, 'mg/mL'); returns (None, None) for censored text."""
    m = _VALUE_UNIT_RE.match(cell.strip())
    if not m:
        return None, None
    try:
        return float(m.group("value")), m.group("unit")
    except (ValueError, TypeError):
        return None, None


def convert_units(
    rows: Sequence[dict[str, str]],
    column: str,
    to_unit: str,
    unit_column: str | None = None,
) -> list[dict[str, float | str]]:
    """Convert every value in ``column`` to ``to_unit``.

    The source unit for each row comes from ``unit_column`` (if given) or is
    parsed from the cell itself (e.g. '2.5 mg/mL'). Rows that cannot be
    parsed are passed through unchanged.
    """
    out: list[dict[str, float | str]] = []
    for row in rows:
        new = dict(row)
        cell = str(row.get(column, "")).strip()
        unit: str | None = None
        number: float | None = None
        if unit_column:
            unit = str(row.get(unit_column, "") or "").strip() or None
            try:
                number = float(cell)
            except ValueError:
                number = None
        else:
            number, unit = split_value_unit(cell)
            if number is None:  # try bare number with a default unit hint
                try:
                    number = float(cell)
                except ValueError:
                    number = None
        if number is None or not unit:
            out.append(new)
            continue
        try:
            new[column] = convert(number, unit, to_unit)
        except ValueError:
            pass  # incompatible/unknown unit: leave the value as-is
        out.append(new)
    return out
