"""Tests for expression parser edge cases."""

import pytest

from codex.engine.solver import _ExprParser


def test_parser_valid_expression() -> None:
    parser = _ExprParser("P1 | (P2 & !P3)")
    tree = parser.parse()
    assert tree[0] == "|"


@pytest.mark.parametrize(
    "expr",
    ["Q1", "(P1", "P1 |"],
    ids=["unknown_atom", "missing_paren", "dangling_or"],
)
def test_parser_invalid(expr: str) -> None:
    parser = _ExprParser(expr)
    with pytest.raises(ValueError):
        parser.parse()
