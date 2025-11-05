#!/usr/bin/env python3
"""
Quick Start Examples: Simplest possible usage of PatternForge

This file demonstrates the most basic usage patterns for both single-field
and multi-field matching. For more advanced features, see other example files.
"""
import sys
sys.path.insert(0, "../src")

from patternforge.engine.models import SolveOptions, QualityMode
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
solution = propose_solution(include, exclude, SolveOptions())

print(f"\n📤 SOLUTION:")
print(f"  Expression: {solution['expr']}")
print(f"  Raw pattern: {solution.get('raw_expr', 'N/A')}")
print(f"  Coverage: {solution['metrics']['covered']}/{solution['metrics']['total_positive']}")
print(f"  False positives: {solution['metrics']['fp']}")
print(f"  Patterns used: {len(solution['atoms'])}")

print(f"\n  Patterns:")
for atom in solution['atoms']:
    print(f"    {atom['id']:4s}: {atom['text']:20s} (type: {atom['kind']})")

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
print(f"  Expression: {solution['expr']}")
print(f"  Raw pattern: {solution.get('raw_expr', 'N/A')}")
print(f"  Coverage: {solution['metrics']['covered']}/{solution['metrics']['total_positive']}")
print(f"  False positives: {solution['metrics']['fp']}")
print(f"  Expressions used: {len(solution.get('expressions', []))}")

print(f"\n  Patterns by field:")
for atom in solution['atoms']:
    field = atom.get('field', 'ALL')
    print(f"    {field:10s}: {atom['text']:20s} (type: {atom['kind']})")

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

# EXACT mode
sol_exact = propose_solution(
    large_include, large_exclude,
    SolveOptions(mode=QualityMode.EXACT)
)
print(f"\nEXACT mode:")
print(f"  Pattern: {sol_exact.get('raw_expr', 'N/A')}")
print(f"  FP: {sol_exact['metrics']['fp']}, Atoms: {sol_exact['metrics']['atoms']}")

# APPROX mode (faster)
sol_approx = propose_solution(
    large_include, large_exclude,
    SolveOptions(mode=QualityMode.APPROX)
)
print(f"\nAPPROX mode:")
print(f"  Pattern: {sol_approx.get('raw_expr', 'N/A')}")
print(f"  FP: {sol_approx['metrics']['fp']}, Atoms: {sol_approx['metrics']['atoms']}")

print("\n" + "=" * 80)
print("✅ Quick start complete! See other examples for advanced features:")
print("  - 02_single_field_patterns.py: Advanced single-field patterns")
print("  - 03_structured_patterns.py: Comprehensive multi-field examples")
print("  - 04_performance_scaling.py: Performance benchmarks")
print("=" * 80)
