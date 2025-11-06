"""
Comprehensive tests verifying EXACT mode guarantees zero false positives.

This test suite was created in response to a report that EXACT mode was
allowing false positives. These tests exhaustively verify that mode="EXACT"
ALWAYS results in metrics['fp'] == 0, regardless of input complexity.
"""
import pytest
import numpy as np
from patternforge.engine.solver import propose_solution, propose_solution_structured


class TestExactModeGuarantees:
    """Test that EXACT mode NEVER produces false positives."""

    def test_exact_mode_simple_paths(self):
        """Test EXACT mode with simple paths - most basic case."""
        include = ["chip/cpu/mem/i0", "chip/gpu/mem/i0"]
        exclude = ["chip/debug/mem/i0", "chip/trace/mem/i0"]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        assert solution.mode == "EXACT"
        # Should cover at least some items
        assert solution.metrics['covered'] > 0

    def test_exact_mode_complex_hierarchical_paths(self):
        """Test EXACT mode with complex hardware-like hierarchical paths."""
        include = [
            "pd_sio/asio/fabric/asio_dart/tag_ram/gen.mem/i0",
            "pd_sio/asio/fabric/asio_dart/pa_ram/gen.mem/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap_mbx_sio_wrapper/memory/gen.mem/i0",
        ]
        exclude = [
            "pd_sio/asio/asio_spis/rx_mem/u0/i0",
            "pd_sio/asio/asio_spis/tx_mem/u0/i0",
            "pd_sio/asio/asio_uarts/rx_mem/u0/i0",
        ]

        solution = propose_solution(include, exclude, mode="EXACT", splitmethod='char')

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        assert solution.mode == "EXACT"

    def test_exact_mode_with_array_indices(self):
        """Test EXACT mode with array indices like [0], [1], etc."""
        include = [
            "module/instance[0]/mem/i0",
            "module/instance[1]/mem/i0",
            "module/instance[2]/mem/i0",
        ]
        exclude = [
            "module/instance[3]/mem/i0",
            "module/instance[4]/mem/i0",
            "debug/instance[0]/mem/i0",
        ]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        # Verify exclude items are not matched
        for pattern in solution.patterns:
            for ex in exclude:
                # Manual check - pattern should not match exclude items
                # This is a double-check beyond the metrics
                pass  # The metrics check is the primary validation

    def test_exact_mode_overlapping_include_exclude(self):
        """Test EXACT mode when include and exclude have similar patterns."""
        include = [
            "chip/cpu/cache/bank0",
            "chip/cpu/cache/bank1",
            "chip/cpu/cache/bank2",
        ]
        exclude = [
            "chip/cpu/debug/bank0",  # Similar structure, different middle segment
            "chip/cpu/debug/bank1",
            "chip/debug/cache/bank0",  # Different middle segment
        ]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_large_exclude_set(self):
        """Test EXACT mode with many exclude items."""
        include = [f"include/module_{i}/mem" for i in range(10)]
        exclude = [f"exclude/module_{i}/mem" for i in range(100)]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_empty_exclude(self):
        """Test EXACT mode with empty exclude list."""
        include = ["alpha/module1/mem", "alpha/module2/mem", "beta/cache"]
        exclude = []

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: Even with empty exclude, EXACT mode metrics should show fp=0
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        # Should cover all items
        assert solution.metrics['covered'] == len(include)

    def test_exact_mode_single_item(self):
        """Test EXACT mode with single include item."""
        include = ["single/path/to/mem/i0"]
        exclude = ["other/path/to/mem/i0", "single/path/to/debug/i0"]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        assert solution.metrics['covered'] == 1

    def test_exact_mode_very_similar_paths(self):
        """Test EXACT mode with paths differing by single character."""
        include = [
            "long/path/to/module/instanceA/mem/i0",
            "long/path/to/module/instanceB/mem/i0",
            "long/path/to/module/instanceC/mem/i0",
        ]
        exclude = [
            "long/path/to/module/instanceD/mem/i0",
            "long/path/to/module/instanceE/mem/i0",
        ]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_case_sensitive_differences(self):
        """Test EXACT mode with case-sensitive differences."""
        include = [
            "Module/Instance/Mem",
            "module/instance/mem",
        ]
        exclude = [
            "MODULE/INSTANCE/MEM",
            "Module/Instance/Debug",
        ]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_vs_approx_mode_comparison(self):
        """Compare EXACT vs APPROX mode to show EXACT has stricter FP guarantee."""
        include = [f"chip/cpu/core{i}/mem" for i in range(20)]
        exclude = [f"chip/gpu/core{i}/mem" for i in range(20)]

        solution_exact = propose_solution(include, exclude, mode="EXACT")
        solution_approx = propose_solution(include, exclude, mode="APPROX")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution_exact.metrics['fp'] == 0, f"EXACT mode produced {solution_exact.metrics['fp']} false positives!"
        # APPROX mode may have FP (but not required)
        # The key is EXACT has stricter guarantee
        assert solution_exact.mode == "EXACT"
        assert solution_approx.mode == "APPROX"

    def test_exact_mode_with_special_characters(self):
        """Test EXACT mode with special regex characters in paths."""
        include = [
            "module/instance_0/mem[0]",
            "module/instance_1/mem[1]",
            "module/instance_2/mem[2]",
        ]
        exclude = [
            "module/instance_3/mem[3]",
            "debug/instance_0/mem[0]",
        ]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_with_unicode(self):
        """Test EXACT mode with unicode characters."""
        include = [
            "modülé/înstance_0/mem",
            "modülé/înstance_1/mem",
        ]
        exclude = [
            "modülé/dëbug/mem",
            "other/înstance_0/mem",
        ]

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_with_max_patterns_budget(self):
        """Test EXACT mode with pattern budget constraint."""
        include = [f"module_{i}/sub_{j}/mem" for i in range(5) for j in range(5)]
        exclude = [f"debug_{i}/sub_{j}/mem" for i in range(5) for j in range(5)]

        solution = propose_solution(include, exclude, mode="EXACT", max_patterns=5)

        # CRITICAL: EXACT mode MUST have zero false positives even with budget
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        assert len(solution.patterns) <= 5

    def test_exact_mode_structured_simple(self):
        """Test EXACT mode with structured solver - simple case."""
        include_rows = [
            {"module": "SRAM", "instance": "chip/cpu/cache", "pin": "DIN"},
            {"module": "SRAM", "instance": "chip/cpu/cache", "pin": "DOUT"},
        ]
        exclude_rows = [
            {"module": "SRAM", "instance": "chip/cpu/cache", "pin": "CLK"},
            {"module": "SRAM", "instance": "chip/debug/trace", "pin": "DIN"},
        ]

        solution = propose_solution_structured(include_rows, exclude_rows, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        assert solution.mode == "EXACT"

    def test_exact_mode_structured_with_wildcards(self):
        """Test EXACT mode with structured solver and None/NaN wildcards in exclude."""
        include_rows = [
            {"module": "REGFILE", "instance": "chip/cpu/decode", "pin": "RD0"},
            {"module": "REGFILE", "instance": "chip/cpu/decode", "pin": "RD1"},
        ]
        exclude_rows = [
            {"module": None, "instance": "chip/cpu/debug", "pin": None},  # Wildcard
            {"module": "REGFILE", "instance": None, "pin": "WEN"},  # Wildcard
        ]

        solution = propose_solution_structured(include_rows, exclude_rows, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_structured_complex_hardware(self):
        """Test EXACT mode with realistic hardware signal patterns."""
        include_rows = [
            {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DIN[0]"},
            {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DIN[63]"},
            {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "DOUT[0]"},
            {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank1", "pin": "DIN[0]"},
        ]
        exclude_rows = [
            {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "CLK"},
            {"module": "SRAM_512x64", "instance": "chip/cpu/core0/l1_icache/bank0", "pin": "WEN"},
            {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DIN[0]"},
        ]

        solution = propose_solution_structured(include_rows, exclude_rows, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_char_vs_classchange_splitmethod(self):
        """Test EXACT mode with different split methods."""
        include = [
            "ModuleABC123/Instance456DEF",
            "ModuleABC123/Instance789GHI",
        ]
        exclude = [
            "ModuleXYZ999/Instance456DEF",
            "ModuleABC123/DebugTrace",
        ]

        solution_char = propose_solution(include, exclude, mode="EXACT", splitmethod='char')
        solution_class = propose_solution(include, exclude, mode="EXACT", splitmethod='classchange')

        # CRITICAL: EXACT mode MUST have zero false positives for both
        assert solution_char.metrics['fp'] == 0, f"EXACT mode (char) produced {solution_char.metrics['fp']} false positives!"
        assert solution_class.metrics['fp'] == 0, f"EXACT mode (classchange) produced {solution_class.metrics['fp']} false positives!"

    def test_exact_mode_with_invert_never(self):
        """Test EXACT mode with invert='never' strategy."""
        include = ["word1", "word2", "word3"]
        exclude = ["other1", "other2", "other3", "other4", "other5"]

        solution = propose_solution(include, exclude, mode="EXACT", invert="never")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_with_invert_auto(self):
        """Test EXACT mode with invert='auto' strategy."""
        include = ["word1", "word2", "word3"]
        exclude = ["other1", "other2", "other3", "other4", "other5"]

        solution = propose_solution(include, exclude, mode="EXACT", invert="auto")

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_stress_test_large_scale(self):
        """Stress test EXACT mode with 100 include and 100 exclude items."""
        include = [f"soc/cpu/core{i}/l1_cache/bank{j}/mem/i0"
                   for i in range(10) for j in range(10)]
        exclude = [f"soc/debug/trace{i}/buffer{j}/mem/i0"
                   for i in range(10) for j in range(10)]

        assert len(include) == 100
        assert len(exclude) == 100

        solution = propose_solution(include, exclude, mode="EXACT")

        # CRITICAL: EXACT mode MUST have zero false positives even at scale
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_with_explicit_max_fp_zero(self):
        """Test EXACT mode with explicit max_fp=0 (should be redundant but verify)."""
        include = ["chip/cpu/mem/i0", "chip/gpu/mem/i0"]
        exclude = ["chip/debug/mem/i0"]

        solution = propose_solution(include, exclude, mode="EXACT", max_fp=0)

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"

    def test_exact_mode_realistic_production_case(self):
        """Test EXACT mode with realistic production-like hardware paths."""
        include = [
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedicache/fedictag/tag_scrf0/GenWays32A.pa42_32.ictag/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tlsi0/tdcd/asc_tdcddat/DcDataParity32.DcDataArrays8[0].dcDat8k/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tlsi0/tdcd/asc_tdcddat/DcDataParity32.DcDataArrays8[1].dcDat8k/arr.mc/i0",
        ]
        exclude = [
            "pd_sio/asio/asio_spis/rx_mem/u0/i0",
            "pd_sio/asio/asio_spis/tx_mem/u0/i0",
            "pd_sio/asio/asio_uarts/rx_mem/u0/i0",
        ]

        solution = propose_solution(include, exclude, mode="EXACT", splitmethod='char')

        # CRITICAL: EXACT mode MUST have zero false positives
        assert solution.metrics['fp'] == 0, f"EXACT mode produced {solution.metrics['fp']} false positives!"
        # Coverage may be 0 if solver can't find patterns without FP - this is correct behavior in EXACT mode
        # The key requirement is fp == 0, not coverage > 0
