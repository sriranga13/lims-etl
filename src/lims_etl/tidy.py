"""Tidying helpers: dtype coercion, censored values, wide-to-long melts."""

from __future__ import annotations

from typing import Sequence

# Values that mean "below/above quantification or not detected" rather
# than a number; passed through by coercion instead of raising.
CENSORED_TOKENS = {"ND", "N/D", "BQL", "<BQL", "TNTC", ">TNTC", "NS", "NA", "N/A", ""}
CENSORED_PREFIXES = ("<", ">", "<=", ">=")


def is_censored(value: str) -> bool:
    """True if the cell is a censored/detection-limit token rather than data."""
    v = value.strip().upper()
    if v in CENSORED_TOKENS:
        return True
    return any(v.startswith(p) for p in CENSORED_PREFIXES) and _rest_is_number(v)


def _rest_is_number(value: str) -> bool:
    for p in CENSORED_PREFIXES:
        if value.startswith(p):
            try:
                float(value[len(p):])
                return True
            except ValueError:
                return False
    return False


def coerce_column(
    values: Sequence[str],
    target: str = "float",
    keep_censored: bool = True,
) -> list:
    """Coerce a column of strings to ``target`` ('float' or 'int').

    Censored tokens (ND, <0.01, BQL, ...) are preserved as their original
    string when ``keep_censored`` is True; otherwise they become None.
    Non-censored non-numeric values become None.
    """
    out: list = []
    for v in values:
        s = v.strip()
        if is_censored(s):
            out.append(s if keep_censored else None)
            continue
        try:
            num = float(s.replace(",", ""))
        except ValueError:
            out.append(None)
            continue
        out.append(int(num) if target == "int" else num)
    return out


def melt_wide_to_long(
    rows: Sequence[dict[str, str]],
    id_columns: Sequence[str],
    value_name: str = "value",
    variable_name: str = "variable",
) -> list[dict[str, str]]:
    """Melt wide measurement columns into tidy long form.

    Every non-id column becomes a row: (ids..., variable_name=column,
    value_name=cell). Empty cells are dropped.
    """
    out: list[dict[str, str]] = []
    id_columns = list(id_columns)
    for row in rows:
        for col, val in row.items():
            if col in id_columns:
                continue
            if val is None or str(val).strip() == "":
                continue
            rec = {c: row.get(c, "") for c in id_columns}
            rec[variable_name] = col
            rec[value_name] = str(val)
            out.append(rec)
    return out


def drop_empty_columns(
    rows: Sequence[dict[str, str]], headers: Sequence[str] | None = None
) -> tuple[list[str], list[dict[str, str]]]:
    """Remove columns that are empty across all rows."""
    headers = list(headers) if headers is not None else (
        list(rows[0].keys()) if rows else []
    )
    keep = [h for h in headers if any(str(r.get(h, "")).strip() for r in rows)]
    return keep, [{h: r.get(h, "") for h in keep} for r in rows]
