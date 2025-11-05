#!/usr/bin/env python3
"""
Test patternforge integration with instance_list_compressor.

This test file evaluates whether patternforge.propose_solution() can be used
for pattern generation and compression of hierarchical instance names.

Adapted from globmatcher integration tests.
"""
from __future__ import annotations

import unittest

from patternforge.engine.solver import propose_solution


class TestPatternforgeIntegration(unittest.TestCase):
    """Test patternforge with real-world instance lists"""

    def test_simple_instance_list(self):
        """Test patternforge with simple instance list"""
        instance_list = [
            "pd_domain/moduleA/sub1/mem/i0",
            "pd_domain/moduleA/sub2/mem/i0",
            "pd_domain/moduleA/sub3/mem/i0",
        ]

        # Use patternforge with empty exclude list
        solution = propose_solution(instance_list, [], splitmethod="char")

        # Extract patterns from solution
        patterns = solution.patterns
        patterns = [pattern.text for pattern in patterns]

        print(f"\nInput instances: {len(instance_list)}")
        print(f"Generated patterns: {patterns}")
        print(f"Number of patterns: {len(patterns)}")
        print(f"Expression: {solution.expr}")
        print(f"Metrics: {solution.metrics}")

        # Verify we get reasonable compression
        self.assertLessEqual(len(patterns), len(instance_list))
        # Verify the solution covers all inputs
        self.assertEqual(solution.metrics["covered"], len(instance_list))
        self.assertEqual(solution.metrics["fp"], 0)
        self.assertEqual(solution.metrics["fn"], 0)

    def test_real_world_28_instances(self):
        """Test patternforge with real-world 28-instance list"""
        instance_list = [
            "pd_sio/asio/fabric/asio_dart/tag_ram/gen.mem/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedicache/fedictag/tag_scrf0/GenWays32A.pa42_32.ictag/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tlsi0/tdcd/asc_tdcddat/DcDataParity32.DcDataArrays8[0].dcDat8k/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tlsi0/tdcd/asc_tdcddat/DcDataParity32.DcDataArrays8[1].dcDat8k/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tlsi0/tdcd/asc_tdcddat/DcDataParity32.DcDataArrays8[2].dcDat8k/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tlsi0/tdcd/asc_tdcddat/DcDataParity32.DcDataArrays8[3].dcDat8k/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedicache/fedicdat/icdat_cmem/l1i.arr.mc[0]/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedicache/fedicdat/icdat_cmem/l1i.arr.mc[1]/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap_mbx_sio_wrapper/memory/gen.mem/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedif/fednfp1/nfp1ctl/NfpAhead.nfpahead/nfp_cmem/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedbr/fedbdp/fedbdparr0/BdpGenA[0].fedbdparr2bnk0/ogehl_table/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedbr/fedbdp/fedbdparr0/BdpGenA[1].fedbdparr2bnk0/ogehl_table/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/GenTcore[0].tcore/tfed/fedbr/fedbdp/fedbdparr0/BdpGenA[2].fedbdparr2bnk0/ogehl_table/arr.mc/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/cpm/dpb/dpc/dpccpm/gencore0.eccpm4/VALID_CPU.dpctrace/VALID_TRACE_RAM.SINGLE_SEG.traceram_01/traceRAM.per_segment[0].arr.mc[0]/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/cpm/dpb/dpc/dpccpm/gencore0.eccpm4/VALID_CPU.dpctrace/VALID_TRACE_RAM.SINGLE_SEG.traceram_01/traceRAM.per_segment[0].arr.mc[1]/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/cpm/dpb/dpc/dpccpm/gencore0.eccpm4/VALID_CPU.dpctrace/VALID_TRACE_RAM.SINGLE_SEG.traceram_23/traceRAM.per_segment[0].arr.mc[0]/i0",
            "pd_sio/asio/asio_dma_cpu/ascWrap_sio/ascWrap/ascAxiWrap/asc/cpm/dpb/dpc/dpccpm/gencore0.eccpm4/VALID_CPU.dpctrace/VALID_TRACE_RAM.SINGLE_SEG.traceram_23/traceRAM.per_segment[0].arr.mc[1]/i0",
            "pd_sio/asio/fabric/asio_dart/pa_ram/gen.mem/i0",
        ]

        exclude_words = [
            "pd_sio/asio/asio_spis/rx_mem/u0/i0",
            "pd_sio/asio/asio_spis/rx_mem/u1/i0",
            "pd_sio/asio/asio_spis/rx_mem/u2/i0",
            "pd_sio/asio/asio_spis/rx_mem/u3/i0",
            "pd_sio/asio/asio_spis/tx_mem/u0/i0",
            "pd_sio/asio/asio_spis/tx_mem/u1/i0",
            "pd_sio/asio/asio_spis/tx_mem/u2/i0",
            "pd_sio/asio/asio_spis/tx_mem/u3/i0",
            "pd_sio/asio/asio_uarts/rx_mem/u0/i0",
            "pd_sio/asio/asio_uarts/tx_mem/u0/i0",
        ]

        # Use patternforge with exclude list
        solution = propose_solution(
            instance_list, exclude_words, splitmethod="char"
        )

        # Extract patterns from solution
        patterns = solution.patterns
        patterns = [pattern.text for pattern in patterns]

        print(f"\nInput instances: {len(instance_list)}")
        print("Generated patterns:")
        for i, pattern in enumerate(sorted(patterns), 1):
            print(f"  {i}. {pattern}")
        print(f"Number of patterns: {len(patterns)}")
        print(f"Expression: {solution.expr}")
        print(f"Metrics: {solution.metrics}")

        # Verify we get good compression (should be much less than 28)
        self.assertLessEqual(len(patterns), 10)
        # Verify the solution provides good coverage (at least 80%)
        coverage_ratio = solution.metrics["covered"] / len(instance_list)
        self.assertGreaterEqual(coverage_ratio, 0.8)
        # Verify low false positives
        self.assertLessEqual(solution.metrics["fp"], len(exclude_words))

    def test_longest(self):
        """Test patternforge with very long instance paths"""
        instance_list = [
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[0].apcie_core_rc_link/apcie_core_rc_app/MMU_EN_1.apcie_core_rc_mmu/apcie_core_rc_mmu_dart_wrap/dart_pcie_tag_ram/gen.mem/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[1].apcie_core_rc_link/apcie_core_rc_app/MMU_EN_1.apcie_core_rc_mmu/apcie_core_rc_mmu_dart_wrap/dart_pcie_tag_ram/gen.mem/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[2].apcie_core_rc_link/apcie_core_rc_app/MMU_EN_1.apcie_core_rc_mmu/apcie_core_rc_mmu_dart_wrap/dart_pcie_tag_ram/gen.mem/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[0].apcie_core_rc_link/apcie_core_rc_app/MMU_EN_1.apcie_core_rc_mmu/apcie_core_rc_mmu_dart_wrap/dart_pcie_xcpn_ram/gen.mem/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[1].apcie_core_rc_link/apcie_core_rc_app/MMU_EN_1.apcie_core_rc_mmu/apcie_core_rc_mmu_dart_wrap/dart_pcie_xcpn_ram/gen.mem/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[2].apcie_core_rc_link/apcie_core_rc_app/MMU_EN_1.apcie_core_rc_mmu/apcie_core_rc_mmu_dart_wrap/dart_pcie_xcpn_ram/gen.mem/i0",
            "apcie_sys_gp/afv2_pcieAxi2Af/core/lioa/gen_LIOA.gen_lioa.lioa_pcie/ioa_inst/ioa_tor_inst/tor_command/SINGLE_PIPE.orig_cmd/gen_bank[0].nonempty_bank.gen_bank_create_new.ioa_array/beat[0].array_392x140.memory_wrapper_inst/wrap_memlogic_mem4_l1_c1/i0",
            "apcie_sys_gp/afv2_pcieAxi2Af/core/mst_llt/master_rd_wrap/gen_ena_read.master_rd/rd_bend/gen_fifoDefault.rsp_cmddata_fifo/cmd_fifo/gen_ramFifo.sync_fifo/fifo_memory/g.bank/g[0].l.stripe/g[0].l.mem/g.mem/i0",
            "apcie_sys_gp/afv2_pcieAxi2Af/core/slv_s1/slave/slave_wr_request_converter_0/rsp_cmddata_fifo/cmd_fifo/gen_ramFifo.sync_fifo/fifo_memory/g.bank/g[0].l.stripe/g[0].l.mem/g.mem/i0",
            "apcie_sys_gp/afv2_pcieAxi2Af/core/mst_llt/master_rd_wrap/gen_ena_read.master_rd/rd_bend/gen_fifoDefault.rsp_cmddata_fifo/data_fifo/gen_ramFifo.sync_fifo/fifo_memory/g.bank/g[0].l.stripe/g[0].l.mem/g.mem/i0",
        ]

        exclude_words = [
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[0].apcie_core_rc_link/pcie_rc_top/pcie_ltssm_dbg_wrap/apcie_ltssm_dbg/ltssm_debug_ram_mem/MEM_64x86.A_def.M_def.M_inst/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[1].apcie_core_rc_link/pcie_rc_top/pcie_ltssm_dbg_wrap/apcie_ltssm_dbg/ltssm_debug_ram_mem/MEM_64x86.A_def.M_def.M_inst/i0",
            "apcie_sys_gp/apcie_sys/apcie_core_rc_wrap/G_apcie_core.apcie_core/apcie_core_rc/links/links[2].apcie_core_rc_link/pcie_rc_top/pcie_ltssm_dbg_wrap/apcie_ltssm_dbg/ltssm_debug_ram_mem/MEM_64x86.A_def.M_def.M_inst/i0",
        ]

        # Use patternforge with exclude list (only showing first 10 instances for brevity)
        solution = propose_solution(
            instance_list, exclude_words, splitmethod="char"
        )

        # Extract patterns from solution
        patterns = solution.patterns
        patterns = [pattern.text for pattern in patterns]

        print(f"\nInput instances: {len(instance_list)}")
        print("Generated patterns:")
        for i, pattern in enumerate(sorted(patterns), 1):
            print(f"  {i}. {pattern}")
        print(f"Number of patterns: {len(patterns)}")
        print(f"Expression: {solution.expr}")
        print(f"Metrics: {solution.metrics}")

        # Verify we get compression
        self.assertLessEqual(len(patterns), len(instance_list))
        # Verify the solution provides reasonable coverage (at least 70%)
        coverage_ratio = solution.metrics["covered"] / len(instance_list)
        self.assertGreaterEqual(coverage_ratio, 0.7)
        # Verify low false positives
        self.assertLessEqual(solution.metrics["fp"], len(exclude_words))

    def test_multiple_distinct_groups(self):
        """Test patternforge with multiple distinct module types"""
        instance_list = [
            "pd_domain/moduleA/sub1/PATTERN_A/mem/i0",
            "pd_domain/moduleA/sub2/PATTERN_A/mem/i0",
            "pd_domain/moduleA/sub3/PATTERN_A/mem/i0",
            "pd_domain/moduleB/sub1/PATTERN_B/mem/i0",
            "pd_domain/moduleB/sub2/PATTERN_B/mem/i0",
            "pd_domain/moduleB/sub3/PATTERN_B/mem/i0",
            "pd_domain/moduleC/sub1/PATTERN_C/mem/i0",
            "pd_domain/moduleC/sub2/PATTERN_C/mem/i0",
            "pd_domain/moduleC/sub3/PATTERN_C/mem/i0",
        ]

        solution = propose_solution(instance_list, [], splitmethod="char")

        # Extract patterns from solution
        patterns = solution.patterns
        patterns = [pattern.text for pattern in patterns]

        print(f"\nInput instances: {len(instance_list)}")
        print("Generated patterns:")
        for i, pattern in enumerate(sorted(patterns), 1):
            print(f"  {i}. {pattern}")
        print(f"Number of patterns: {len(patterns)}")
        print(f"Expression: {solution.expr}")
        print(f"Metrics: {solution.metrics}")

        # Should compress to a small number of patterns
        self.assertLessEqual(len(patterns), 5)
        # Verify the solution covers all inputs
        self.assertEqual(solution.metrics["covered"], len(instance_list))
        self.assertEqual(solution.metrics["fp"], 0)

    def test_splitmethod_comparison(self):
        """Compare 'char' vs 'classchange' splitmethod"""
        instance_list = [
            "pd_sio/asio/asio_spis/rx_mem/u0/i0",
            "pd_sio/asio/asio_spis/rx_mem/u1/i0",
            "pd_sio/asio/asio_spis/tx_mem/u0/i0",
            "pd_sio/asio/asio_spis/tx_mem/u1/i0",
        ]

        solution_char = propose_solution(
            instance_list, [], splitmethod="char"
        )
        solution_classchange = propose_solution(
            instance_list, [], splitmethod="classchange"
        )

        # Extract patterns from solutions
        atoms_char = solution_char.patterns
        patterns_char = [pattern.text for pattern in atoms_char]

        atoms_classchange = solution_classchange.patterns
        patterns_classchange = [pattern.text for pattern in atoms_classchange]

        print(f"\nInput instances: {len(instance_list)}")
        print("\nPatterns with splitmethod='char':")
        for pattern in sorted(patterns_char):
            print(f"  {pattern}")
        print(f"Expression: {solution_char.expr}")

        print("\nPatterns with splitmethod='classchange':")
        for pattern in sorted(patterns_classchange):
            print(f"  {pattern}")
        print(f"Expression: {solution_classchange.expr}")

        # Both should provide good compression
        self.assertLessEqual(len(patterns_char), len(instance_list))
        self.assertLessEqual(len(patterns_classchange), len(instance_list))

        # Both should cover all inputs
        self.assertEqual(solution_char.metrics["covered"], len(instance_list))
        self.assertEqual(solution_classchange.metrics["covered"], len(instance_list))


if __name__ == "__main__":
    unittest.main(verbosity=2)
