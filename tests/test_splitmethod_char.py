"""Test that splitmethod='char' correctly splits into individual characters."""
import pytest
from patternforge.engine.solver import propose_solution
from patternforge.engine.tokens import tokenize


def test_splitmethod_char_splits_into_characters():
    """Test that splitmethod='char' splits text into individual characters."""
    tokens = tokenize("hello", splitmethod="char")

    # Should get individual characters: h, e, l, l, o
    assert len(tokens) == 5
    assert [t.value for t in tokens] == ['h', 'e', 'l', 'l', 'o']


def test_splitmethod_char_uses_min_token_len_1():
    """Test that splitmethod='char' automatically uses min_token_len=1."""
    # Even with min_token_len=3, char mode should use 1
    tokens = tokenize("hello", splitmethod="char", min_token_len=3)

    # Should still get all characters (min_token_len override to 1)
    assert len(tokens) == 5


def test_splitmethod_char_finds_patterns():
    """Test that splitmethod='char' can find character-based patterns."""
    include = [
        "pd_domain/moduleA/sub1/mem/i0",
        "pd_domain/moduleA/sub2/mem/i0",
        "pd_domain/moduleA/sub3/mem/i0",
    ]
    exclude = []

    solution = propose_solution(include, exclude, splitmethod='char')

    # Should find character-based patterns
    assert len(solution.patterns) > 0
    assert solution.metrics['covered'] == 3
    assert solution.metrics['fp'] == 0
    # Should NOT be using inverted solution
    assert solution.global_inverted == False


def test_splitmethod_classchange_still_works():
    """Test that splitmethod='classchange' still works as before."""
    include = [
        "Module123ABC/Instance456DEF",
        "Module123ABC/Instance789GHI",
    ]

    solution = propose_solution(include, [], splitmethod='classchange')

    # Should find patterns based on class changes
    assert len(solution.patterns) > 0
    assert solution.metrics['covered'] == 2


def test_splitmethod_char_vs_classchange():
    """Compare char vs classchange splitmethod."""
    include = ["moduleA/sub1", "moduleA/sub2", "moduleA/sub3"]
    exclude = []

    solution_char = propose_solution(include, exclude, splitmethod='char')
    solution_class = propose_solution(include, exclude, splitmethod='classchange')

    # Both should find patterns
    assert len(solution_char.patterns) > 0
    assert len(solution_class.patterns) > 0

    # Both should cover all items
    assert solution_char.metrics['covered'] == 3
    assert solution_class.metrics['covered'] == 3

    # Patterns will be different (char-level vs word-level)
    # char might find '*u*' (from 'sub'), classchange might find '*sub*'
    assert solution_char.patterns != solution_class.patterns
