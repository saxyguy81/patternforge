#!/usr/bin/env python3
"""
Single-Field Pattern Examples: Comprehensive Guide to Pattern Types

This file demonstrates all pattern types for single-field (flat string) matching:
- PREFIX patterns (token/*)
- SUFFIX patterns (*/token)
- SUBSTRING patterns (*token*)
- MULTI-SEGMENT patterns (*a*b*c*)
- Pattern combinations and ranking

For multi-field structured data, see 03_structured_patterns.py
"""

from patternforge.engine.solver import propose_solution

def print_solution(title, include, exclude, **kwargs):
    """Helper to print a solution with formatting."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    print(f"\n📥 INPUT:")
    print(f"  ✓ Include: {len(include)} paths")
    for path in include[:10]:
        print(f"      {path}")
    if len(include) > 10:
        print(f"      ... and {len(include) - 10} more")

    if exclude:
        print(f"\n  ✗ Exclude: {len(exclude)} paths")
        for path in exclude[:5]:
            print(f"      {path}")
        if len(exclude) > 5:
            print(f"      ... and {len(exclude) - 5} more")

    solution = propose_solution(include, exclude, **kwargs)

    print(f"\n📤 OUTPUT:")
    print(f"  Expression: {solution.expr}")
    print(f"  Raw pattern: {solution.raw_expr}")
    print(f"\n  📊 Metrics:")
    print(f"    Coverage:      {solution.metrics['covered']}/{solution.metrics['total_positive']} ({100*solution.metrics['covered']/max(1, solution.metrics['total_positive']):.0f}%)")
    print(f"    False Pos:     {solution.metrics['fp']} ✅")
    print(f"    Patterns:      {solution.metrics['patterns']}")
    print(f"    Wildcards:     {solution.metrics['wildcards']}")

    print(f"\n  🎯 Pattern Details:")
    for pattern in solution.patterns:
        kind_desc = {
            'prefix': 'PREFIX (starts with)',
            'suffix': 'SUFFIX (ends with)',
            'substring': 'SUBSTRING (contains)',
            'multi': 'MULTI-SEGMENT (ordered keywords)',
            'exact': 'EXACT (full match)'
        }.get(pattern.kind, pattern.kind.upper())

        print(f"\n    [{pattern.id}] {pattern.text}")
        print(f"        Type: {kind_desc}")
        print(f"        Matches: {pattern.tp} paths, FP: {pattern.fp}, Wildcards: {pattern.wildcards}")

    return solution

print("=" * 80)
print("SINGLE-FIELD PATTERN EXAMPLES")
print("=" * 80)
print("""
This guide demonstrates different wildcard pattern types that PatternForge
discovers automatically. All examples use hierarchical paths like:
  chip/cpu/core0/cache/bank0

The solver finds minimal patterns with wildcards (*) to match your data.
""")

# ============================================================================
# EXAMPLE 1: PREFIX Patterns
# ============================================================================
print_solution(
    "EXAMPLE 1: PREFIX Patterns - Anchored at Start",
    include=[
        "video/display/pixel0",
        "video/display/pixel1",
        "video/display/scaler0",
        "video/shader/vector0",
        "video/shader/vector1",
        "video/memory/cache0",
    ],
    exclude=[
        "audio/codec/mp3",
        "audio/mixer/channel0",
        "compute/dsp/vector0",
    ]
)

# ============================================================================
# EXAMPLE 2: SUBSTRING Patterns
# ============================================================================
print_solution(
    "EXAMPLE 2: SUBSTRING Patterns - Matches Anywhere",
    include=[
        "chip/cpu/l1_cache/bank0",
        "chip/cpu/l1_cache/bank1",
        "chip/cpu/l2_cache/bank0",
        "chip/gpu/l1_cache/bank0",
    ],
    exclude=[
        "chip/cpu/register_file/entry0",
        "chip/cpu/instruction_buffer/slot0",
        "chip/gpu/texture_memory/block0",
    ]
)

# ============================================================================
# EXAMPLE 3: MULTI-SEGMENT Patterns
# ============================================================================
print_solution(
    "EXAMPLE 3: MULTI-SEGMENT Patterns - Ordered Keywords",
    include=[
        "system/cpu/core0/execute/alu_int/stage1_reg",
        "system/cpu/core0/execute/alu_int/stage2_reg",
        "system/cpu/core1/execute/alu_int/stage1_reg",
        "system/cpu/core0/execute/alu_fp/stage1_reg",
    ],
    exclude=[
        "system/cpu/core0/decode/instruction_reg",
        "system/cpu/core0/fetch/pc_reg",
        "system/cpu/core0/execute/branch_unit/prediction_reg",
        "system/gpu/shader0/alu_int/stage1_reg",
    ]
)

# ============================================================================
# EXAMPLE 4: Pattern Ranking and Selection
# ============================================================================
print("\n" + "=" * 80)
print("EXAMPLE 4: Pattern Ranking - How the Solver Chooses")
print("=" * 80)
print("""
The solver generates many candidate patterns and ranks them by:
- Coverage (how many include items they match)
- Precision (avoiding exclude items)
- Simplicity (fewer wildcards, shorter patterns)
- IDF score (favoring discriminative tokens)

Let's see what patterns are generated and how they're ranked.
""")

from patternforge.engine.candidates import generate_candidates

test_paths = [
    "chip/cpu/core0/l1_cache/data_array/bank0",
    "chip/cpu/core0/l1_cache/data_array/bank1",
    "chip/cpu/core0/l1_cache/tag_array/bank0",
    "chip/cpu/core1/l1_cache/data_array/bank0",
]

print("Input paths:")
for path in test_paths:
    print(f"  {path}")

candidates = generate_candidates(
    test_paths,
    splitmethod='classchange',
    min_token_len=3,
    per_word_substrings=16,
    max_multi_segments=3
)

print(f"\nTop 10 generated patterns (of {len(candidates)} total):")
print(f"  {'Pattern':<30} {'Type':<12} {'Score':>8}")
print(f"  {'-'*30} {'-'*12} {'-'*8}")

# Sort by score descending
top_candidates = sorted(candidates, key=lambda x: -x[2])[:10]
for pattern, kind, score, field in top_candidates:
    print(f"  {pattern:<30} {kind:<12} {score:>8.2f}")

# ============================================================================
# EXAMPLE 5: Complex Hierarchical Filtering
# ============================================================================
print_solution(
    "EXAMPLE 5: Complex Hierarchical Filtering",
    include=[
        "soc/cpu_cluster/core0/execute/alu/result_reg[0]",
        "soc/cpu_cluster/core0/execute/alu/result_reg[63]",
        "soc/cpu_cluster/core1/execute/alu/result_reg[0]",
        "soc/cpu_cluster/core0/execute/fpu/result_reg[0]",
        "soc/cpu_cluster/core0/execute/fpu/result_reg[31]",
    ],
    exclude=[
        "soc/cpu_cluster/core0/decode/instruction_reg[0]",
        "soc/cpu_cluster/core0/execute/branch/prediction_reg[0]",
        "soc/gpu_cluster/shader0/execute/alu/result_reg[0]",
        "soc/cpu_cluster/debug/trace_buffer/data_reg[0]",
    ]
)

# ============================================================================
# EXAMPLE 6: Inverted Patterns (NOT logic)
# ============================================================================
print("\n" + "=" * 80)
print("EXAMPLE 6: Inverted Patterns - Everything EXCEPT")
print("=" * 80)
print("""
Sometimes it's easier to specify what you DON'T want.
invert="always" returns the complement: "everything EXCEPT pattern"
""")

include = [
    "video/display/pixel0",
    "video/shader/vector0",
    "audio/codec/mp3",
    "audio/mixer/channel0",
    "compute/dsp/vector0",
]
exclude = [
    "video/debug/trace",
    "audio/debug/stats",
    "compute/debug/monitor",
]

print("\nNormal mode (find what includes have in common):")
sol_normal = propose_solution(include, exclude, invert="never")
print(f"  Pattern: {sol_normal.raw_expr}")
print(f"  Inverted: {sol_normal.global_inverted}")
print(f"  Coverage: {sol_normal.metrics['covered']}/{sol_normal.metrics['total_positive']}")

print("\nInverted mode (everything except debug):")
sol_inverted = propose_solution(include, exclude, invert="always")
print(f"  Pattern: {sol_inverted.raw_expr}")
print(f"  Inverted: {sol_inverted.global_inverted}")
print(f"  Coverage: {sol_inverted.metrics['covered']}/{sol_inverted.metrics['total_positive']}")
print(f"  Meaning: Match everything EXCEPT {sol_inverted.raw_expr}")

print("\nAuto mode (solver picks best):")
sol_auto = propose_solution(include, exclude, invert="auto")
print(f"  Pattern: {sol_auto.raw_expr}")
print(f"  Inverted: {sol_auto.global_inverted}")
print(f"  Coverage: {sol_auto.metrics['covered']}/{sol_auto.metrics['total_positive']}")

# ============================================================================
# EXAMPLE 7: Real-World Use Case - Regression Triage
# ============================================================================
print_solution(
    "EXAMPLE 7: Real-World - Regression Triage",
    include=[
        "regress/nightly/ipA/test_fifo/rand_smoke/fail",
        "regress/nightly/ipA/test_fifo/max_burst/fail",
        "regress/nightly/ipA/test_dma/rand_smoke/fail",
        "regress/nightly/ipB/test_cache/assoc16/fail",
        "regress/nightly/ipB/test_cache/assoc32/fail",
        "regress/nightly/ipC/test_uart/loopback/fail",
        "regress/nightly/ipD/test_pcie/gen4_link/fail",
    ],
    exclude=[
        "regress/nightly/ipA/test_fifo/rand_smoke/pass",
        "regress/nightly/ipA/test_dma/stress/pass",
        "regress/nightly/ipB/test_cache/assoc16/pass",
        "regress/nightly/ipC/test_uart/parity/pass",
        "regress/nightly/ipD/test_pcie/error_inject/pass",
    ]
)

# ============================================================================
# EXAMPLE 8: Tokenization Methods
# ============================================================================
print("\n" + "=" * 80)
print("EXAMPLE 8: Tokenization Methods - classchange vs char")
print("=" * 80)
print("""
Tokenization affects which patterns are generated:
- 'classchange': Split on character class changes (CamelCase, numbers, etc.)
- 'char': Split on specific characters like '/', '_', etc.
""")

paths = [
    "SRAMController_512x64/BankArray0/ReadPort",
    "SRAMController_512x64/BankArray1/WritePort",
    "SRAMController_1024x32/BankArray0/ReadPort",
]

print("Paths to match:")
for p in paths:
    print(f"  {p}")

print("\nWith splitmethod='classchange':")
sol_class = propose_solution(paths, [], splitmethod='classchange')
print(f"  Pattern: {sol_class.raw_expr}")
print(f"  Patterns: {sol_class.metrics['patterns']}")

print("\nWith splitmethod='char':")
sol_char = propose_solution(paths, [], splitmethod='char')
print(f"  Pattern: {sol_char.raw_expr}")
print(f"  Patterns: {sol_char.metrics['patterns']}")

print("\n" + "=" * 80)
print("🎓 KEY INSIGHTS: Pattern Types")
print("=" * 80)
print("""
PATTERN TYPES:
1. PREFIX (token/*):
   - Anchored at start of string
   - Example: video/* matches video/display/pixel0
   - Use when: All targets share a common prefix

2. SUFFIX (*/token):
   - Anchored at end of string
   - Example: */fail matches all paths ending in /fail
   - Use when: All targets share a common suffix

3. SUBSTRING (*token*):
   - Matches anywhere in string
   - Example: *cache* matches chip/cpu/l1_cache/bank0
   - Use when: Target keyword appears anywhere

4. MULTI-SEGMENT (*a*b*c*):
   - Multiple ordered keywords
   - Example: *cpu*execute*alu* matches cpu/core0/execute/alu_int/stage1
   - Use when: Need multiple keywords in specific order
   - More precise than single substring

5. EXACT (token):
   - Full string match, no wildcards
   - Example: "video/display/pixel0" matches only that exact path
   - Use when: Patterns are identical

RANKING FACTORS:
- Coverage: How many include items matched
- Precision: Avoiding exclude items (zero FP in EXACT mode)
- Simplicity: Fewer wildcards preferred
- Length: Shorter patterns preferred
- IDF: Rare tokens ranked higher

MODES:
- EXACT: Guarantees zero false positives (may use more patterns)
- APPROX: Allows some FP for simpler solutions (faster)

INVERSION:
- NEVER: Normal mode (find what matches)
- ALWAYS: Complement mode (everything except pattern)
- AUTO: Solver chooses based on cost
""")

print("=" * 80)
print("✅ Examples complete! Next: 03_structured_patterns.py for multi-field data")
print("=" * 80)
