"""Test empty exclude edge cases - ensure no trivial '*' patterns."""
from patternforge.engine.solver import propose_solution, propose_solution_structured


def test_empty_exclude_normal_paths():
    """Empty exclude should produce specific patterns, not trivial '*'."""
    include = [
        "alpha/module1/mem/i0",
        "alpha/module2/mem/i1",
        "beta/cache/bank0",
    ]
    exclude = []

    solution = propose_solution(include, exclude)

    # Should not return trivial wildcard
    assert solution.raw_expr != "*"
    assert "*" not in [p.text for p in solution.patterns]

    # Should produce specific patterns
    assert len(solution.patterns) > 0
    assert solution.metrics["covered"] == len(include)


def test_empty_exclude_identical_items():
    """Empty exclude with identical items should produce exact match."""
    include = ["foo/bar/baz"] * 10
    exclude = []

    solution = propose_solution(include, exclude)

    # Should not return trivial wildcard
    assert solution.raw_expr != "*"
    assert "*" not in [p.text for p in solution.patterns]

    # Should produce exact match or specific pattern
    assert len(solution.patterns) >= 1
    assert solution.metrics["covered"] == 10


def test_empty_exclude_diverse_items():
    """Empty exclude with diverse items should produce specific patterns."""
    include = [f"item_{i}" for i in range(20)]
    exclude = []

    solution = propose_solution(include, exclude)

    # Should not return trivial wildcard
    assert solution.raw_expr != "*"
    if solution.patterns:  # May have no good solution for very diverse items
        assert "*" not in [p.text for p in solution.patterns]


def test_empty_exclude_structured():
    """Empty exclude_rows in structured solver should produce specific patterns."""
    include_rows = [
        {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[31]"},
        {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DOUT[0]"},
    ]
    exclude_rows = []

    solution = propose_solution_structured(include_rows, exclude_rows)

    # Should not return trivial wildcard
    assert solution.raw_expr != "*"
    if solution.patterns:
        assert "*" not in [p.text for p in solution.patterns]

    # Patterns should have actual field content
    for p in solution.patterns:
        if p.field:  # Structured patterns have fields
            text_without_wildcards = p.text.replace("*", "").strip()
            assert text_without_wildcards, f"Pattern '{p.text}' has no content"


def test_empty_exclude_single_item():
    """Empty exclude with single item should produce specific pattern."""
    include = ["chip/cpu/core0"]
    exclude = []

    solution = propose_solution(include, exclude)

    # Should not return trivial wildcard
    assert solution.raw_expr != "*"
    assert "*" not in [p.text for p in solution.patterns]

    # Should produce at least one pattern
    assert len(solution.patterns) >= 1


def test_empty_exclude_pattern_specificity():
    """Patterns should have actual content, not just wildcards."""
    include = [
        "regress/nightly/test_a/variant1",
        "regress/nightly/test_b/variant2",
        "regress/nightly/test_c/variant3",
    ]
    exclude = []

    solution = propose_solution(include, exclude)

    # Check that patterns have actual content (not just wildcards)
    for p in solution.patterns:
        text_without_wildcards = p.text.replace("*", "").replace("|", "").replace("&", "").strip()
        assert text_without_wildcards, f"Pattern '{p.text}' is all wildcards!"


def test_empty_string_include():
    """Empty string in include should not produce trivial patterns."""
    include = [""]
    exclude = []

    solution = propose_solution(include, exclude)

    # With empty string, tokenization produces no tokens
    # Should result in no solution or no patterns (not trivial '*')
    if solution.raw_expr != "FALSE" and solution.patterns:
        assert solution.raw_expr != "*"
        assert "*" not in [p.text for p in solution.patterns]
