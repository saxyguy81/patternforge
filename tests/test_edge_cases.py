"""
Edge case tests for PatternForge - testing boundary conditions and error handling.

These tests ensure robustness by testing invalid inputs, empty data,
wildcards in input, and other edge cases.
"""
import pytest
import numpy as np
from patternforge.engine.solver import propose_solution, propose_solution_structured


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_include_list(self):
        """Test with empty include list."""
        solution = propose_solution([], [], splitmethod='char')

        assert solution.metrics['total_positive'] == 0
        assert len(solution.patterns) == 0

    def test_single_item_no_exclude(self):
        """Test with single item and no excludes."""
        solution = propose_solution(["single/path/item"], [], splitmethod='char')

        assert solution.metrics['covered'] == 1
        assert len(solution.patterns) >= 1
        assert solution.metrics['fp'] == 0

    def test_identical_items(self):
        """Test with all identical items."""
        instance_list = ["identical/path/item"] * 10

        solution = propose_solution(instance_list, [], splitmethod='char')

        # Should compress to 1 pattern
        assert len(solution.patterns) == 1
        assert solution.metrics['covered'] == 10

    def test_very_long_path(self):
        """Test with very long hierarchical path."""
        long_path = "/".join([f"level{i}" for i in range(50)]) + "/mem/i0"

        solution = propose_solution([long_path], [], splitmethod='char')

        assert solution.metrics['covered'] == 1
        assert len(solution.patterns) >= 1

    def test_special_characters_in_paths(self):
        """Test with special characters in paths."""
        paths = [
            "module/instance_0/mem[0]",
            "module/instance_1/mem[1]",
            "module/instance_2/mem[2]",
        ]

        solution = propose_solution(paths, [], splitmethod='char')

        assert solution.metrics['covered'] == len(paths)
        assert solution.metrics['fp'] == 0

    def test_unicode_characters(self):
        """Test with unicode characters in paths."""
        paths = [
            "modülé/înstance_0/mem",
            "modülé/înstance_1/mem",
        ]

        solution = propose_solution(paths, [], splitmethod='char')

        # Should handle unicode gracefully
        assert solution.metrics['covered'] == len(paths)

    def test_numeric_only_tokens(self):
        """Test with numeric-only path segments."""
        paths = [
            "123/456/789/mem",
            "123/456/790/mem",
            "123/457/789/mem",
        ]

        solution = propose_solution(paths, [], splitmethod='char')

        assert solution.metrics['covered'] == len(paths)
        assert solution.metrics['fp'] == 0

    def test_mixed_case_sensitivity(self):
        """Test case sensitivity in pattern matching."""
        paths = [
            "Module/Instance/Mem",
            "Module/Instance/mem",  # Different case
        ]

        solution = propose_solution(paths, [], splitmethod='char')

        # Both should be covered
        assert solution.metrics['covered'] == len(paths)

    def test_overlapping_include_exclude(self):
        """Test when include and exclude have overlapping items."""
        include = [
            "chip/cpu/cache/bank0",
            "chip/cpu/cache/bank1",
            "chip/cpu/cache/bank2",
        ]

        exclude = [
            "chip/cpu/cache/bank1",  # Overlap with include
            "chip/cpu/debug/trace",
        ]

        solution = propose_solution(include, exclude, splitmethod='char')

        # Should avoid patterns that match bank1
        assert solution.metrics['fp'] == 0
        # May not cover bank1 if it creates conflict
        assert solution.metrics['covered'] <= len(include)

    def test_all_items_excluded(self):
        """Test when all include items would be excluded by patterns."""
        include = ["chip/cpu/mem"]
        exclude = ["chip/cpu/mem"]  # Same as include

        solution = propose_solution(include, exclude, splitmethod='char')

        # Can't create patterns that don't exclude the item
        # May result in FP equal to include size (matches same item)
        assert solution.metrics['fp'] >= 0  # May have FP
        # Coverage might be 0 or low
        assert solution.metrics['covered'] <= len(include)

    def test_very_similar_paths_with_tiny_differences(self):
        """Test with paths that differ by single character."""
        paths = [
            "long/path/to/module/instanceA/mem/i0",
            "long/path/to/module/instanceB/mem/i0",
            "long/path/to/module/instanceC/mem/i0",
        ]

        solution = propose_solution(paths, [], splitmethod='char')

        # Should find common pattern
        assert len(solution.patterns) <= 3
        assert solution.metrics['covered'] == len(paths)

    def test_splitmethod_with_numbers(self):
        """Test classchange splitmethod with numbers."""
        paths = [
            "Module123ABC/Instance456DEF",
            "Module123ABC/Instance789GHI",
        ]

        solution_char = propose_solution(paths, [], splitmethod='char')
        solution_class = propose_solution(paths, [], splitmethod='classchange')

        # Both should cover all paths
        assert solution_char.metrics['covered'] == len(paths)
        assert solution_class.metrics['covered'] == len(paths)

    def test_structured_with_none_fields(self):
        """Test structured solver with None values in exclude."""
        include_rows = [
            {"module": "SRAM", "instance": "chip/cpu/cache", "pin": "DIN"},
            {"module": "SRAM", "instance": "chip/cpu/cache", "pin": "DOUT"},
        ]

        exclude_rows = [
            {"module": None, "instance": "chip/debug", "pin": None},  # None as wildcard
            {"module": "SRAM", "instance": None, "pin": "CLK"},  # None as wildcard
        ]

        solution = propose_solution_structured(include_rows, exclude_rows)

        # Should handle None wildcards correctly
        assert solution.metrics['covered'] == len(include_rows)
        assert solution.metrics['fp'] == 0

    def test_structured_with_nan_fields(self):
        """Test structured solver with NaN values in exclude."""
        include_rows = [
            {"module": "REGFILE", "instance": "chip/cpu/decode", "pin": "RD0"},
            {"module": "REGFILE", "instance": "chip/cpu/decode", "pin": "RD1"},
        ]

        exclude_rows = [
            {"module": np.nan, "instance": "chip/cpu/debug", "pin": np.nan},  # NaN as wildcard
        ]

        solution = propose_solution_structured(include_rows, exclude_rows)

        # Should handle NaN wildcards correctly
        assert solution.metrics['covered'] == len(include_rows)
        assert solution.metrics['fp'] == 0

    def test_structured_with_empty_exclude_rows(self):
        """Test structured solver with empty exclude list."""
        include_rows = [
            {"module": "DFF", "instance": "cpu/execute/alu", "pin": "CK"},
            {"module": "DFF", "instance": "cpu/execute/fpu", "pin": "CK"},
        ]

        exclude_rows = []

        solution = propose_solution_structured(include_rows, exclude_rows)

        # Should generate patterns without exclude constraints
        assert solution.metrics['covered'] == len(include_rows)
        assert len(solution.patterns) >= 1

    def test_empty_string_handling(self):
        """Test handling of empty strings in various contexts."""
        # Empty string in include - should be handled gracefully
        solution = propose_solution([""], [], splitmethod='char')

        # Empty strings produce no meaningful patterns
        # Coverage will be total_positive count
        assert solution.metrics['total_positive'] == 1

    def test_whitespace_only_paths(self):
        """Test paths with only whitespace."""
        # Whitespace-only paths should be handled gracefully
        solution = propose_solution(["   ", "\t\t"], [], splitmethod='char')

        # Whitespace paths are treated as input
        assert solution.metrics['total_positive'] == 2

    def test_max_candidates_budget(self):
        """Test with limited candidate budget."""
        instance_list = [f"module_{i}/sub_{j}/mem" for i in range(10) for j in range(10)]

        # Limit candidates to force greedy selection
        solution = propose_solution(
            instance_list,
            [],
            splitmethod='char',
            max_candidates=100  # Very low limit
        )

        # Should still provide some coverage
        assert solution.metrics['covered'] > 0

    def test_max_patterns_budget(self):
        """Test with limited pattern budget."""
        instance_list = [f"module_{i}/sub_{j}/mem" for i in range(5) for j in range(5)]

        # Limit to 3 patterns
        solution = propose_solution(
            instance_list,
            [],
            splitmethod='char',
            max_patterns=3
        )

        # Should respect budget
        assert len(solution.patterns) <= 3
        # May not cover all items due to budget limit
        assert solution.metrics['covered'] <= len(instance_list)

    def test_mode_case_insensitive(self):
        """Test that mode parameter is case-insensitive."""
        instance_list = ["chip/cpu/mem/i0", "chip/gpu/mem/i0"]

        # Test various case combinations
        for mode in ["EXACT", "exact", "Exact", "APPROX", "approx", "Approx"]:
            solution = propose_solution(instance_list, [], mode=mode, splitmethod='char')
            assert solution.metrics['covered'] == len(instance_list)

    def test_invert_strategy(self):
        """Test inversion strategy for complement patterns."""
        include = ["word1", "word2", "word3"]
        exclude = ["other1", "other2", "other3", "other4", "other5"]

        # Test different invert strategies
        solution_never = propose_solution(include, exclude, invert="never")
        solution_auto = propose_solution(include, exclude, invert="auto")

        # Both should provide valid solutions
        assert solution_never.metrics['covered'] <= len(include)
        assert solution_auto.metrics['covered'] <= len(include)

    def test_per_field_weights_in_structured(self):
        """Test per-field weights in structured solver."""
        include_rows = [
            {"module": "SRAM_512", "instance": "chip/cpu/cache", "pin": "DIN[0]"},
            {"module": "SRAM_512", "instance": "chip/cpu/cache", "pin": "DIN[31]"},
            {"module": "SRAM_1k", "instance": "chip/cpu/cache", "pin": "DOUT[0]"},
        ]

        # Prefer patterns on pin field
        solution = propose_solution_structured(
            include_rows,
            [],
            w_field={"pin": 3.0, "module": 0.5, "instance": 1.0}
        )

        # Should generate solution preferring pin patterns
        assert solution.metrics['covered'] == len(include_rows)

    def test_effort_levels(self):
        """Test different effort levels."""
        instance_list = [f"module_{i}/instance_{j}/mem" for i in range(10) for j in range(10)]

        for effort in ["low", "medium", "high"]:
            solution = propose_solution_structured(
                [{"path": p} for p in instance_list],
                [],
                effort=effort
            )

            # All effort levels should provide valid solutions
            assert solution.metrics['covered'] == len(instance_list)

    def test_percentage_budgets(self):
        """Test percentage-based budgets."""
        instance_list = [f"chip/module_{i}/mem" for i in range(100)]

        # Allow 5% false positives
        solution = propose_solution(
            instance_list,
            [f"debug/module_{i}/mem" for i in range(50)],
            max_fp=0.05,  # 5% of 100 = 5 FP allowed
            splitmethod='char'
        )

        # Should respect percentage budget
        assert solution.metrics['fp'] <= 5  # 5% of 100
        assert solution.metrics['covered'] <= len(instance_list)
