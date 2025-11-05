"""Tests for explanation helpers."""

from patternforge.engine.explain import explain_dict, explain_text, summarize_text


def sample_solution() -> dict:
    return {
        "expr": "P1",
        "raw_expr": "*alpha*",
        "global_inverted": False,
        "metrics": {"covered": 2, "total_positive": 2, "fp": 1, "fn": 0},
        "patterns": [
            {
                "id": "P1",
                "text": "*alpha*",
                "kind": "substring",
                "wildcards": 2,
                "length": 5,
                "tp": 2,
                "fp": 1,
            }
        ],
        "witnesses": {
            "tp_examples": ["alpha/module1"],
            "fp_examples": ["beta/module1"],
            "fn_examples": [],
        },
    }


def test_explain_dict() -> None:
    sol = sample_solution()
    payload = explain_dict(sol, ["alpha/module1", "alpha/module2"], ["beta/module1"])
    assert payload["metrics"]["covered"] == 2
    assert payload["patterns"][0]["tp"] == 2


def test_explain_text() -> None:
    sol = sample_solution()
    text = explain_text(sol, ["alpha/module1", "alpha/module2"], [])
    assert "EXPR: P1" in text
    assert "RAW:" in text
    assert "FP" in text


def test_summarize_text() -> None:
    sol = sample_solution()
    summary = summarize_text(sol)
    assert "covers 2 of 2" in summary
