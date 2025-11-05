"""Tests for per-field explanation helper."""
from __future__ import annotations

from patternforge.engine.explain import explain_by_field


def test_explain_by_field_groups_atoms() -> None:
    solution = {
        "expr": "P1 | P2",
        "raw_expr": "*fabric* | *bank*",
        "patterns": [
            {"id": "P1", "text": "*fabric*", "kind": "substring", "wildcards": 2, "length": 6},
            {"id": "P2", "text": "*bank*", "kind": "substring", "wildcards": 2, "length": 4},
        ],
    }
    rows = [
        {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
        {"module": "fabric_router", "instance": "rt0/core0", "pin": "req"},
    ]
    out = explain_by_field(solution, rows, field_order=["module", "instance", "pin"])
    groups = out["by_field"]
    # fabric hits module field, bank hits instance field
    assert groups
    assert any(a["id"] == "P1" for a in groups.get("module", []))
    assert any(a["id"] == "P2" for a in groups.get("instance", []))

