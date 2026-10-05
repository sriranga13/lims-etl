import csv
import json
import os
import sqlite3
import tempfile

import pytest

from lims_etl.cli import main
from lims_etl.sinks import write_csv, write_json, write_sqlite


def _tmp(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as fh:
        fh.write(content)
    return path


def test_cli_load_stdout(capsys):
    path = _tmp("sample_id,result\nS1,1.5\n")
    try:
        assert main(["load", path, "-o", "-"]) == 0
        out = capsys.readouterr().out
        assert "S1" in out and "sample_id" in out
    finally:
        os.unlink(path)


def test_cli_load_split_units(capsys):
    path = _tmp("Sample ID,Concentration (mg/mL)\nS1,2.5\n")
    try:
        assert main(["load", path, "--split-units", "-o", "-"]) == 0
        assert "Concentration" in capsys.readouterr().out
    finally:
        os.unlink(path)


def test_cli_load_normalize(capsys):
    path = _tmp("Sample ID,Result\nS1,1\n")
    try:
        assert main(["load", path, "--normalize", "-o", "-"]) == 0
        out = capsys.readouterr().out
        assert "sample_id" in out
    finally:
        os.unlink(path)


def test_cli_plate_to_csv():
    src = _tmp(",1,2\nA,0.1,0.2\nB,0.3,0.4\n")
    out = src + ".out.csv"
    try:
        assert main(["plate", src, "-o", out]) == 0
        with open(out) as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["well"] == "A1"
        assert len(rows) == 4
    finally:
        os.unlink(src)
        os.unlink(out)


def test_cli_plate_with_metadata():
    src = _tmp(",1\nA,0.1\n")
    meta = _tmp("well,sample_id\nA1,S-100\n")
    out = src + ".out.csv"
    try:
        assert main(["plate", src, "--metadata", meta, "-o", out]) == 0
        with open(out) as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["sample_id"] == "S-100"
    finally:
        for p in (src, meta, out):
            os.unlink(p)


def test_cli_melt():
    src = _tmp("sample,day1,day2\nS1,10,20\n")
    out = src + ".out.csv"
    try:
        assert main(["melt", src, "--id", "sample", "-o", out]) == 0
        with open(out) as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2
        assert rows[0]["variable"] == "day1"
    finally:
        os.unlink(src)
        os.unlink(out)


def test_cli_units():
    src = _tmp("value,unit\n1000,ug/ml\n")
    out = src + ".out.csv"
    try:
        assert main(["units", src, "value", "--to", "mg/ml",
                     "--unit-column", "unit", "-o", out]) == 0
        with open(out) as fh:
            rows = list(csv.DictReader(fh))
        assert float(rows[0]["value"]) == pytest.approx(1.0)
    finally:
        os.unlink(src)
        os.unlink(out)


def test_sink_json():
    path = tempfile.mktemp(suffix=".json")
    try:
        assert write_json(path, [{"a": 1}]) == 1
        assert json.load(open(path)) == [{"a": 1}]
    finally:
        os.unlink(path)


def test_sink_csv():
    path = tempfile.mktemp(suffix=".csv")
    try:
        assert write_csv(path, [{"a": "1", "b": "2"}]) == 1
    finally:
        os.unlink(path)


def test_sink_sqlite():
    path = tempfile.mktemp(suffix=".db")
    try:
        assert write_sqlite(path, [{"well": "A1", "value": "0.1"}], table="wells") == 1
        conn = sqlite3.connect(path)
        rows = conn.execute('SELECT well, value FROM wells').fetchall()
        conn.close()
        assert rows == [("A1", "0.1")]
    finally:
        os.unlink(path)
