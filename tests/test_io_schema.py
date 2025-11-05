"""Tests for IO helpers and schema utilities."""

import json
from pathlib import Path

import pytest

from patternforge import io
from patternforge.schema import FieldSchema, load_schema, schema_from_flags


def test_read_text_and_jsonl(tmp_path: Path) -> None:
    text_path = tmp_path / "items.txt"
    text_path.write_text("alpha\nbeta\n")
    assert io.read_items(str(text_path)) == ["alpha", "beta"]

    jsonl_path = tmp_path / "items.jsonl"
    jsonl_path.write_text('{"item":"gamma"}\n{"item":"delta"}\n')
    assert io.read_items(str(jsonl_path)) == ["gamma", "delta"]


def test_read_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text("item\nalpha\nbeta\n")
    assert io.read_items(str(csv_path)) == ["alpha", "beta"]


def test_read_csv_composite_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "connections.csv"
    csv_path.write_text(
        "module,instance,pin\n"
        "fabric,cache0/bank0,req_in\n"
        "fabric,cache0/bank1,req_out\n"
        "fabric,cache1/bank0,data_in\n"
    )
    assert io.read_items(str(csv_path)) == [
        "fabric/cache0/bank0/req_in",
        "fabric/cache0/bank1/req_out",
        "fabric/cache1/bank0/data_in",
    ]


def test_load_and_save_solution(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "solution.json"
    payload = {"expr": "P1", "patterns": []}
    io.save_solution(payload, str(path))
    loaded = io.load_solution(str(path))
    assert loaded == payload

    # Ensure writing to stdout path works without raising.
    io.write_json(payload, "-")
    io.write_text("payload", "-")
    captured = capsys.readouterr()
    assert "expr" in captured.out


def test_schema_loading(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"name": "path", "delimiter": "/", "fields": ["a", "b"]}))
    schema = load_schema(str(schema_path))
    assert isinstance(schema, FieldSchema)
    assert schema.split("alpha/beta") == ["alpha", "beta"]

    inline = schema_from_flags("/", "a,b")
    assert inline is not None
    assert inline.fields == ["a", "b"]

    assert schema_from_flags(None, None) is None


def test_schema_from_flags_missing_fields() -> None:
    with pytest.raises(ValueError):
        schema_from_flags("/", None)


def test_load_schema_invalid_fields(tmp_path: Path) -> None:
    schema_path = tmp_path / "bad.json"
    schema_path.write_text(json.dumps({"name": "path", "delimiter": "/", "fields": "not-a-list"}))
    with pytest.raises(ValueError):
        load_schema(str(schema_path))
