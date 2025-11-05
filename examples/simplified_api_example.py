#!/usr/bin/env python3
"""
Example demonstrating the simplified structured API.

This shows how the new unified API consolidates all configuration into SolveOptions,
with field preferences via w_field and support for per-field customization.
"""

import sys
sys.path.insert(0, "../src")

from patternforge.engine.solver import propose_solution_structured
from patternforge.engine.models import SolveOptions, OptimizeWeights

print("=" * 80)
print("SIMPLIFIED STRUCTURED API EXAMPLES")
print("=" * 80)

# Sample data: SRAM pins in cache hierarchy
include_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[31]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DOUT[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DOUT[31]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DOUT[0]"},
]

exclude_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "CLK"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "WEN"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "CEN"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DOUT[0]"},
]

print("\n" + "=" * 80)
print("EXAMPLE 1: Simplest Usage (Auto-Detection)")
print("=" * 80)
print("\nBefore (old API - 10+ lines):")
print("""
from patternforge.engine.solver import propose_solution_structured
from patternforge.engine.models import SolveOptions
from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields

tokenizer = make_split_tokenizer("classchange", min_token_len=3)
field_tokenizers = {"module": tokenizer, "instance": tokenizer, "pin": tokenizer}
token_iter = list(iter_structured_tokens_with_fields(
    include_rows, field_tokenizers, field_order=["module", "instance", "pin"]
))
solution = propose_solution_structured(
    include_rows, exclude_rows, SolveOptions(splitmethod="classchange"), token_iter=token_iter
)
""")

print("After (new API - 1 line):")
print("""
solution = propose_solution_structured(include_rows, exclude_rows)
""")

solution = propose_solution_structured(include_rows, exclude_rows)

print(f"\nResult:")
print(f"  Expression: {solution['raw_expr']}")
print(f"  Coverage: {solution['metrics']['covered']}/{solution['metrics']['total_positive']}")
print(f"  False Positives: {solution['metrics']['fp']}")
print(f"  Patterns: {len(solution['atoms'])}")
for atom in solution['atoms']:
    field = atom.get('field', 'N/A')
    print(f"    {field:10s}: {atom['text']:25s} ({atom['kind']})")

print("\n" + "=" * 80)
print("EXAMPLE 2: Field Weights (Prefer Specific Fields)")
print("=" * 80)
print("""
Prefer patterns on 'pin' field over 'instance' field:
- pin weight: 2.0 (high priority)
- instance weight: 0.5 (low priority - discourage broad instance patterns)
- module weight: default 1.0
""")

print("\nCode:")
print("""
solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        weights=OptimizeWeights(
            w_field={"pin": 2.0, "instance": 0.5}
        )
    )
)
""")

solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        weights=OptimizeWeights(
            w_field={"pin": 2.0, "instance": 0.5}
        )
    )
)

print(f"\nResult:")
print(f"  Expression: {solution['raw_expr']}")
print(f"  Coverage: {solution['metrics']['covered']}/{solution['metrics']['total_positive']}")
print(f"  False Positives: {solution['metrics']['fp']}")
for atom in solution['atoms']:
    field = atom.get('field', 'N/A')
    print(f"    {field:10s}: {atom['text']:25s} ({atom['kind']})")

print("\n" + "=" * 80)
print("EXAMPLE 3: Per-Field Tokenization Methods")
print("=" * 80)
print("""
Use different tokenization per field:
- instance: 'char' (split on / for hierarchical paths)
- module: 'classchange' (split on case changes)
- pin: 'char' (split on [ and ] for bus notation)
""")

print("\nCode:")
print("""
solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        splitmethod={
            "instance": "char",
            "module": "classchange",
            "pin": "char"
        }
    )
)
""")

solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        splitmethod={"instance": "char", "module": "classchange", "pin": "char"}
    )
)

print(f"\nResult:")
print(f"  Expression: {solution['raw_expr']}")
print(f"  Coverage: {solution['metrics']['covered']}/{solution['metrics']['total_positive']}")
print(f"  False Positives: {solution['metrics']['fp']}")
for atom in solution['atoms']:
    field = atom.get('field', 'N/A')
    print(f"    {field:10s}: {atom['text']:25s} ({atom['kind']})")

print("\n" + "=" * 80)
print("EXAMPLE 4: Combined - Field Weights + Per-Field Tokenization")
print("=" * 80)

print("\nCode:")
print("""
solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        weights=OptimizeWeights(
            w_field={"pin": 2.0, "module": 1.5, "instance": 0.3}
        ),
        splitmethod={"instance": "char", "module": "classchange", "pin": "char"}
    )
)
""")

solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        weights=OptimizeWeights(
            w_field={"pin": 2.0, "module": 1.5, "instance": 0.3}
        ),
        splitmethod={"instance": "char", "module": "classchange", "pin": "char"}
    )
)

print(f"\nResult:")
print(f"  Expression: {solution['raw_expr']}")
print(f"  Coverage: {solution['metrics']['covered']}/{solution['metrics']['total_positive']}")
print(f"  False Positives: {solution['metrics']['fp']}")
for atom in solution['atoms']:
    field = atom.get('field', 'N/A')
    print(f"    {field:10s}: {atom['text']:25s} ({atom['kind']})")

print("\n" + "=" * 80)
print("KEY FEATURES:")
print("=" * 80)
print("""
✅ Auto-detect fields from dict keys
✅ Auto-generate tokenizers from splitmethod
✅ Support DataFrame input (pandas, polars)
✅ Field weights to prefer patterns on certain fields
✅ Per-field tokenization control
✅ Default to EXACT mode (zero false positives)
✅ Case-insensitive matching
✅ 90% reduction in boilerplate code
✅ Backward compatible with advanced options

API Reduction:
  Before: 10+ lines of imports, tokenizer setup, token_iter generation
  After:  1 line for common case, 2-3 lines for advanced features
""")
