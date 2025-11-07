#!/usr/bin/env python3
"""Investigate the splitmethod='char' behavior."""

import sys
sys.path.insert(0, "src")

from patternforge.engine.solver import propose_solution

def test_simple_case():
    """Test the simple instance list case."""
    print("=" * 80)
    print("INVESTIGATING SPLITMETHOD='char' ISSUE")
    print("=" * 80)

    include = [
        "pd_domain/moduleA/sub1/mem/i0",
        "pd_domain/moduleA/sub2/mem/i0",
        "pd_domain/moduleA/sub3/mem/i0",
    ]
    exclude = []

    print("\nInput:")
    print(f"  Include: {include}")
    print(f"  Exclude: {exclude}")

    print("\n" + "=" * 80)
    print("WITH splitmethod='char'")
    print("=" * 80)
    solution_char = propose_solution(include, exclude, splitmethod='char')

    print(f"Expression: '{solution_char.expr}'")
    print(f"Raw expression: '{solution_char.raw_expr}'")
    print(f"Global inverted: {solution_char.global_inverted}")
    print(f"Term method: {solution_char.term_method}")
    print(f"Number of patterns: {len(solution_char.patterns)}")
    print(f"Metrics: {solution_char.metrics}")

    print("\nInterpretation:")
    if solution_char.global_inverted:
        print(f"  ⚠️  global_inverted=True means the actual pattern is: NOT ({solution_char.expr})")
        print(f"  ⚠️  'NOT (FALSE)' = 'TRUE' = matches EVERYTHING")
        print(f"  ⚠️  This explains coverage={solution_char.metrics['covered']}")

    print("\n" + "=" * 80)
    print("WITH splitmethod='classchange'")
    print("=" * 80)
    solution_class = propose_solution(include, exclude, splitmethod='classchange')

    print(f"Expression: '{solution_class.expr}'")
    print(f"Raw expression: '{solution_class.raw_expr}'")
    print(f"Global inverted: {solution_class.global_inverted}")
    print(f"Term method: {solution_class.term_method}")
    print(f"Number of patterns: {len(solution_class.patterns)}")
    print(f"Metrics: {solution_class.metrics}")
    print(f"Patterns: {[p.text for p in solution_class.patterns]}")

    print("\n" + "=" * 80)
    print("WHY THE DIFFERENCE?")
    print("=" * 80)
    print(f"""
splitmethod='char':
  - Splits on delimiters like '/', creating tokens: ['pd', 'domain', 'moduleA', 'sub1', 'mem', 'i0']
  - With default min_token_len=3, very short tokens might be filtered
  - May not find good discriminative patterns
  - Falls back to inverted solution: 'NOT (FALSE)' = match everything

splitmethod='classchange':
  - Splits on case changes, creating different tokens
  - Finds useful pattern '*sub*' that matches all 3 items
  - No need for inversion
    """)

    print("\n" + "=" * 80)
    print("IS THIS A BUG?")
    print("=" * 80)
    print("""
The behavior is TECHNICALLY CORRECT but CONFUSING:

✅ Correct semantics:
   - 'NOT (FALSE)' does match everything
   - With empty exclude list, fp=0 is correct
   - Coverage=3/3 is correct

❌ Confusing presentation:
   - Expression shows "FALSE" but actually means "NOT FALSE"
   - Users see 0 patterns but full coverage
   - Relies on understanding the global_inverted flag

POSSIBLE FIX:
Should we disable inversion when exclude list is empty?
Or improve output to show "NOT (FALSE)" instead of just "FALSE"?
    """)

if __name__ == "__main__":
    test_simple_case()
