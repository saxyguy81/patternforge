"""Tests for solution terms, residual coverage, and flags."""
from __future__ import annotations

from patternforge.engine.models import InvertStrategy, OptimizeBudgets, QualityMode, SolveOptions
from patternforge.engine.solver import propose_solution


def _options(**kwargs) -> SolveOptions:
    opts = SolveOptions(
        mode=QualityMode.EXACT,
        invert=InvertStrategy.NEVER,
        budgets=OptimizeBudgets(max_candidates=256, max_atoms=8),
        allow_complex_expressions=kwargs.get("allow_complex_expressions", False),
        min_token_len=3,
        per_word_substrings=8,
        max_multi_segments=3,
        splitmethod="classchange",
    )
    return opts


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
    sol = propose_solution(include, exclude, _options())
    assert "expressions" in sol and isinstance(sol["expressions"], list)
    covered = sol["metrics"]["covered"]
    residual_sum = sum(t.get("incremental_tp", 0) for t in sol["expressions"])
    assert residual_sum == covered


def test_terms_fields_present_and_flag() -> None:
    include = ["alpha/m1", "beta/m2"]
    exclude: list[str] = ["alpha/dbg"]
    sol = propose_solution(include, exclude, _options())
    assert sol.get("term_method") == "additive"
    term = sol["expressions"][0]
    for key in ("expr", "raw_expr", "tp", "fp", "fn", "incremental_tp", "incremental_fp", "length"):
        assert key in term


def test_terms_flag_inverted_subtractive() -> None:
    include = ["a/x"]
    exclude = ["a/y", "b/z"]
    opts = _options()
    opts = SolveOptions(**{**opts.__dict__, "invert": InvertStrategy.ALWAYS})
    sol = propose_solution(include, exclude, opts)
    assert sol.get("term_method") == "subtractive"


def test_terms_with_allow_complex_terms_flag() -> None:
    include = ["alpha/module1", "beta/module2"]
    exclude = ["alpha/debug", "beta/debug"]
    sol = propose_solution(include, exclude, _options(allow_complex_terms=True))
    # Complex terms may or may not form conjunctions; ensure schema remains stable
    assert isinstance(sol.get("expressions", []), list)
    for t in sol["expressions"]:
        assert set(["expr", "raw_expr", "tp", "fp", "fn", "incremental_tp", "incremental_fp", "length"]).issubset(t.keys())
