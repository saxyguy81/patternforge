"""Tests for the greedy solver and expression evaluation."""

import pytest

from codex.engine.models import (
    InvertStrategy,
    OptimizeBudgets,
    OptimizeWeights,
    QualityMode,
    SolveOptions,
)
from codex.engine.solver import evaluate_expr, propose_solution


def _options(invert: InvertStrategy = InvertStrategy.NEVER) -> SolveOptions:
    return SolveOptions(
        mode=QualityMode.EXACT,
        invert=invert,
        weights=OptimizeWeights(),
        budgets=OptimizeBudgets(max_candidates=128, max_atoms=8, max_ops=8, depth=2),
        allow_not_on_atoms=True,
        min_token_len=3,
        per_word_substrings=8,
        per_word_multi=4,
        per_word_cuts=16,
        max_multi_segments=3,
        splitmethod="classchange",
        seed=0,
    )


def test_propose_solution_generates_atoms() -> None:
    include = [
        "alpha/module1/mem/i0",
        "alpha/module2/mem/i0",
        "alpha/module3/io/i1",
    ]
    exclude = ["beta/module1/mem/i0"]
    solution = propose_solution(include, exclude, _options())
    assert solution["expr"]
    assert solution["metrics"]["total_positive"] == 3
    assert solution["metrics"]["covered"] <= 3
    assert solution["atoms"]


def test_propose_solution_inversion() -> None:
    include = ["one"]
    exclude = ["one", "two", "three"]
    solution = propose_solution(include, list(exclude), _options(invert=InvertStrategy.ALWAYS))
    assert solution["global_inverted"] is True


def test_evaluate_expr_roundtrip() -> None:
    include = ["alpha/mem", "alpha/io"]
    atoms = {"P1": "*alpha*"}
    metrics = evaluate_expr("P1", atoms, include, [])
    assert metrics == {"covered": 2, "total_positive": 2, "fp": 0, "fn": 0}


def test_evaluate_expr_invalid_atom() -> None:
    include = ["alpha"]
    with pytest.raises(KeyError):
        evaluate_expr("P2", {"P1": "alpha"}, include, [])
