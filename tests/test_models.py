"""Tests for data models."""

from codex.engine.models import InvertStrategy, QualityMode, SolveOptions


def test_solve_options_for_inversion() -> None:
    options = SolveOptions(mode=QualityMode.APPROX, invert=InvertStrategy.AUTO)
    inverted = options.for_inversion()
    assert inverted.mode is options.mode
    assert inverted.invert is options.invert
