"""Tests for IDF computation."""

from codex.engine.idf import compute_idf
from codex.engine.tokens import Token


def test_compute_idf() -> None:
    tokens = [Token("alpha", 0), Token("beta", 1), Token("alpha", 2)]
    values = compute_idf(tokens, total_docs=4)
    assert "alpha" in values and values["alpha"] < values["beta"]
