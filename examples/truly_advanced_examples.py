#!/usr/bin/env python3
"""
Even More Advanced: Truly Complex Pattern Combinations
"""
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution

print("=" * 80)
print("TRULY ADVANCED: Complex Pattern Combinations")
print("=" * 80)

# Example 1: Forcing multi-segment patterns with complex terms
print("\n" + "=" * 80)
print("EXAMPLE 1: Multi-Segment Patterns (Requires Complex Terms)")
print("=" * 80)

instance_list = [
    "chip/cpu_domain/core0/l1_instruction_cache/tag_array/sram_bank0",
    "chip/cpu_domain/core0/l1_instruction_cache/tag_array/sram_bank1",
    "chip/cpu_domain/core0/l1_data_cache/tag_array/sram_bank0",
    "chip/cpu_domain/core1/l1_instruction_cache/tag_array/sram_bank0",
    "chip/gpu_domain/shader0/l1_texture_cache/tag_array/sram_bank0",
    "chip/gpu_domain/shader0/l1_texture_cache/data_array/sram_bank0",
]

exclude_list = [
    "chip/cpu_domain/core0/debug_cache/tag_array/capture_ram",
    "chip/io_domain/pcie/buffer_cache/sram_bank0",
]

solution = propose_solution(instance_list, exclude_list,
                           SolveOptions(splitmethod="classchange"))

print(f"\nINPUT:")
print(f"  Include: {len(instance_list)} L1 cache instances")
for inst in instance_list:
    print(f"    • {inst}")
print(f"\n  Exclude: {len(exclude_list)} non-L1 cache instances")
for inst in exclude_list:
    print(f"    • {inst}")

print(f"\nOUTPUT:")
print(f"  Expression: {solution.get('expr', 'N/A')}")
print(f"  Raw: {solution.get('raw_expr', 'N/A')}")
print(f"\n  Metrics:")
print(f"    Coverage:  {solution['metrics']['covered']}/{solution['metrics']['total_positive']} ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
print(f"    Wildcards: {solution['metrics']['wildcards']}")
print(f"    Patterns:  {solution['metrics']['atoms']}")

# Show terms (may include conjunctions)
terms = solution.get('terms', [])
if terms:
    print(f"\n  Terms Generated ({len(terms)}):")
    for i, term in enumerate(terms, 1):
        print(f"\n    Term {i}: {term.get('raw_expr', 'N/A')}")
        print(f"      Expression Type: {term.get('expr', 'N/A')}")
        print(f"      Matches: {term.get('tp')} true positives, {term.get('fp')} false positives")
        print(f"      Incremental: +{term.get('incremental_tp')} TP, +{term.get('incremental_fp')} FP")

# Example 2: Mixed prefix and multi-segment
print("\n" + "=" * 80)
print("EXAMPLE 2: Prefix + Multi-Segment Combination")
print("=" * 80)

instance_list = [
    "soc/cpu_subsystem/core0/pipeline/decode/register_file/port0",
    "soc/cpu_subsystem/core0/pipeline/decode/register_file/port1",
    "soc/cpu_subsystem/core1/pipeline/decode/register_file/port0",
    "soc/gpu_subsystem/compute_unit0/local_memory/bank0",
    "soc/gpu_subsystem/compute_unit0/local_memory/bank1",
    "soc/gpu_subsystem/compute_unit1/local_memory/bank0",
]

exclude_list = [
    "soc/io_subsystem/uart/register_file/control",
    "soc/debug_subsystem/trace/memory/bank0",
]

solution = propose_solution(instance_list, exclude_list, SolveOptions(splitmethod="classchange"))

print(f"\nINPUT:")
print(f"  Include: {len(instance_list)} mixed CPU and GPU instances")
for inst in instance_list:
    print(f"    • {inst}")
print(f"\n  Exclude: {len(exclude_list)} IO and debug instances")
for inst in exclude_list:
    print(f"    • {inst}")

print(f"\nOUTPUT:")
print(f"  Expression: {solution.get('raw_expr', 'N/A')}")
print(f"\n  Metrics:")
print(f"    Coverage:  {solution['metrics']['covered']}/{solution['metrics']['total_positive']} ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
print(f"    Wildcards: {solution['metrics']['wildcards']}")

atoms = solution.get('atoms', [])
print(f"\n  Pattern Analysis ({len(atoms)} patterns):")
for i, atom in enumerate(atoms, 1):
    print(f"\n    Pattern {i}: {atom['text']}")
    print(f"      Type:      {atom['kind']:12} {'✓ ANCHORED' if atom['kind'] in ['prefix', 'suffix'] else ''}")
    print(f"      Wildcards: {atom['wildcards']}")
    print(f"      Matches:   {atom['tp']} instances")

    if atom['kind'] == 'prefix':
        prefix = atom['text'].replace('/*', '')
        print(f"      Insight:   Groups all '{prefix}' hierarchy paths")
    elif atom['kind'] == 'multi':
        segments = [s for s in atom['text'].split('*') if s]
        print(f"      Insight:   Requires path to contain: {' → '.join(segments)}")

# Example 3: Very complex real-world scenario
print("\n" + "=" * 80)
print("EXAMPLE 3: Real-World Complex Chip with Mixed Patterns")
print("=" * 80)

instance_list = [
    # CPU power domain - L2 caches
    "chip/pd_cpu/cluster_big/l2_cache/tag_array/way0/bank0/mem",
    "chip/pd_cpu/cluster_big/l2_cache/tag_array/way0/bank1/mem",
    "chip/pd_cpu/cluster_big/l2_cache/data_array/way0/bank0/mem",
    "chip/pd_cpu/cluster_little/l2_cache/tag_array/way0/bank0/mem",
    # GPU power domain - caches
    "chip/pd_gpu/shader_array/sm0/l1_cache/unified/bank0/mem",
    "chip/pd_gpu/shader_array/sm1/l1_cache/unified/bank0/mem",
    # System cache (always-on domain)
    "chip/pd_aon/system_cache/snoop_filter/directory/entry0/mem",
    "chip/pd_aon/system_cache/snoop_filter/directory/entry1/mem",
    # Network-on-chip routers
    "chip/pd_aon/noc_fabric/router_0_0/virtual_channel/vc0/buffer/mem",
    "chip/pd_aon/noc_fabric/router_0_1/virtual_channel/vc0/buffer/mem",
]

exclude_list = [
    "chip/pd_cpu/cluster_big/debug/trace/buffer/mem",
    "chip/pd_gpu/shader_array/sm0/debug/perf_counter/mem",
    "chip/pd_aon/test_wrapper/mbist/pattern_gen/mem",
]

solution = propose_solution(instance_list, exclude_list, SolveOptions(splitmethod="classchange"))

print(f"\nINPUT:")
print(f"  Include: {len(instance_list)} memory instances across 3 power domains")
print(f"    - CPU domain:    L2 caches (4 instances)")
print(f"    - GPU domain:    L1 caches (2 instances)")
print(f"    - Always-on:     System cache + NoC (4 instances)")

print(f"\n  Exclude: {len(exclude_list)} debug/test instances")

print(f"\nOUTPUT:")
print(f"  Expression: {solution.get('raw_expr', 'N/A')[:100]}...")
print(f"\n  Metrics:")
print(f"    Coverage:    {solution['metrics']['covered']}/{solution['metrics']['total_positive']} ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
print(f"    Wildcards:   {solution['metrics']['wildcards']}")
print(f"    Patterns:    {solution['metrics']['atoms']}")
print(f"    Compression: {len(instance_list)} → {solution['metrics']['atoms']} ({100*(1-solution['metrics']['atoms']/len(instance_list)):.0f}% reduction)")

atoms = solution.get('atoms', [])
print(f"\n  Generated Patterns:")
print(f"  {'-' * 76}")
for i, atom in enumerate(atoms, 1):
    text = atom['text']
    if len(text) > 50:
        text = text[:25] + "..." + text[-22:]

    pattern_type = ""
    if atom['kind'] == 'prefix':
        pattern_type = " [PREFIX - anchored start]"
    elif atom['kind'] == 'suffix':
        pattern_type = " [SUFFIX - anchored end]"
    elif atom['kind'] == 'multi':
        pattern_type = " [MULTI - ordered segments]"
    elif atom['kind'] == 'substring':
        pattern_type = " [SUBSTRING - flexible]"

    print(f"\n  {i}. {text}{pattern_type}")
    print(f"     Wildcards: {atom['wildcards']}, Matches: {atom['tp']} instances, FP: {atom['fp']}")

print("\n" + "=" * 80)
print("KEY INSIGHT: Pattern Optimization Strategy")
print("=" * 80)
print("""
The solver uses a GREEDY strategy that:

1. Generates ALL candidate patterns:
   - Prefix:      token/*        (1 wildcard, start-anchored)
   - Suffix:      */token        (1 wildcard, end-anchored)
   - Substring:   *token*        (2 wildcards, unanchored)
   - Multi:       *tok1*tok2*    (variable wildcards, ordered)
   - Exact:       full/path      (0 wildcards)

2. Scores patterns by:
   - Length of token (longer = better)
   - Pattern type (anchored > unanchored)
   - Special boost: prefix/suffix get 1.5x score

3. Greedily selects patterns to:
   - Maximize coverage of include set
   - Minimize false positives from exclude set
   - Minimize total wildcards
   - Minimize number of patterns

Result: Optimal balance of specificity, coverage, and simplicity!
""")
print("=" * 80)
