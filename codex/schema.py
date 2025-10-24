"""Schema utilities for structured paths."""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSchema:
    name: str
    delimiter: str
    fields: list[str]

    def split(self, item: str) -> list[str]:
        parts = item.split(self.delimiter)
        if len(parts) < len(self.fields):
            parts = parts + [""] * (len(self.fields) - len(parts))
        return parts


def load_schema(path: str) -> FieldSchema:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    name = payload.get("name", "path")
    delimiter = payload.get("delimiter", "/")
    fields = payload.get("fields")
    if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise ValueError("schema fields must be an array of strings")
    return FieldSchema(name=name, delimiter=delimiter, fields=list(fields))


def schema_from_flags(delimiter: str | None, fields: str | None) -> FieldSchema | None:
    if delimiter is None and fields is None:
        return None
    if delimiter is None:
        delimiter = "/"
    if not fields:
        raise ValueError("--fields requires comma separated names when delimiter is supplied")
    return FieldSchema(
        name="inline",
        delimiter=delimiter,
        fields=[f.strip() for f in fields.split(",") if f.strip()],
    )
