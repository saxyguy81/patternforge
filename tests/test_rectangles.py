"""Tests for rectangle planner."""

from codex.engine.rectangles import plan_rectangles


def test_plan_rectangles_counts() -> None:
    include = ["alpha/x", "alpha/y", "beta/z", "beta/y"]
    plan = plan_rectangles(include, rect_budget=2, rect_penalty=1.0, exception_weight=0.5)
    assert plan["total"] == 4
    prefixes = {rect["prefix"] for rect in plan["rectangles"]}
    assert prefixes == {"alpha", "beta"}
