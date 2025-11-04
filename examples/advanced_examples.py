#!/usr/bin/env python3
"""
Advanced Pattern Generation Examples: Mixed Anchored and Substring Patterns
"""
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution

def print_solution(title, instance_list, exclude_list, splitmethod):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    print(f"\nINPUT:")
    print(f"  Include: {len(instance_list)} instances")
    for i, inst in enumerate(instance_list, 1):
        print(f"    {i}. {inst}")

    if exclude_list:
        print(f"\n  Exclude: {len(exclude_list)} instances")
        for i, inst in enumerate(exclude_list, 1):
            print(f"    {i}. {inst}")

    solution = propose_solution(instance_list, exclude_list, SolveOptions(splitmethod=splitmethod))

    print(f"\nOUTPUT:")
    print(f"  Expression: {solution.get('raw_expr', 'N/A')}")
    print(f"\n  Metrics:")
    print(f"    Coverage:       {solution['metrics']['covered']}/{solution['metrics']['total_positive']} instances ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
    print(f"    Patterns:       {solution['metrics']['atoms']}")
    print(f"    Wildcards:      {solution['metrics']['wildcards']}")
    print(f"    False Pos/Neg:  {solution['metrics']['fp']}/{solution['metrics']['fn']}")

    atoms = solution.get('atoms', [])
    if atoms:
        print(f"\n  Pattern Details:")
        for i, atom in enumerate(atoms, 1):
            print(f"\n    Pattern {i}: {atom['text']}")
            print(f"      Type:      {atom['kind']:12} {'✓ ANCHORED' if atom['kind'] in ['prefix', 'suffix'] else '(unanchored)' if atom['kind'] == 'substring' else ''}")
            print(f"      Wildcards: {atom['wildcards']}")
            print(f"      Matches:   {atom['tp']} instances")
            print(f"      Analysis:  ", end="")
            if atom['kind'] == 'prefix':
                print(f"Anchored at START → matches paths beginning with '{atom['text'].replace('/*', '')}'")
            elif atom['kind'] == 'suffix':
                print(f"Anchored at END → matches paths ending with '{atom['text'].replace('*/', '')}'")
            elif atom['kind'] == 'substring':
                print(f"Matches anywhere containing '{atom['text'].strip('*')}'")
            elif atom['kind'] == 'multi':
                parts = [p for p in atom['text'].split('*') if p]
                print(f"Multi-segment: requires {' AND '.join(parts)} in order")
            else:
                print(f"Exact match")
    else:
        print(f"\n  Note: Using inverted logic (matches everything except excludes)")

# Example 1: Mixed prefix and substring patterns
print("=" * 80)
print("ADVANCED EXAMPLES: Mixed Anchored and Substring Patterns")
print("=" * 80)

# Example 1: Hierarchical paths with shared middle components
print_solution(
    "EXAMPLE 1: Mixed Prefix + Substring Patterns",
    instance_list=[
        "soc_top/cpu_cluster0/core0/l1_cache/data_bank0",
        "soc_top/cpu_cluster0/core0/l1_cache/data_bank1",
        "soc_top/cpu_cluster0/core1/l1_cache/data_bank0",
        "soc_top/cpu_cluster0/core1/l1_cache/data_bank1",
        "soc_top/gpu_cluster/shader0/l1_cache/instr_bank0",
        "soc_top/gpu_cluster/shader1/l1_cache/instr_bank0",
        "peripheral/dma_controller/channel0/fifo",
        "peripheral/dma_controller/channel1/fifo",
    ],
    exclude_list=[
        "soc_top/cpu_cluster0/debug/trace",
        "soc_top/gpu_cluster/debug/power",
        "peripheral/uart/rx_fifo",
    ],
    splitmethod="classchange"
)

# Example 2: Complex multi-segment patterns
print_solution(
    "EXAMPLE 2: Multi-Segment Patterns (Multiple Keywords Required)",
    instance_list=[
        "design/block_a/submodule_x/memory/sram_array/bank0",
        "design/block_a/submodule_x/memory/sram_array/bank1",
        "design/block_a/submodule_y/memory/sram_array/bank0",
        "design/block_b/submodule_x/memory/sram_array/bank0",
        "design/block_c/functional_unit/register_file/port_read",
        "design/block_c/functional_unit/register_file/port_write",
    ],
    exclude_list=[
        "design/block_a/debug/memory/capture",
        "design/block_b/test/sram_bist",
        "design/block_d/memory/rom_array/bank0",
    ],
    splitmethod="classchange"
)

# Example 3: Suffix patterns for common endings
print_solution(
    "EXAMPLE 3: Suffix Patterns (Anchored at End)",
    instance_list=[
        "top/module_a/interface/axi_master",
        "top/module_b/interface/axi_master",
        "top/module_c/interface/axi_master",
        "top/subsystem_x/bus/axi_slave",
        "top/subsystem_y/bus/axi_slave",
        "top/subsystem_z/bus/axi_slave",
    ],
    exclude_list=[
        "top/module_a/interface/apb_master",
        "top/subsystem_x/bus/ahb_slave",
    ],
    splitmethod="classchange"
)

# Example 4: Complex real-world chip hierarchy
print_solution(
    "EXAMPLE 4: Complex Chip Hierarchy with Mixed Pattern Types",
    instance_list=[
        "chip/domain_pd/cluster0/cpu_big/l2_cache/tag_array/bank0/i0",
        "chip/domain_pd/cluster0/cpu_big/l2_cache/tag_array/bank1/i0",
        "chip/domain_pd/cluster0/cpu_big/l2_cache/data_array/bank0/i0",
        "chip/domain_pd/cluster1/cpu_small/l1_cache/unified/way0/i0",
        "chip/domain_pd/cluster1/cpu_small/l1_cache/unified/way1/i0",
        "chip/domain_ao/system_cache/directory/entry_ram/bank0/i0",
        "chip/domain_ao/system_cache/directory/entry_ram/bank1/i0",
        "chip/domain_ao/fabric/router/queue_mem/fifo0/i0",
    ],
    exclude_list=[
        "chip/domain_pd/cluster0/debug/trace_buffer/ram/i0",
        "chip/domain_ao/test/mbist_controller/pattern_gen/i0",
    ],
    splitmethod="classchange"
)

print("\n" + "=" * 80)
print("SUMMARY: Pattern Type Usage")
print("=" * 80)
print("""
The pattern generator intelligently combines different pattern types:

1. PREFIX PATTERNS (token/*)
   - Anchored at START of path
   - Fewer wildcards than substring
   - Best for: Grouping by top-level hierarchy
   - Example: soc_top/* matches all soc_top paths

2. SUFFIX PATTERNS (*/token)
   - Anchored at END of path
   - Fewer wildcards than substring
   - Best for: Grouping by common endpoints
   - Example: */axi_master matches all AXI master interfaces

3. SUBSTRING PATTERNS (*token*)
   - Matches anywhere in path
   - More wildcards but more flexible
   - Best for: Common middle components
   - Example: *cache* matches any path with "cache"

4. MULTI-SEGMENT PATTERNS (*tok1*tok2*tok3*)
   - Requires multiple keywords in order
   - Good for: Specific feature combinations
   - Example: *cpu*cache*bank* requires all three

The solver chooses the optimal combination to minimize wildcards while
maximizing coverage and specificity!
""")
print("=" * 80)
