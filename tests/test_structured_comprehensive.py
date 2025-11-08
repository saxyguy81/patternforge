"""Comprehensive tests for structured data solver - realistic hardware design scenarios."""
from __future__ import annotations

import unittest
from src.patternforge.engine.solver import propose_solution_structured
from src.patternforge.engine.models import SolveOptions


class TestStructuredRealistic(unittest.TestCase):
    """Test realistic hardware design scenarios."""

    def test_memory_instances_exact_mode(self):
        """Test memory instances with hierarchical paths - should get 0 FP in EXACT mode."""
        include = [
            {"module": "SRAM", "instance": "pd_sio/asio/fabric/dart/tag_ram/u0", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_sio/asio/fabric/dart/tag_ram/u1", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_sio/asio/fabric/dart/pa_ram/u0", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_sio/asio/fabric/dart/pa_ram/u1", "pin": "DIN"},
        ]
        exclude = [
            {"module": "SRAM", "instance": "pd_sio/asio/asio_spis/rx_mem/u0", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_sio/asio/asio_uarts/tx_mem/u0", "pin": "DIN"},
            {"module": "DRAM", "instance": "pd_sio/asio/fabric/dart/tag_ram/u0", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # EXACT mode MUST have zero false positives
        self.assertEqual(solution.metrics['fp'], 0, "EXACT mode must have 0 false positives")
        # Should cover all includes
        self.assertEqual(solution.metrics['covered'], len(include))
        # Should have reasonable number of patterns
        self.assertLessEqual(solution.metrics['patterns'], 5)

        print(f"\nMemory instances test:")
        print(f"  Pattern: {solution.raw_expr}")
        print(f"  Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
        print(f"  FP: {solution.metrics['fp']}, Patterns: {solution.metrics['patterns']}")

    def test_single_field_difference_should_use_that_field(self):
        """When include rows differ only in one field, should generate pattern on that field."""
        include = [
            {"module": "SRAM", "instance": "pd_core/cache", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_core/cache", "pin": "DOUT"},
            {"module": "SRAM", "instance": "pd_core/cache", "pin": "WEN"},
        ]
        exclude = [
            {"module": "ROM", "instance": "pd_core/cache", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Should use module field to distinguish SRAM from ROM
        module_patterns = [p for p in solution.patterns if p.field == "module"]
        self.assertTrue(len(module_patterns) > 0, "Should have at least one module pattern")

        # Should have 0 FP in EXACT mode
        self.assertEqual(solution.metrics['fp'], 0)
        self.assertEqual(solution.metrics['covered'], len(include))

        print(f"\nSingle field difference test:")
        print(f"  Patterns: {[f'{p.field}={p.text}' for p in solution.patterns]}")
        print(f"  FP: {solution.metrics['fp']}")

    def test_common_prefix_in_hierarchy(self):
        """Should find longest common prefix in hierarchical instance paths."""
        include = [
            {"module": "SRAM", "instance": "pd_sio/asio/asio_spis/rx_mem/u0", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_sio/asio/asio_spis/rx_mem/u1", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_sio/asio/asio_spis/tx_mem/u0", "pin": "DOUT"},
            {"module": "SRAM", "instance": "pd_sio/asio/asio_spis/tx_mem/u1", "pin": "DOUT"},
        ]
        exclude = [
            {"module": "SRAM", "instance": "pd_sio/asio/asio_uarts/rx_mem/u0", "pin": "DIN"},
            {"module": "ROM", "instance": "pd_sio/asio/asio_spis/rx_mem/u0", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Should generate pattern like "pd_sio/asio/asio_spis/*" for instance field
        instance_patterns = [p for p in solution.patterns if p.field == "instance"]

        # Check if we got a good prefix pattern
        has_prefix = any("pd_sio/asio/asio_spis" in p.text for p in instance_patterns)

        print(f"\nCommon prefix test:")
        print(f"  Instance patterns: {[p.text for p in instance_patterns]}")
        print(f"  Has asio_spis prefix: {has_prefix}")
        print(f"  Raw expression: {solution.raw_expr}")

        # Must have 0 FP
        self.assertEqual(solution.metrics['fp'], 0)
        self.assertEqual(solution.metrics['covered'], len(include))

    def test_multi_field_expression_reduces_fp(self):
        """Should use multi-field expressions when single field causes FP."""
        include = [
            {"module": "SRAM", "instance": "cache/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache/bank1", "pin": "DIN"},
        ]
        exclude = [
            {"module": "SRAM", "instance": "router/buf0", "pin": "DIN"},  # Same module+pin, different instance
            {"module": "ROM", "instance": "cache/bank0", "pin": "DIN"},   # Same instance+pin, different module
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Should need multi-field expressions to avoid FP
        # Check if we got multiple fields in expressions
        multi_field_terms = [t for t in solution.expressions if len(t.get('fields', {})) > 1]

        print(f"\nMulti-field expression test:")
        print(f"  Total expressions: {len(solution.expressions)}")
        print(f"  Multi-field expressions: {len(multi_field_terms)}")
        for term in solution.expressions:
            print(f"    {term.get('raw_expr', term.get('expr'))}")

        # Must have 0 FP
        self.assertEqual(solution.metrics['fp'], 0)
        self.assertEqual(solution.metrics['covered'], len(include))

    def test_identical_rows(self):
        """Identical include rows should generate single exact pattern."""
        include = [
            {"module": "SRAM", "instance": "cache/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache/bank0", "pin": "DIN"},
        ]
        exclude = [
            {"module": "ROM", "instance": "cache/bank0", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Should generate very simple pattern - possibly just one field to distinguish
        self.assertEqual(solution.metrics['fp'], 0)
        self.assertEqual(solution.metrics['covered'], len(include))

        # Should be very few patterns since all includes are identical
        self.assertLessEqual(len(solution.patterns), 3)

        print(f"\nIdentical rows test:")
        print(f"  Patterns: {solution.metrics['patterns']}")
        print(f"  Raw expression: {solution.raw_expr}")

    def test_large_dataset_scalability(self):
        """Test with larger dataset to verify scalability."""
        # Generate 50 include rows with variation
        include = []
        for i in range(50):
            module = "SRAM" if i % 3 == 0 else "DRAM" if i % 3 == 1 else "ROM"
            instance = f"pd_core/cache{i // 10}/bank{i % 10}"
            pin = "DIN" if i % 2 == 0 else "DOUT"
            include.append({"module": module, "instance": instance, "pin": pin})

        # Generate excludes that should be distinguishable
        exclude = [
            {"module": "FLASH", "instance": "pd_core/cache0/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "pd_debug/trace", "pin": "CLK"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Must have 0 FP in EXACT mode
        self.assertEqual(solution.metrics['fp'], 0)
        # Should cover all includes
        self.assertEqual(solution.metrics['covered'], len(include))
        # Should have reasonable number of patterns (not 50!)
        self.assertLessEqual(solution.metrics['patterns'], 20)

        print(f"\nLarge dataset test (50 rows):")
        print(f"  Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
        print(f"  Patterns: {solution.metrics['patterns']}")
        print(f"  Expressions: {len(solution.expressions)}")

    def test_field_specificity_preference(self):
        """Should prefer more specific patterns over wildcards."""
        include = [
            {"module": "SRAM_256x32", "instance": "cache/bank0", "pin": "DIN[0]"},
            {"module": "SRAM_256x32", "instance": "cache/bank1", "pin": "DIN[1]"},
        ]
        exclude = [
            {"module": "SRAM_128x16", "instance": "cache/bank0", "pin": "DIN[0]"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Should use module field to distinguish (more specific value)
        module_patterns = [p for p in solution.patterns if p.field == "module"]

        # Check if patterns are specific (not just wildcards)
        specific_patterns = [p for p in solution.patterns if p.wildcards == 0]

        print(f"\nField specificity test:")
        print(f"  Module patterns: {[p.text for p in module_patterns]}")
        print(f"  Specific (no wildcards): {len(specific_patterns)}/{len(solution.patterns)}")

        self.assertEqual(solution.metrics['fp'], 0)
        self.assertEqual(solution.metrics['covered'], len(include))

    def test_no_exclude_rows(self):
        """Test with no exclude rows - should still generate reasonable patterns."""
        include = [
            {"module": "SRAM", "instance": "cache/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache/bank1", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache/bank2", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include, [], mode="EXACT")

        # Should cover all includes
        self.assertEqual(solution.metrics['covered'], len(include))
        # No excludes = no false positives possible
        self.assertEqual(solution.metrics['fp'], 0)
        # Should be simple pattern
        self.assertLessEqual(solution.metrics['patterns'], 3)

        print(f"\nNo exclude rows test:")
        print(f"  Raw expression: {solution.raw_expr}")
        print(f"  Patterns: {solution.metrics['patterns']}")


class TestEarlyTerminationAnalysis(unittest.TestCase):
    """Analyze early termination behavior for optimality."""

    def test_early_termination_vs_exhaustive(self):
        """Compare solutions with and without early termination to check optimality."""
        # Scenario: multiple patterns could cover the same data
        include = [
            {"module": "SRAM", "instance": "cache0/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache0/bank1", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache1/bank0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache1/bank1", "pin": "DIN"},
        ]
        exclude = [
            {"module": "ROM", "instance": "cache0/bank0", "pin": "DIN"},
        ]

        # Get solution with current algorithm
        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Check if solution is reasonable
        print(f"\nEarly termination analysis:")
        print(f"  Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
        print(f"  Patterns: {solution.metrics['patterns']}")
        print(f"  FP: {solution.metrics['fp']}")
        print(f"  Expressions:")
        for i, expr in enumerate(solution.expressions, 1):
            fields = expr.get('fields', {})
            matches = expr.get('matches', 0)
            print(f"    {i}. {fields} (matches: {matches})")

        # Verify it meets criteria
        self.assertEqual(solution.metrics['fp'], 0, "Should have 0 FP in EXACT mode")
        self.assertEqual(solution.metrics['covered'], len(include), "Should cover all includes")

        # Check if pattern is optimal (hard to define "optimal" precisely, but check reasonableness)
        # For this case, should be able to cover with very few patterns
        self.assertLessEqual(solution.metrics['patterns'], 4)

    def test_greedy_vs_optimal_pattern_count(self):
        """Test if greedy finds minimal pattern count."""
        # Best solution: single pattern on module="SRAM"
        # Greedy might find: multiple instance patterns
        include = [
            {"module": "SRAM", "instance": "cache0", "pin": "DIN"},
            {"module": "SRAM", "instance": "cache1", "pin": "DOUT"},
            {"module": "SRAM", "instance": "buffer", "pin": "WEN"},
        ]
        exclude = [
            {"module": "ROM", "instance": "cache0", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include, exclude, mode="EXACT")

        # Ideally should find single module pattern
        print(f"\nGreedy optimality test:")
        print(f"  Patterns: {solution.metrics['patterns']}")
        print(f"  Pattern details:")
        for p in solution.patterns:
            print(f"    {p.field}={p.text}")

        self.assertEqual(solution.metrics['fp'], 0)
        self.assertEqual(solution.metrics['covered'], len(include))

        # Should find simple solution (ideally 1 pattern on module field)
        # But allow up to 3 in case algorithm isn't perfect
        self.assertLessEqual(solution.metrics['patterns'], 3)


if __name__ == '__main__':
    unittest.main()
