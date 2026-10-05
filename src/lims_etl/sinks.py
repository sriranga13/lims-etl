"""Sinks: write tidy tables out to CSV, JSON, or SQLite."""

from __future__ import annotations

import csv
import json
import sqlite3
from typing import Sequence


def write_csv(path: str, rows: Sequence[dict], headers: Sequence[str] | None = None) -> int:
    """Write rows to CSV. Returns the number of rows written."""
    if not rows:
        return 0
    headers = list(headers) if headers is not None else list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def write_json(path: str, rows: Sequence[dict], indent: int = 2) -> int:
    """Write rows to a JSON array file. Returns the number of rows written."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(list(rows), fh, indent=indent)
    return len(rows)


def write_sqlite(
    path: str,
    rows: Sequence[dict],
    table: str = "measurements",
    headers: Sequence[str] | None = None,
) -> int:
    """Write rows to a SQLite table (created/replaced). All columns TEXT."""
    if not rows:
        return 0
    headers = list(headers) if headers is not None else list(rows[0].keys())
    cols = ", ".join(f'"{h}" TEXT' for h in headers)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')
        cur.execute(f'CREATE TABLE "{table}" ({cols})')
        placeholders = ", ".join("?" for _ in headers)
        col_list = ", ".join(f'"{h}"' for h in headers)
        cur.executemany(
            f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
            [[str(r.get(h, "")) for h in headers] for r in rows],
        )
        conn.commit()
    finally:
        conn.close()
    return len(rows)
