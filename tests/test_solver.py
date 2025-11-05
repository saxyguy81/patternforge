"""Tests for the greedy solver and expression evaluation."""

import pytest

from patternforge.engine.solver import evaluate_expr, propose_solution


# Default test options as kwargs
DEFAULT_TEST_OPTIONS = {
    "mode": "EXACT",
    "invert": "never",
    "max_candidates": 128,
    "max_patterns": 8,
    "min_token_len": 3,
    "per_word_substrings": 8,
    "max_multi_segments": 3,
    "splitmethod": "classchange",
}


def test_propose_solution_generates_atoms() -> None:
    include = [
        "alpha/module1/mem/i0",
        "alpha/module2/mem/i0",
        "alpha/module3/io/i1",
    ]
    exclude = ["beta/module1/mem/i0"]
    solution = propose_solution(include, exclude, **DEFAULT_TEST_OPTIONS)
    assert solution.expr
    assert solution.metrics["total_positive"] == 3
    assert solution.metrics["covered"] <= 3
    assert solution.patterns


def test_propose_solution_inversion() -> None:
    include = ["one"]
    exclude = ["one", "two", "three"]
    # Create options dict with invert="always"
    options = DEFAULT_TEST_OPTIONS.copy()
    options['invert'] = 'always'
    solution = propose_solution(include, list(exclude), **options)
    assert solution.global_inverted is True


def test_evaluate_expr_roundtrip() -> None:
    include = ["alpha/mem", "alpha/io"]
    patterns = {"P1": "*alpha*"}
    metrics = evaluate_expr("P1", patterns, include, [])
    assert metrics == {"covered": 2, "total_positive": 2, "fp": 0, "fn": 0}


def test_evaluate_expr_invalid_atom() -> None:
    include = ["alpha"]
    with pytest.raises(KeyError):
        evaluate_expr("P2", {"P1": "alpha"}, include, [])
