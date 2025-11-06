#!/usr/bin/env python3
"""Diagnostic script to investigate EXACT mode false positives."""

import sys
sys.path.insert(0, "src")

from patternforge.engine.solver import propose_solution
from patternforge.engine.matcher import match_pattern

def investigate_exact_mode_bug():
    """Investigate the EXACT mode bug with array indices."""
    print("=" * 80)
    print("INVESTIGATING EXACT MODE BUG")
    print("=" * 80)

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

    print("\nInclude:")
    for i in include:
        print(f"  {i}")

    print("\nExclude:")
    for i in exclude:
        print(f"  {i}")

    solution = propose_solution(include, exclude, mode="EXACT")

    print(f"\n{'='*80}")
    print("SOLUTION DETAILS")
    print('='*80)
    print(f"Mode: {solution.mode}")
    print(f"Expression: '{solution.expr}'")
    print(f"Raw expression: '{solution.raw_expr}'")
    print(f"Number of patterns: {len(solution.patterns)}")

    print(f"\nMetrics:")
    for key, value in solution.metrics.items():
        print(f"  {key}: {value}")

    print(f"\nPatterns list:")
    if len(solution.patterns) == 0:
        print("  <EMPTY - NO PATTERNS!>")
    for i, pattern in enumerate(solution.patterns):
        print(f"  {i}: {pattern}")

    print(f"\nFull solution.__dict__:")
    for key, value in solution.__dict__.items():
        if key != 'patterns':  # Already printed above
            print(f"  {key}: {value}")

    # Test the expression
    if solution.expr:
        print(f"\n{'='*80}")
        print(f"Testing expression: '{solution.expr}'")
        print('='*80)
        print("Include matches:")
        for inc in include:
            matches = match_pattern(inc, solution.expr)
            print(f"  {inc}: {matches}")

        print("\nExclude matches (should all be False!):")
        for exc in exclude:
            matches = match_pattern(exc, solution.expr)
            status = "✗ FALSE POSITIVE" if matches else "✓ Correct"
            print(f"  {exc}: {matches} {status}")

if __name__ == "__main__":
    investigate_exact_mode_bug()
