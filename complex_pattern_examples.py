#!/usr/bin/env python3
"""
Complex Pattern Examples: Anchored + Multi-Segment Combinations

Demonstrates the solver's ability to combine:
- PREFIX patterns (token/*)
- SUFFIX patterns (*/token)
- MULTI-SEGMENT patterns (*a*b*c*)
"""
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution

def print_example(title, instance_list, exclude_list):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    solution = propose_solution(instance_list, exclude_list, SolveOptions(splitmethod="classchange"))

    print(f"\n📥 INPUT:")
    print(f"  ✓ Include: {len(instance_list)} instances")
    for inst in instance_list:
        print(f"      {inst}")

    if exclude_list:
        print(f"\n  ✗ Exclude: {len(exclude_list)} instances")
        for inst in exclude_list:
            print(f"      {inst}")

    print(f"\n📤 OUTPUT:")
    print(f"  Expression: {solution.get('raw_expr', 'N/A')}")
    print(f"\n  📊 Metrics:")
    print(f"    Coverage:      {solution['metrics']['covered']}/{solution['metrics']['total_positive']} ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
    print(f"    False Pos:     {solution['metrics']['fp']} ✅")
    print(f"    Patterns:      {solution['metrics']['atoms']}")
    print(f"    Wildcards:     {solution['metrics']['wildcards']}")

    atoms = solution.get('atoms', [])
    print(f"\n  🎯 Pattern Analysis ({len(atoms)} patterns):")
    for i, atom in enumerate(atoms, 1):
        print(f"\n    [{i}] {atom['text']}")

        # Determine pattern type and characteristics
        if atom['kind'] == 'prefix':
            print(f"        Type: PREFIX (anchored at START)")
            print(f"        ⚓ Matches paths beginning with: {atom['text'].replace('/*', '')}")
        elif atom['kind'] == 'suffix':
            print(f"        Type: SUFFIX (anchored at END)")
            print(f"        ⚓ Matches paths ending with: {atom['text'].replace('*/', '')}")
        elif atom['kind'] == 'multi':
            segments = [s for s in atom['text'].split('*') if s]
            print(f"        Type: MULTI-SEGMENT (ordered keywords)")
            print(f"        🔗 Requires: {' → '.join(repr(s) for s in segments)}")
            print(f"        ℹ️  All {len(segments)} segments must appear in order")
        elif atom['kind'] == 'substring':
            print(f"        Type: SUBSTRING (flexible)")
            print(f"        🔍 Matches anywhere containing: {atom['text'].strip('*')}")
        else:
            print(f"        Type: EXACT")

        print(f"        Wildcards: {atom['wildcards']}")
        print(f"        Matches: {atom['tp']} instances, FP: {atom['fp']}")

print("=" * 80)
print("COMPLEX PATTERN EXAMPLES: Anchored + Multi-Segment Combinations")
print("=" * 80)
print("\nThese examples demonstrate sophisticated pattern generation combining:")
print("  • PREFIX patterns (prefix/*) - anchored at start")
print("  • SUFFIX patterns (*/suffix) - anchored at end")
print("  • MULTI-SEGMENT patterns (*a*b*c*) - ordered keywords")
print("=" * 80)

# Example 1: Real SoC with memory hierarchies
print_example(
    "EXAMPLE 1: SoC Memory Hierarchy - Multi-Segment Avoids False Positives",
    instance_list=[
        # CPU L1 caches - instruction and data
        "soc/cpu_cluster/core0/l1_cache/instruction/tag_array/sram",
        "soc/cpu_cluster/core0/l1_cache/instruction/data_array/sram",
        "soc/cpu_cluster/core0/l1_cache/data/tag_array/sram",
        "soc/cpu_cluster/core0/l1_cache/data/data_array/sram",
        "soc/cpu_cluster/core1/l1_cache/instruction/tag_array/sram",
        "soc/cpu_cluster/core1/l1_cache/data/tag_array/sram",
        # L2 shared cache
        "soc/cpu_cluster/l2_cache/shared/tag_array/sram",
        "soc/cpu_cluster/l2_cache/shared/data_array/sram",
    ],
    exclude_list=[
        # Debug memories - has "sram" but not in cache context
        "soc/cpu_cluster/core0/debug/trace_buffer/sram",
        "soc/cpu_cluster/core0/debug/breakpoint_unit/sram",
        # Test infrastructure
        "soc/test_wrapper/bist/pattern_gen/cache_test/sram",
        # Has "cache" but not "sram"
        "soc/cpu_cluster/l2_cache/shared/tag_array/register_file",
    ]
)

# Example 2: GPU shader units with specific filtering
print_example(
    "EXAMPLE 2: GPU Shader Units - Prefix + Multi-Segment Combo",
    instance_list=[
        # Shader core 0
        "gpu/shader_array/sm0/warp_scheduler/instruction_buffer/bank0",
        "gpu/shader_array/sm0/warp_scheduler/instruction_buffer/bank1",
        "gpu/shader_array/sm0/warp_scheduler/scoreboard/entry_ram",
        # Shader core 1
        "gpu/shader_array/sm1/warp_scheduler/instruction_buffer/bank0",
        "gpu/shader_array/sm1/warp_scheduler/instruction_buffer/bank1",
        "gpu/shader_array/sm1/warp_scheduler/scoreboard/entry_ram",
        # Shader core 2
        "gpu/shader_array/sm2/warp_scheduler/instruction_buffer/bank0",
        "gpu/shader_array/sm2/warp_scheduler/scoreboard/entry_ram",
    ],
    exclude_list=[
        # Different GPU block
        "gpu/texture_unit/sampler/instruction_buffer/cache",
        # Has "warp" but in different context
        "gpu/shader_array/sm0/warp_register_file/data",
        # Debug infrastructure
        "gpu/debug/shader_profiler/instruction_counter",
    ]
)

# Example 3: Network-on-Chip routers
print_example(
    "EXAMPLE 3: NoC Routers - Suffix Pattern for Port Types",
    instance_list=[
        # Router 0,0
        "chip/noc/mesh_2x2/router_0_0/north_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_0/south_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_0/east_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_0/west_port/input_fifo/buffer",
        # Router 0,1
        "chip/noc/mesh_2x2/router_0_1/north_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_1/south_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_1/east_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_1/west_port/input_fifo/buffer",
        # Router 1,0
        "chip/noc/mesh_2x2/router_1_0/north_port/input_fifo/buffer",
        "chip/noc/mesh_2x2/router_1_0/east_port/input_fifo/buffer",
    ],
    exclude_list=[
        # Output fifos (different from input_fifo)
        "chip/noc/mesh_2x2/router_0_0/north_port/output_fifo/buffer",
        "chip/noc/mesh_2x2/router_0_0/arbiter/decision_fifo/buffer",
        # Non-port buffers
        "chip/noc/mesh_2x2/router_0_0/crossbar/staging_buffer",
    ]
)

# Example 4: Complex chip with power domains
print_example(
    "EXAMPLE 4: Power Domains - Multi-Level Hierarchy Filtering",
    instance_list=[
        # Always-on domain - critical memories
        "chip/power_domain_aon/rtc/calendar/backup_ram/cell0",
        "chip/power_domain_aon/rtc/calendar/backup_ram/cell1",
        "chip/power_domain_aon/pmu/state_machine/retention_ram/entry0",
        "chip/power_domain_aon/pmu/state_machine/retention_ram/entry1",
        # CPU domain - low power memories
        "chip/power_domain_cpu/sleep_controller/wakeup_config/retention_ram/cell0",
        "chip/power_domain_cpu/sleep_controller/wakeup_config/retention_ram/cell1",
    ],
    exclude_list=[
        # Has "ram" but not retention type
        "chip/power_domain_aon/rtc/timer/scratch_ram/cell0",
        "chip/power_domain_cpu/sleep_controller/debug/trace_ram/entry0",
        # Has "retention" but not in RAM context
        "chip/power_domain_aon/pmu/retention_flops/data",
    ]
)

# Example 5: Peripheral subsystem with protocol variations
print_example(
    "EXAMPLE 5: I/O Peripherals - Mixed Pattern Types for Protocol Variants",
    instance_list=[
        # UART peripherals
        "periph/uart0/apb_interface/tx_fifo/mem",
        "periph/uart0/apb_interface/rx_fifo/mem",
        "periph/uart1/apb_interface/tx_fifo/mem",
        "periph/uart1/apb_interface/rx_fifo/mem",
        # SPI peripherals
        "periph/spi0/apb_interface/tx_buffer/mem",
        "periph/spi0/apb_interface/rx_buffer/mem",
        "periph/spi1/apb_interface/tx_buffer/mem",
        # I2C peripherals
        "periph/i2c0/apb_interface/command_queue/mem",
        "periph/i2c0/apb_interface/data_buffer/mem",
    ],
    exclude_list=[
        # AXI interface (not APB)
        "periph/dma/axi_interface/descriptor_queue/mem",
        # APB but not a standard peripheral
        "periph/gpio/apb_interface/config_registers",
        # Wrong memory type
        "periph/uart0/baud_generator/divider_latch",
    ]
)

# Example 6: CPU pipeline with execution units
print_example(
    "EXAMPLE 6: CPU Execution Units - Precise Multi-Segment Filtering",
    instance_list=[
        # Integer ALU
        "cpu/core0/execute/alu_integer/result_queue/entry0",
        "cpu/core0/execute/alu_integer/result_queue/entry1",
        "cpu/core0/execute/alu_integer/bypass_network/latch0",
        # FPU
        "cpu/core0/execute/fpu_double/result_queue/entry0",
        "cpu/core0/execute/fpu_double/result_queue/entry1",
        "cpu/core0/execute/fpu_double/bypass_network/latch0",
        # Load/Store unit
        "cpu/core0/execute/lsu/store_queue/entry0",
        "cpu/core0/execute/lsu/store_queue/entry1",
        "cpu/core0/execute/lsu/load_queue/entry0",
    ],
    exclude_list=[
        # Decode stage (not execute)
        "cpu/core0/decode/instruction_queue/entry0",
        # Execute but different structure
        "cpu/core0/execute/branch_unit/prediction_stack",
        # Has "execute" but in wrong context
        "cpu/core0/debug/execute_trace_buffer/entry0",
    ]
)

# Example 7: Really complex scenario - mixed everything
print_example(
    "EXAMPLE 7: Mixed Hierarchy - Demonstrating All Pattern Types",
    instance_list=[
        # Group 1: Top-level prefix pattern candidate
        "design_top/subsys_a/mod_x/ctrl/state_reg",
        "design_top/subsys_a/mod_y/ctrl/state_reg",
        "design_top/subsys_a/mod_z/ctrl/state_reg",
        # Group 2: Multi-segment pattern candidate
        "design_top/subsys_b/compute/alu/result_buffer/bank0",
        "design_top/subsys_b/compute/alu/result_buffer/bank1",
        "design_top/subsys_b/compute/fpu/result_buffer/bank0",
        # Group 3: Suffix pattern candidate
        "design_top/subsys_c/memory/cache/tag_array",
        "design_top/subsys_c/memory/cache/data_array",
        "design_top/subsys_c/memory/tlb/entry_array",
    ],
    exclude_list=[
        # Would match simple patterns but should be excluded
        "design_top/subsys_a/debug/ctrl/error_reg",
        "design_top/subsys_b/test/alu/scan_buffer/chain0",
        "design_top/subsys_c/memory/bist/pattern_array",
        "design_top/test_wrapper/subsys_mirror/state_reg",
    ]
)

print("\n" + "=" * 80)
print("🎓 KEY INSIGHTS FROM EXAMPLES")
print("=" * 80)
print("""
1. MULTI-SEGMENT patterns (*a*b*c*) excel when:
   - Need to filter by multiple keywords that must appear together
   - Simple substring would cause false positives
   - Example: *cache*sram* matches only cache memories, not debug srams

2. PREFIX patterns (prefix/*) are chosen when:
   - All instances share a common top-level hierarchy
   - Most efficient with only 1 wildcard
   - Example: gpu/* for all GPU components

3. SUFFIX patterns (*/suffix) are perfect for:
   - Grouping by common endpoints (ports, interfaces, types)
   - Avoiding middle-of-path matches
   - Example: */input_fifo vs *input_fifo* (avoids output_fifo_input)

4. COMBINATIONS are used when:
   - Different groups need different specificity levels
   - Mixed hierarchies require multiple pattern types
   - EXACT mode forces zero false positives

5. The greedy solver AUTOMATICALLY chooses the optimal mix by:
   - Trying all pattern types (prefix, suffix, multi, substring, exact)
   - Scoring based on: pattern length, type, and specificity
   - Enforcing ZERO false positives in EXACT mode
   - Minimizing total wildcards while maximizing coverage

Result: You get the most specific, minimal pattern set possible! ✨
""")
print("=" * 80)
