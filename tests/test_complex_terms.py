"""Tests for complex conjunction terms when enabled."""
from __future__ import annotations

from patternforge.engine.models import InvertStrategy, OptimizeBudgets, QualityMode, SolveOptions
from patternforge.engine.solver import propose_solution


def _opts_complex() -> SolveOptions:
    return SolveOptions(
        mode=QualityMode.EXACT,
        invert=InvertStrategy.NEVER,
        budgets=OptimizeBudgets(max_candidates=256, max_atoms=8, max_ops=8, depth=2),
        allow_not_on_atoms=True,
        allow_complex_terms=True,
        min_token_len=3,
        per_word_substrings=8,
        per_word_multi=4,
        per_word_cuts=16,
        max_multi_segments=3,
        splitmethod="classchange",
        seed=0,
    )


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
    sol = propose_solution(include, exclude, _opts_complex())
    # Expect at least one term containing an '&'
    terms = sol.get("terms", [])
    assert any("&" in t.get("expr", "") or "&" in t.get("raw_expr", "") for t in terms)
    # Find that conjunction and assert it has lower fp than components would individually
    conj = next(t for t in terms if "&" in t.get("expr", "") or "&" in t.get("raw_expr", ""))
    assert conj["fp"] == 0
    assert conj["tp"] == 2


def test_and_not_term_present_and_reduces_fp() -> None:
    include = [
        "mod/cache",
        "mod/cache",
    ]
    exclude = [
        "dbg/cache",
    ]
    sol = propose_solution(include, exclude, _opts_complex())
    terms = sol.get("terms", [])
    # Expect a '-' based term
    assert any("-" in t.get("expr", "") or "-" in t.get("raw_expr", "") for t in terms)
    minus = next(t for t in terms if "-" in t.get("expr", "") or "-" in t.get("raw_expr", ""))
    assert minus["fp"] == 0
    assert minus["tp"] == 2
