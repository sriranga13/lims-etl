"""CLI: lims-etl load | plate | melt | units

Turns messy lab CSV exports into tidy, analysis-ready tables.
"""

from __future__ import annotations

import argparse
import csv
import sys

from . import io as _io
from . import plates as _plates
from . import sinks as _sinks
from . import tidy as _tidy
from . import units as _units


def _read_stdin_rows() -> list[list[str]]:
    return [list(r) for r in csv.reader(sys.stdin)]


def cmd_load(args: argparse.Namespace) -> int:
    table = _io.load_table(args.input, header_candidates=args.header_hint)
    rows = table.rows
    headers = table.headers

    unit_map: dict[str, str] = {}
    if args.split_units:
        new_headers = [_units.split_header_units(h)[0] for h in headers]
        rows = [{nh: r.get(oh, "") for nh, oh in zip(new_headers, headers)} for r in rows]
        headers = new_headers

    if args.normalize:
        new_headers = _io.normalize_headers(headers)
        rows = [{nh: r.get(oh, "") for nh, oh in zip(new_headers, headers)} for r in rows]
        headers = new_headers

    if args.coerce:
        coerced: list[dict] = []
        for row in rows:
            rec = dict(row)
            for col in (args.coerce or []):
                if col in rec:
                    val = _tidy.coerce_column([str(rec[col])])[0]
                    rec[col] = "" if val is None else val
            coerced.append(rec)
        rows = coerced

    print(f"# header found on line {table.header_line + 1} "
          f"({table.skipped_lines} preamble lines skipped)", file=sys.stderr)
    return _write(args, rows, headers)


def cmd_plate(args: argparse.Namespace) -> int:
    grid = _io.read_csv_rows(args.input)
    layout = _plates.PLATE_384 if args.wells == 384 else _plates.PLATE_96
    records = _plates.parse_plate(grid, layout=layout)
    if args.metadata:
        meta = _io.load_table(args.metadata)
        records = _plates.attach_metadata(records, meta.rows, on=args.join_key)
    if args.melt_plate:
        records = [{"well": r["well"], "variable": "value", "value": r["value"]} for r in records]
    print(f"# parsed {len(records)} wells ({layout.name})", file=sys.stderr)
    headers = list(records[0].keys()) if records else ["well", "row", "col", "value"]
    return _write(args, records, headers)


def cmd_melt(args: argparse.Namespace) -> int:
    table = _io.load_table(args.input)
    long = _tidy.melt_wide_to_long(
        table.rows,
        id_columns=args.id,
        value_name=args.value_name,
        variable_name=args.variable_name,
    )
    headers = list(args.id) + [args.variable_name, args.value_name]
    print(f"# melted {len(table.rows)} wide rows -> {len(long)} long rows", file=sys.stderr)
    return _write(args, long, headers)


def cmd_units(args: argparse.Namespace) -> int:
    table = _io.load_table(args.input)
    converted = _units.convert_units(table.rows, args.column, args.to, args.unit_column)
    print(f"# converted column {args.column!r} to {args.to}", file=sys.stderr)
    return _write(args, converted, table.headers)


def _write(args: argparse.Namespace, rows: list[dict], headers: list[str]) -> int:
    if args.output == "-":
        if rows:
            writer = csv.DictWriter(sys.stdout, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return 0
    if args.output.endswith(".json"):
        n = _sinks.write_json(args.output, rows)
    elif args.output.endswith(".db") or args.output.endswith(".sqlite"):
        n = _sinks.write_sqlite(args.output, rows, table=args.table)
    else:
        n = _sinks.write_csv(args.output, rows, headers)
    print(f"# wrote {n} rows -> {args.output}", file=sys.stderr)
    return 0


def _add_sink_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("-o", "--output", default="-",
                   help="Output path: .csv (default), .json, .db/.sqlite. '-' = stdout.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lims-etl",
        description="Normalize messy lab CSV exports into tidy tables.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("load", help="Load a messy export, skipping preamble lines.")
    pl.add_argument("input")
    pl.add_argument("--header-hint", action="append", default=None,
                    help="Column name hint to locate the header row (repeatable).")
    pl.add_argument("--split-units", action="store_true",
                    help="Split 'Name (unit)' headers into name + report unit.")
    pl.add_argument("--normalize", action="store_true",
                    help="Normalize headers to snake_case.")
    pl.add_argument("--coerce", action="append", default=None, metavar="COLUMN",
                    help="Coerce column values to float (repeatable).")
    _add_sink_args(pl)
    pl.set_defaults(func=cmd_load)

    pp = sub.add_parser("plate", help="Parse a plate-reader grid into tidy wells.")
    pp.add_argument("input")
    pp.add_argument("--wells", type=int, choices=[96, 384], default=96)
    pp.add_argument("--metadata", default=None,
                    help="CSV of sample metadata to join (needs a 'well' column).")
    pp.add_argument("--join-key", default="well")
    pp.add_argument("--melt-plate", action="store_true",
                    help="Emit (well, variable, value) rows.")
    _add_sink_args(pp)
    pp.set_defaults(func=cmd_plate)

    pm = sub.add_parser("melt", help="Melt wide measurement columns into long form.")
    pm.add_argument("input")
    pm.add_argument("--id", action="append", default=[], metavar="COLUMN",
                    help="ID column to keep (repeatable).")
    pm.add_argument("--value-name", default="value")
    pm.add_argument("--variable-name", default="variable")
    _add_sink_args(pm)
    pm.set_defaults(func=cmd_melt)

    pu = sub.add_parser("units", help="Convert a measurement column between units.")
    pu.add_argument("input")
    pu.add_argument("column")
    pu.add_argument("--to", required=True, help="Target unit, e.g. g/L or ug/ml.")
    pu.add_argument("--unit-column", default=None,
                    help="Column holding per-row source units.")
    _add_sink_args(pu)
    pu.set_defaults(func=cmd_units)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
