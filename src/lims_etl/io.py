"""CSV ingestion helpers for messy lab exports.

Instruments often write a preamble (metadata lines, run info) before the
actual header row, and values are padded with stray whitespace. These
helpers find the real header and return clean row dicts.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence


@dataclass
class LoadedTable:
    """Result of :func:`load_table`."""

    headers: list[str]
    rows: list[dict[str, str]]
    header_line: int  # 0-based line number of the detected header row
    skipped_lines: int  # number of preamble lines before the header


def read_csv_rows(path: str, encoding: str = "utf-8-sig") -> list[list[str]]:
    """Read a CSV file into a list of raw string rows."""
    with open(path, newline="", encoding=encoding) as fh:
        return [list(row) for row in csv.reader(fh)]


def find_header_row(
    rows: Sequence[Sequence[str]],
    candidates: Sequence[str] | None = None,
) -> int:
    """Return the 0-based index of the most likely header row.

    Strategy: scan the first 25 rows and score each row by how many of its
    non-empty cells are non-numeric (headers are mostly text labels).
    If ``candidates`` is given, the row whose first non-empty cell matches
    one of the candidates (case-insensitive) wins immediately.

    Raises:
        ValueError: if no plausible header row is found.
    """
    limit = min(len(rows), 25)
    if limit == 0:
        raise ValueError("no rows to inspect")

    best_idx, best_score = -1, -1
    for i in range(limit):
        cells = [c.strip() for c in rows[i] if c.strip()]
        if not cells:
            continue
        if candidates and cells[0].lower() in {c.lower() for c in candidates}:
            return i
        text_like = sum(1 for c in cells if not _looks_numeric(c))
        score = text_like * 2 - len(cells) * 0
        score -= sum(1 for c in cells if _looks_numeric(c))
        if score > best_score:
            best_score, best_idx = score, i
    if best_idx < 0:
        raise ValueError("no plausible header row found")
    return best_idx


def _looks_numeric(value: str) -> bool:
    """True if the value looks like a plain number (after unit stripping)."""
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return False
    # allow '<', '>' prefixes (censored values like '<0.01')
    cleaned = cleaned.lstrip("<>").strip()
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def normalize_headers(headers: Iterable[str]) -> list[str]:
    """Normalize headers: strip, lowercase, collapse whitespace to underscores."""
    out: list[str] = []
    seen: dict[str, int] = {}
    for h in headers:
        base = re.sub(r"\s+", "_", h.strip().lower())
        base = re.sub(r"[^a-z0-9_]", "", base) or "column"
        count = seen.get(base, 0)
        seen[base] = count + 1
        out.append(f"{base}_{count + 1}" if count else base)
    return out


def load_table(
    path: str,
    header_candidates: Sequence[str] | None = None,
    encoding: str = "utf-8-sig",
) -> LoadedTable:
    """Load a messy CSV export into a :class:`LoadedTable`.

    Skips preamble lines, detects the header row, strips whitespace from
    every cell, and drops fully-empty trailing rows.
    """
    raw = read_csv_rows(path, encoding=encoding)
    idx = find_header_row(raw, candidates=header_candidates)
    headers = [c.strip() for c in raw[idx]]
    rows: list[dict[str, str]] = []
    for line in raw[idx + 1 :]:
        cells = [c.strip() for c in line]
        if not any(cells):
            continue
        # pad short rows so zip() keeps all headers
        cells += [""] * (len(headers) - len(cells))
        rows.append(dict(zip(headers, cells)))
    return LoadedTable(
        headers=headers,
        rows=rows,
        header_line=idx,
        skipped_lines=idx,
    )


def iter_rows(text: str) -> Iterator[dict[str, str]]:
    """Convenience: yield row dicts from a CSV string (first line is header)."""
    fh = io.StringIO(text)
    for row in csv.DictReader(fh):
        yield {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
