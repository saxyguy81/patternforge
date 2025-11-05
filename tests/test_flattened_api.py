"""Test the flattened kwargs API for propose_solution"""
from patternforge.engine.solver import propose_solution


def test_basic_usage():
    """Test basic usage with defaults"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
    exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

    solution = propose_solution(include, exclude)
    assert solution.expr is not None
    assert len(solution.patterns) > 0


def test_flattened_budgets():
    """Test flattened budget kwargs"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
    exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

    solution = propose_solution(include, exclude, max_patterns=3, max_fp=0)
    assert len(solution.patterns) <= 3
    assert solution.metrics['fp'] == 0


def test_flattened_weights():
    """Test flattened weight kwargs"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
    exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

    solution = propose_solution(include, exclude, w_fp=2.0, w_fn=1.0, w_pattern=0.1)
    assert solution.expr is not None
    assert len(solution.patterns) > 0


def test_mixed_kwargs():
    """Test mixed budget and weight kwargs"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
    exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

    solution = propose_solution(include, exclude,
        max_patterns=5,
        max_fp=0,
        w_fp=2.0,
        w_fn=1.0
    )
    assert len(solution.patterns) <= 5
    assert solution.metrics['fp'] == 0


def test_mode_with_kwargs():
    """Test string mode + budget kwargs"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
    exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

    solution = propose_solution(include, exclude,
        mode="EXACT",
        max_patterns=3
    )
    assert solution.mode == "EXACT"
    assert len(solution.patterns) <= 3


def test_all_parameter_types():
    """Test multiple parameter types"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
    exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

    solution = propose_solution(include, exclude,
        mode="APPROX",
        effort="high",
        max_patterns=4,
        max_fp=0,
        w_fp=2.0,
        w_pattern=0.05,
        allowed_patterns=["prefix", "suffix", "substring"]
    )
    assert solution.mode == "APPROX"
    assert len(solution.patterns) <= 4
    assert solution.metrics['fp'] == 0


def test_string_mode_case_insensitive():
    """Test string mode is case insensitive"""
    include = ["alpha/module1/mem/i0", "alpha/module2/io/i1"]
    exclude = ["gamma/module1/mem/i0"]

    # All these should work
    solution1 = propose_solution(include, exclude, mode="exact")
    solution2 = propose_solution(include, exclude, mode="EXACT")
    solution3 = propose_solution(include, exclude, mode="Exact")

    assert solution1.mode == "EXACT"
    assert solution2.mode == "EXACT"
    assert solution3.mode == "EXACT"


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/site/mesa/org-seg-projects-komodo-mesa-controlled_c04-fe-soc-users-smhanan-scratch1/misc/patternforge/src")

    print("=" * 70)
    print("Testing Flattened API")
    print("=" * 70)

    test_basic_usage()
    print("✓ TEST 1: Basic usage with defaults")

    test_flattened_budgets()
    print("✓ TEST 2: Flattened budget kwargs")

    test_flattened_weights()
    print("✓ TEST 3: Flattened weight kwargs")

    test_mixed_kwargs()
    print("✓ TEST 4: Mixed budget and weight kwargs")

    test_mode_with_kwargs()
    print("✓ TEST 5: String mode + budget kwargs")

    test_all_parameter_types()
    print("✓ TEST 6: Multiple parameter types")

    test_string_mode_case_insensitive()
    print("✓ TEST 7: String mode case insensitive")

    print("\n" + "=" * 70)
    print("✅ All flattened API tests passed!")
    print("=" * 70)
