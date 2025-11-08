#!/usr/bin/env python3
"""Debug the memory instances test to see what patterns are generated."""

from src.patternforge.engine.solver import propose_solution_structured

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

print("=" * 80)
print("MEMORY INSTANCES TEST - PATTERN ANALYSIS")
print("=" * 80)

print("\nINCLUDE (want to match):")
for i, row in enumerate(include, 1):
    print(f"  {i}. module={row['module']}, instance={row['instance']}, pin={row['pin']}")

print("\nEXCLUDE (want to avoid):")
for i, row in enumerate(exclude, 1):
    print(f"  {i}. module={row['module']}, instance={row['instance']}, pin={row['pin']}")

print("\n" + "=" * 80)
print("OPTIMAL SOLUTION ANALYSIS:")
print("=" * 80)
print("\nThe optimal solution should be:")
print("  - Single pattern: module=SRAM AND instance=*/fabric/dart/* AND pin=DIN")
print("  - This covers all 4 includes and excludes all 3 excludes")
print("  - Breakdown:")
print("    - module=SRAM excludes row 3 (DRAM)")
print("    - instance=*/fabric/dart/* excludes rows 1-2 (asio_spis, asio_uarts)")

solution = propose_solution_structured(include, exclude, mode="EXACT")

print("\n" + "=" * 80)
print("ACTUAL SOLUTION:")
print("=" * 80)

print(f"\nMetrics:")
print(f"  Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
print(f"  False Positives: {solution.metrics['fp']}")
print(f"  False Negatives: {solution.metrics['fn']}")
print(f"  Number of Patterns: {solution.metrics['patterns']}")
print(f"  Number of Expressions: {len(solution.expressions)}")

print(f"\nPatterns generated ({len(solution.patterns)} total):")
for i, p in enumerate(solution.patterns, 1):
    matches = f", matches={p.matches}" if p.matches is not None else ""
    fp = f", fp={p.fp}" if p.fp is not None else ""
    print(f"  {i}. field={p.field}, pattern='{p.text}', kind={p.kind}, wildcards={p.wildcards}{matches}{fp}")

print(f"\nExpressions (terms):")
for i, expr in enumerate(solution.expressions, 1):
    fields = expr.get('fields', {})
    matches = expr.get('matches', 0)
    fp = expr.get('fp', 0)
    incremental = expr.get('incremental_matches', 0)
    print(f"  {i}. {fields}")
    print(f"      matches={matches}, fp={fp}, incremental_matches={incremental}")

print(f"\nRaw expression:")
print(f"  {solution.raw_expr}")

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)

# Check if we're getting the optimal solution
has_fabric_dart = any("fabric" in p.text and "dart" in p.text for p in solution.patterns if p.field == "instance")
has_module_sram = any(p.text == "sram" and p.field == "module" for p in solution.patterns)

print(f"\nHas optimal instance pattern (fabric/dart): {has_fabric_dart}")
print(f"Has optimal module pattern (sram): {has_module_sram}")

if solution.metrics['patterns'] > 5:
    print(f"\n⚠ WARNING: Generated {solution.metrics['patterns']} patterns (expected ≤5)")
    print("This suggests the algorithm is not finding the optimal solution.")
    print("\nPossible causes:")
    print("  1. Pattern generation not creating the optimal candidate")
    print("  2. Greedy selection choosing suboptimal patterns")
    print("  3. Cost function favoring wrong patterns")
else:
    print(f"\n✓ Good: Generated {solution.metrics['patterns']} patterns (within expected range)")
