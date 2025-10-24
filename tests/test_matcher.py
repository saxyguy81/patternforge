"""Tests for pattern matching helpers."""

import pytest

from patternforge.engine.matcher import match_all, match_pattern, ordered_match, wildcard_count


@pytest.mark.parametrize(
    "pattern,text,expected",
    [
        ("*", "abc", True),
        ("abc", "abc", True),
        ("abc", "abcd", False),
        ("*bc", "abc", True),
        ("a*c", "abc", True),
        ("a*d", "abc", False),
    ],
)
def test_match_pattern(pattern: str, text: str, expected: bool) -> None:
    assert match_pattern(text, pattern) is expected


def test_ordered_match_variants() -> None:
    assert ordered_match("abcxxpat1yyypat2", ["abc", "pat1", "pat2"], True, False)
    assert not ordered_match("abcpat2pat1", ["pat1", "pat2"], False, False)
    assert ordered_match("midpat1end", ["pat1", "end"], False, True)


def test_match_all_and_wildcard_count() -> None:
    texts = ["abc", "def", "abdefc"]
    flags = match_all(texts, "a*c")
    assert flags == [True, False, True]
    assert wildcard_count("*abc*") == 0
