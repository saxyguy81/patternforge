#!/usr/bin/env python3
"""
Quick Start Examples: Simplest possible usage of PatternForge

This file demonstrates the most basic usage patterns for both single-field
and multi-field matching. For more advanced features, see other example files.
"""

from patternforge.engine.solver import propose_solution, propose_solution_structured

print("=" * 80)
print("QUICK START EXAMPLES")
print("=" * 80)

# ============================================================================
# EXAMPLE 1: Single-Field Pattern Matching
# ============================================================================
print("\n" + "=" * 80)
print("EXAMPLE 1: Single-Field Pattern Matching (Simplest)")
print("=" * 80)
print("""
Goal: Find patterns that match hierarchical paths.
Use case: Regression triage, log filtering, signal selection
""")

include = [
    "alpha/module1/mem/i0",
    "alpha/module2/io/i1",
    "beta/cache/bank0",
]
exclude = [
    "gamma/module1/mem/i0",
    "beta/router/debug",
]

print("Include paths:")
for path in include:
    print(f"  ✓ {path}")

print("\nExclude paths:")
for path in exclude:
    print(f"  ✗ {path}")

# Simplest possible usage - defaults work well!
solution = propose_solution(include, exclude)

print(f"\n📤 SOLUTION:")
print(f"  Expression: {solution.expr}")
print(f"  Raw pattern: {solution.raw_expr}")
print(f"  Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
print(f"  False positives: {solution.metrics['fp']}")
print(f"  Patterns used: {len(solution.patterns)}")

print(f"\n  Patterns:")
for pattern in solution.patterns:
    print(f"    {pattern.id:4s}: {pattern.text:20s} (type: {pattern.kind})")

# ============================================================================
# EXAMPLE 2: Structured Multi-Field Pattern Matching
# ============================================================================
print("\n" + "=" * 80)
print("EXAMPLE 2: Structured Multi-Field Pattern Matching")
print("=" * 80)
print("""
Goal: Find patterns across structured data with multiple fields.
Use case: Hardware signal selection, database filtering, multi-column matching
""")

include_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[31]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DOUT[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DIN[0]"},
]

exclude_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "CLK"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DIN[0]"},
]

print("Include rows (module, instance, pin):")
for row in include_rows:
    print(f"  ✓ {row['module']:15s} {row['instance']:35s} {row['pin']}")

print("\nExclude rows:")
for row in exclude_rows:
    print(f"  ✗ {row['module']:15s} {row['instance']:35s} {row['pin']}")

# Simplest structured usage - auto-detects fields!
solution = propose_solution_structured(include_rows, exclude_rows)

print(f"\n📤 SOLUTION:")
print(f"  Expression: {solution.expr}")
print(f"  Raw pattern: {solution.raw_expr}")
print(f"  Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
print(f"  False positives: {solution.metrics['fp']}")
print(f"  Expressions used: {len(solution.expressions)}")

print(f"\n  Patterns by field:")
for pattern in solution.patterns:
    field = pattern.field or 'ALL'
    print(f"    {field:10s}: {pattern.text:20s} (type: {pattern.kind})")

# ============================================================================
# EXAMPLE 3: Exact vs Approximate Modes
# ============================================================================
print("\n" + "=" * 80)
print("EXAMPLE 3: Quality Modes (EXACT vs APPROX)")
print("=" * 80)
print("""
EXACT mode: Zero false positives guaranteed (default)
APPROX mode: Faster, may allow some false positives for simpler patterns
""")

large_include = [
    f"regress/nightly/ip{chr(65+i)}/test_module/variant{j}/fail"
    for i in range(5) for j in range(3)
]
large_exclude = [
    f"regress/nightly/ip{chr(65+i)}/test_module/variant{j}/pass"
    for i in range(5) for j in range(3)
]

print(f"Dataset: {len(large_include)} include, {len(large_exclude)} exclude")

# EXACT mode (zero false positives guaranteed)
sol_exact = propose_solution(
    large_include, large_exclude,
    mode="EXACT"  # Zero FP guarantee
)
print(f"\nEXACT mode:")
print(f"  Pattern: {sol_exact.raw_expr}")
print(f"  FP: {sol_exact.metrics['fp']}, Patterns: {sol_exact.metrics['patterns']}")

# APPROX mode (faster, may allow some FP)
sol_approx = propose_solution(
    large_include, large_exclude,
    mode="APPROX"  # Faster, simpler patterns
)
print(f"\nAPPROX mode:")
print(f"  Pattern: {sol_approx.raw_expr}")
print(f"  FP: {sol_approx.metrics['fp']}, Patterns: {sol_approx.metrics['patterns']}")

print("\n" + "=" * 80)
print("✅ Quick start complete! See other examples for advanced features:")
print("  - 02_single_field_patterns.py: Advanced single-field patterns")
print("  - 03_structured_patterns.py: Comprehensive multi-field examples")
print("  - 04_performance_scaling.py: Performance benchmarks")
print("=" * 80)
