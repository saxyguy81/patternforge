"""Input/output helpers for the patternforge CLI."""
import csv
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class Items:
    """Container describing include/exclude sets."""

    include: list[str]
    exclude: list[str]


def _read_text_lines(handle: TextIO) -> list[str]:
    return [line.rstrip("\n\r") for line in handle if line.strip()]


def _read_jsonl(handle: TextIO) -> list[str]:
    data: list[str] = []
    for raw in handle:
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        if isinstance(obj, dict) and "item" in obj:
            value = obj["item"]
        else:
            value = obj
        data.append(str(value))
    return data


def _read_csv(handle: TextIO, column: str = "item") -> list[str]:
    reader = csv.DictReader(handle)
    fieldnames = reader.fieldnames or []
    if column in fieldnames:
        return [row[column] for row in reader if row.get(column)]

    # Fallback: compose a hierarchical path from common field names.
    join_fields = [
        name for name in ("module", "instance", "pin", "signal") if name in fieldnames
    ]
    if not join_fields:
        raise ValueError(
            "CSV missing required column 'item' and no supported composite columns were found"
        )

    items: list[str] = []
    for row in reader:
        components: list[str] = []
        for name in join_fields:
            value = row.get(name, "")
            if value:
                components.append(str(value).strip())
        if components:
            items.append("/".join(components))
    return items


def _open_path(path: str) -> Iterable[str]:
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext in {".json", ".jsonl"}:
        with open(path, encoding="utf-8") as handle:
            for line in _read_jsonl(handle):
                yield line
    elif ext in {".csv"}:
        with open(path, encoding="utf-8", newline="") as handle:
            for line in _read_csv(handle):
                yield line
    else:
        with open(path, encoding="utf-8") as handle:
            for line in _read_text_lines(handle):
                yield line


def read_items(path: str) -> list[str]:
    return list(_open_path(path))


def load_solution(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_solution(solution: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(solution, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_json(obj: dict, path: str) -> None:
    if path == "-":
        json.dump(obj, os.sys.stdout, indent=2, sort_keys=True)
        os.sys.stdout.write("\n")
        os.sys.stdout.flush()
        return
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_text(text: str, path: str) -> None:
    if path == "-":
        os.sys.stdout.write(text)
        if not text.endswith("\n"):
            os.sys.stdout.write("\n")
        os.sys.stdout.flush()
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def ensure_items(include_path: str, exclude_path: str | None) -> Items:
    include = read_items(include_path)
    exclude = read_items(exclude_path) if exclude_path else []
    return Items(include=include, exclude=exclude)
