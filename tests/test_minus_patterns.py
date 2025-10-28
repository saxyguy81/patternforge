"""Tests for raw-pattern minus operator ('-') and complex combinations."""
from __future__ import annotations

from patternforge.engine.solver import evaluate_expr


def test_evaluate_expr_with_minus_pattern() -> None:
    include = ["mod/cache", "mod/cacheX", "alpha"]
    exclude = ["dbg/cache", "dbg/cacheX", "beta"]
    atoms = {"P1": "*cache* - *dbg*"}
    metrics = evaluate_expr("P1", atoms, include, exclude)
    # P1 should match the two include cache items and exclude the dbg/cache items
    assert metrics == {"covered": 2, "total_positive": 3, "fp": 0, "fn": 1}


def test_evaluate_expr_with_and_and_minus() -> None:
    include = ["mod/cache", "mod/cacheX", "mod/cache/router", "alpha"]
    exclude = ["dbg/cache", "router/cache", "beta"]
    atoms = {"P1": "(*mod*) & (*cache*) - (*router*)"}
    metrics = evaluate_expr("P1", atoms, include, exclude)
    # Matches include items containing mod and cache but not router
    assert metrics == {"covered": 2, "total_positive": 4, "fp": 0, "fn": 2}

