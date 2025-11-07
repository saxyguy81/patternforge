"""Tests for complex conjunction terms when enabled."""
from __future__ import annotations

from patternforge.engine.solver import propose_solution


# Complex terms options as kwargs dict
COMPLEX_OPTIONS = {
    "mode": "EXACT",
    "invert": "never",
    "max_candidates": 256,
    "max_patterns": 8,
    "allow_complex_expressions": True,
    "min_token_len": 3,
    "per_word_substrings": 8,
    "max_multi_segments": 3,
    "splitmethod": "classchange",
}


def test_conjunction_term_present_and_reduces_fp() -> None:
    # Includes contain both 'cache' and 'bank'; excludes split the signals across different items
    include = [
        "mod/cache/bank0",
        "mod/cache/bank1",
    ]
    exclude = [
        "debug/cache/zzz",
        "debug/bank/zzz",
    ]
    sol = propose_solution(include, exclude, **COMPLEX_OPTIONS)
    # Expect at least one expression containing an '&'
    expressions = sol.expressions
    assert any("&" in t.get("expr", "") or "&" in t.get("raw_expr", "") for t in expressions)
    # Find that conjunction and assert it has lower fp than components would individually
    conj = next(t for t in expressions if "&" in t.get("expr", "") or "&" in t.get("raw_expr", ""))
    assert conj["fp"] == 0
    assert conj["matches"] == 2


def test_and_not_term_present_and_reduces_fp() -> None:
    include = [
        "mod/cache",
        "mod/cache",
    ]
    exclude = [
        "dbg/cache",
    ]
    sol = propose_solution(include, exclude, **COMPLEX_OPTIONS)
    expressions = sol.expressions
    # Expect a '-' based expression
    assert any("-" in t.get("expr", "") or "-" in t.get("raw_expr", "") for t in expressions)
    minus = next(t for t in expressions if "-" in t.get("expr", "") or "-" in t.get("raw_expr", ""))
    assert minus["fp"] == 0
    assert minus["matches"] == 2
