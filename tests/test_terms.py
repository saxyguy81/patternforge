"""Tests for solution terms, residual coverage, and flags."""
from __future__ import annotations

from patternforge.engine.solver import propose_solution


# Default test options as kwargs dict
DEFAULT_OPTIONS = {
    "mode": "EXACT",
    "invert": "never",
    "max_candidates": 256,
    "max_patterns": 8,
    "min_token_len": 3,
    "per_word_substrings": 8,
    "max_multi_segments": 3,
    "splitmethod": "classchange",
}


def test_terms_residual_sums_to_covered() -> None:
    include = [
        "alpha/module1",
        "beta/module2",
        "gamma/io",
    ]
    exclude = [
        "alpha/debug",
        "beta/debug",
        "zzz/yyy",
    ]
    sol = propose_solution(include, exclude, **DEFAULT_OPTIONS)
    assert sol.expressions and isinstance(sol.expressions, list)
    covered = sol.metrics["covered"]
    residual_sum = sum(t.get("incremental_tp", 0) for t in sol.expressions)
    assert residual_sum == covered


def test_terms_fields_present_and_flag() -> None:
    include = ["alpha/m1", "beta/m2"]
    exclude: list[str] = ["alpha/dbg"]
    sol = propose_solution(include, exclude, **DEFAULT_OPTIONS)
    assert sol.term_method == "additive"
    term = sol.expressions[0]
    for key in ("expr", "raw_expr", "tp", "fp", "fn", "incremental_tp", "incremental_fp", "length"):
        assert key in term


def test_terms_flag_inverted_subtractive() -> None:
    include = ["a/x"]
    exclude = ["a/y", "b/z"]
    opts = DEFAULT_OPTIONS.copy()
    opts["invert"] = "always"  # Override default
    sol = propose_solution(include, exclude, **opts)
    assert sol.term_method == "subtractive"


def test_terms_with_allow_complex_terms_flag() -> None:
    include = ["alpha/module1", "beta/module2"]
    exclude = ["alpha/debug", "beta/debug"]
    opts = DEFAULT_OPTIONS.copy()
    opts["allow_complex_expressions"] = True  # Fixed: was allow_complex_terms
    sol = propose_solution(include, exclude, **opts)
    # Complex terms may or may not form conjunctions; ensure schema remains stable
    assert isinstance(sol.expressions, list)
    for t in sol.expressions:
        assert set(["expr", "raw_expr", "tp", "fp", "fn", "incremental_tp", "incremental_fp", "length"]).issubset(t.keys())
