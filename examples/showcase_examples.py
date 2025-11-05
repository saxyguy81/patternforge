#!/usr/bin/env python3
"""
Showcase: The Best Examples of Mixed Pattern Types
"""
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution
from patternforge.engine.candidates import generate_candidates

print("=" * 80)
print("SHOWCASE: Mixed Pattern Type Examples")
print("=" * 80)
print("\nIMPORTANT: All examples use EXACT mode (default)")
print("  - EXACT mode enforces ZERO false positives (max_fp=0)")
print("  - Patterns will NEVER match items in the exclude list")
print("  - This ensures precision and safety")
print("=" * 80)

# Example 1: Beautiful mix of prefix and suffix
print("\n" + "=" * 80)
print("EXAMPLE 1: Prefix + Suffix Patterns Working Together")
print("=" * 80)

instance_list = [
    # AXI master interfaces in CPU domain
    "soc_top/cpu_domain/core0/axi_master",
    "soc_top/cpu_domain/core1/axi_master",
    "soc_top/cpu_domain/dma/axi_master",
    # AXI slave interfaces in memory domain
    "soc_top/mem_domain/ddr_ctrl0/axi_slave",
    "soc_top/mem_domain/ddr_ctrl1/axi_slave",
    # APB interfaces in peripheral domain
    "soc_top/periph_domain/uart0/apb_slave",
    "soc_top/periph_domain/uart1/apb_slave",
    "soc_top/periph_domain/gpio/apb_slave",
]

exclude_list = [
    "soc_top/debug_domain/trace/ahb_master",
    "soc_top/test_domain/bist/interface",
]

solution = propose_solution(instance_list, exclude_list, SolveOptions(splitmethod="classchange"))

print(f"\nINPUT ({len(instance_list)} instances):")
print(f"  CPU domain:   3x axi_master")
print(f"  Memory domain: 2x axi_slave")
print(f"  Periph domain: 3x apb_slave")

for inst in instance_list:
    print(f"    • {inst}")

print(f"\nEXCLUDE ({len(exclude_list)} instances):")
for inst in exclude_list:
    print(f"    • {inst}")

print(f"\nOUTPUT:  ")
print(f"  Expression: {solution.get('raw_expr', 'N/A')}")
print(f"\n  Metrics:")
print(f"    Coverage:  {solution['metrics']['covered']}/{solution['metrics']['total_positive']} ({100*solution['metrics']['covered']/solution['metrics']['total_positive']:.0f}%)")
print(f"    False Pos: {solution['metrics']['fp']} (EXACT mode enforces FP=0)")
print(f"    False Neg: {solution['metrics']['fn']}")
print(f"    Wildcards: {solution['metrics']['wildcards']}")
print(f"    Patterns:  {solution['metrics']['atoms']}")

atoms = solution.get('atoms', [])
print(f"\n  Pattern Breakdown:")
for i, atom in enumerate(atoms, 1):
    print(f"\n    {i}. {atom['text']}")
    print(f"       Type:      {atom['kind']}")
    print(f"       Wildcards: {atom['wildcards']}")
    print(f"       Matches:   {atom['tp']} instances")

    if atom['kind'] == 'prefix':
        print(f"       📌 Anchored START: Must begin with '{atom['text'].replace('/*', '')}'")
    elif atom['kind'] == 'suffix':
        print(f"       📌 Anchored END: Must end with '{atom['text'].replace('*/', '')}'")
    elif atom['kind'] == 'multi':
        segments = [s for s in atom['text'].split('*') if s]
        print(f"       🔗 Multi-segment: Requires {' AND '.join(segments)} in order")

print(f"\n  💡 INSIGHT:")
if any(a['kind'] in ['prefix', 'suffix'] for a in atoms):
    print(f"     The solver intelligently chose ANCHORED patterns!")
    print(f"     This is more specific than unanchored substring patterns.")

# Example 2: Multi-segment pattern showcase
print("\n" + "=" * 80)
print("EXAMPLE 2: Multi-Segment Pattern (Ordered Keywords)")
print("=" * 80)

instance_list = [
    "design/cpu_cluster/core0/pipeline/execute/alu/result_reg",
    "design/cpu_cluster/core0/pipeline/execute/mult/result_reg",
    "design/cpu_cluster/core1/pipeline/execute/alu/result_reg",
    "design/cpu_cluster/core1/pipeline/execute/fpu/result_reg",
]

exclude_list = [
    "design/cpu_cluster/core0/execute/debug_reg",  # Missing 'pipeline'
    "design/gpu_cluster/core0/pipeline/execute/result_reg",  # Different cluster
]

solution = propose_solution(instance_list, exclude_list, SolveOptions(splitmethod="classchange"))

print(f"\nINPUT ({len(instance_list)} instances):")
for inst in instance_list:
    print(f"  • {inst}")

print(f"\nEXCLUDE ({len(exclude_list)} instances):")
for inst in exclude_list:
    print(f"  • {inst}")

print(f"\nOUTPUT:")
print(f"  Expression: {solution.get('raw_expr', 'N/A')}")

atoms = solution.get('atoms', [])
print(f"\n  Generated Pattern:")
for atom in atoms:
    print(f"    {atom['text']} (type={atom['kind']}, wildcards={atom['wildcards']})")

    if atom['kind'] == 'multi':
        segments = [s for s in atom['text'].split('*') if s]
        print(f"\n    🔗 This is a MULTI-SEGMENT pattern!")
        print(f"       Requires ALL of these keywords IN ORDER:")
        for i, seg in enumerate(segments, 1):
            print(f"         {i}. '{seg}'")
        print(f"\n       Why this works:")
        print(f"       ✓ Matches all includes (they have all segments in order)")
        print(f"       ✗ Rejects excludes (missing segments or wrong order)")

# Example 3: The grand finale - all types
print("\n" + "=" * 80)
print("EXAMPLE 3: Grand Finale - Candidate Analysis")
print("=" * 80)

instance_list = [
    "project/module_a/subsys_x/component/memory/bank0",
    "project/module_a/subsys_x/component/memory/bank1",
    "project/module_a/subsys_y/component/memory/bank0",
    "project/module_b/subsys_x/logic/fifo",
    "project/module_b/subsys_y/logic/fifo",
]

print(f"\nINPUT ({len(instance_list)} instances):")
for inst in instance_list:
    print(f"  • {inst}")

print(f"\nCANDIDATE GENERATION ANALYSIS:")
print(f"-" * 80)

candidates = generate_candidates(
    instance_list,
    splitmethod='classchange',
    min_token_len=3,
    per_word_substrings=True,
    max_multi_segments=3,
    token_iter=None
)

# Group by type
by_type = {}
for pattern, kind, score, field in candidates:
    if kind not in by_type:
        by_type[kind] = []
    by_type[kind].append((pattern, score))

print(f"\nGenerated {len(candidates)} total candidates")
print(f"")

for kind in ['prefix', 'suffix', 'multi', 'substring', 'exact']:
    if kind in by_type:
        patterns = sorted(by_type[kind], key=lambda x: -x[1])[:5]
        print(f"  {kind.upper():12} ({len(by_type[kind])} patterns):")
        for pattern, score in patterns[:3]:
            print(f"    score={score:6.1f}  {pattern}")
        if len(patterns) > 3:
            print(f"    ... and {len(by_type[kind]) - 3} more")

print(f"\n{'=' * 80}")
print(f"WHAT THE SOLVER CHOSE:")
print(f"{'=' * 80}")

solution = propose_solution(instance_list, [], SolveOptions(splitmethod="classchange"))
print(f"  Expression: {solution.get('raw_expr', 'N/A')}")
print(f"  Wildcards:  {solution['metrics']['wildcards']}")

atoms = solution.get('atoms', [])
for i, atom in enumerate(atoms, 1):
    print(f"\n  Pattern {i}: {atom['text']}")
    print(f"    Type: {atom['kind']}, Score: {atom.get('score', 'N/A')}, Matches: {atom['tp']}")
    print(f"    Why chosen: ", end="")
    if atom['kind'] == 'prefix':
        print("Start-anchored → highly specific with only 1 wildcard")
    elif atom['kind'] == 'suffix':
        print("End-anchored → highly specific with only 1 wildcard")
    elif atom['kind'] == 'multi':
        print("Multi-segment → specific ordering constraint")
    elif atom['kind'] == 'substring':
        print("Flexible matching → good balance of coverage and simplicity")
    else:
        print("Exact match → no ambiguity")

print(f"\n{'=' * 80}")
print(f"KEY TAKEAWAYS")
print(f"{'=' * 80}")
print("""
The pattern generator creates a rich candidate pool:

1. PREFIX patterns (token/*)
   ✓ 1 wildcard only
   ✓ Anchored at start
   ✓ 1.5x score boost
   → Best for: Grouping by top-level hierarchy

2. SUFFIX patterns (*/token)
   ✓ 1 wildcard only
   ✓ Anchored at end
   ✓ 1.5x score boost
   → Best for: Grouping by endpoints

3. MULTI-SEGMENT patterns (*tok1*tok2*tok3*)
   ✓ Ordered constraints
   ✓ Multiple keywords required
   → Best for: Complex filtering logic

4. SUBSTRING patterns (*token*)
   • 2 wildcards
   • Unanchored (flexible)
   → Best for: Simple, broad matching

The greedy solver picks the OPTIMAL combination to minimize wildcards
while maximizing coverage and avoiding false positives!
""")
print("=" * 80)
