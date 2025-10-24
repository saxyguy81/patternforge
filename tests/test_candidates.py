"""Tests for candidate generation."""

from patternforge.engine.candidates import generate_candidates


def test_generate_candidates_basic() -> None:
    include = ["alpha/beta/gamma", "alpha/delta/gamma"]
    result = generate_candidates(
        include,
        splitmethod="classchange",
        min_token_len=3,
        per_word_substrings=8,
        per_word_multi=4,
        max_multi_segments=3,
    )
    assert result
    patterns = [pattern for pattern, _, _ in result]
    assert any(pattern.startswith("*alpha") for pattern in patterns)
    assert any(pattern.endswith("gamma") for pattern in patterns)
