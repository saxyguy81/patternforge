# PatternForge User Guide

Comprehensive documentation for PatternForge - a fast, deterministic glob-pattern discovery engine for hierarchical data.

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Single-Field Pattern Matching](#single-field-pattern-matching)
5. [Structured Multi-Field Matching](#structured-multi-field-matching)
6. [Configuration Reference](#configuration-reference)
7. [Performance and Scaling](#performance-and-scaling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

## Introduction

### What is PatternForge?

PatternForge automatically discovers minimal wildcard patterns that match your data. Given a set of "include" items (what you want) and "exclude" items (what you don't want), it generates precise glob patterns using wildcards (`*`).

**Key Features:**
- **Zero false positives** in EXACT mode (guaranteed not to match excludes)
- **Automatic pattern discovery** - no manual regex writing
- **Multi-field support** - patterns across structured data (module/instance/pin)
- **Scalable** - handles 10,000+ rows efficiently
- **Interpretable** - generates human-readable wildcard patterns

**Use Cases:**
- Regression triage (find patterns in failing tests)
- Hardware signal selection (netlists, pin lists)
- Log file filtering
- Database queries on hierarchical data
- Test case categorization

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/patternforge
cd patternforge

# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH=/path/to/patternforge/src:$PYTHONPATH
```

## Quick Start

### Python API - Simplest Usage

```python
from patternforge.engine.solver import propose_solution

# Your data
include = [
    "chip/cpu/l1_cache/bank0",
    "chip/cpu/l1_cache/bank1",
    "chip/cpu/l2_cache/bank0",
]
exclude = [
    "chip/gpu/l1_cache/bank0",
    "chip/cpu/registers/file0",
]

# Generate patterns - defaults to EXACT mode (zero false positives)
solution = propose_solution(include, exclude)

# Inspect results
print(f"Pattern: {solution.raw_expr}")  # *cpu*cache*
print(f"Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
print(f"False positives: {solution.metrics['fp']}")  # 0 in EXACT mode

# Customize with direct parameters - no classes needed!
solution = propose_solution(include, exclude,
    mode="EXACT",        # Zero false positives (string, not enum!)
    max_patterns=5,      # At most 5 patterns
    w_fp=2.0            # Penalize false positives heavily
)
```

**See:** `examples/01_quick_start.py` for complete runnable examples

### CLI Usage

```bash
# Create input files
echo -e "chip/cpu/l1_cache/bank0\nchip/cpu/l1_cache/bank1" > include.txt
echo -e "chip/gpu/l1_cache/bank0" > exclude.txt

# Generate patterns
PYTHONPATH=src python -m patternforge.cli propose \
  --include include.txt \
  --exclude exclude.txt \
  --format json \
  --out solution.json

# View results
jq '.expr, .raw_expr, .metrics' solution.json
```

## Core Concepts

### Pattern Types

PatternForge discovers five types of wildcard patterns:

#### 1. PREFIX Patterns (`token/*`)
- Anchored at start
- 1 wildcard
- **Example:** `video/*` matches `video/display/pixel0`
- **Use when:** All targets share a common prefix

#### 2. SUFFIX Patterns (`*/token`)
- Anchored at end
- 1 wildcard
- **Example:** `*/fail` matches all paths ending in `fail`
- **Use when:** All targets share a common suffix

#### 3. SUBSTRING Patterns (`*token*`)
- Matches anywhere
- 2 wildcards
- **Example:** `*cache*` matches `chip/cpu/l1_cache/bank0`
- **Use when:** Target keyword appears anywhere

#### 4. MULTI-SEGMENT Patterns (`*a*b*c*`)
- Multiple ordered keywords
- Variable wildcards
- **Example:** `*cpu*execute*alu*` requires all three keywords in order
- **Use when:** Need multiple keywords in specific order (more precise)

#### 5. EXACT Patterns
- No wildcards
- Full string match
- **Example:** `chip/cpu/core0` matches only that exact path
- **Use when:** Patterns are identical

**See:** `examples/02_single_field_patterns.py` for detailed examples of each type

### Matching Semantics

**Wildcard Rules:**
- `*` matches any substring (including `/` and empty string)
- Everything else is literal
- Patterns without leading `*` are anchored at start
- Patterns without trailing `*` are anchored at end

**Examples:**
```
Pattern          String                    Match?
-------          ------                    ------
video*           video/display/pixel0      ✓ (prefix)
video*           other/video/display       ✗ (not anchored at start)
*video*          other/video/display       ✓ (substring)
*/pixel0         video/display/pixel0      ✓ (suffix)
*/pixel0         video/display/pixel0/x    ✗ (not anchored at end)
*cpu*cache*      chip/cpu/l1_cache/bank0   ✓ (multi-segment, ordered)
*cache*cpu*      chip/cpu/l1_cache/bank0   ✗ (wrong order)
```

### Quality Modes

#### EXACT Mode (Default)
- **Guarantee:** Zero false positives
- **Trade-off:** May not achieve 100% coverage to avoid FP
- **Use when:** Precision matters more than recall
- **Speed:** Slower (explores more combinations)

```python
solution = propose_solution(include, exclude, mode="EXACT")
```

#### APPROX Mode
- **Behavior:** Allows some false positives for simpler patterns
- **Trade-off:** Faster, but may match exclude items
- **Use when:** Speed matters and some FP acceptable
- **Speed:** 2-10x faster

```python
solution = propose_solution(include, exclude, mode="APPROX")
```

**See:** `examples/01_quick_start.py` Example 3

## Single-Field Pattern Matching

For hierarchical paths or flat strings where you want to match entire strings.

### Basic Example

```python
from patternforge.engine.solver import propose_solution

include = [
    "regress/nightly/ipA/test_fifo/rand_smoke/fail",
    "regress/nightly/ipA/test_dma/burst_test/fail",
    "regress/nightly/ipB/test_cache/assoc16/fail",
]
exclude = [
    "regress/nightly/ipA/test_fifo/rand_smoke/pass",
    "regress/nightly/ipB/test_cache/assoc16/pass",
]

# Generate patterns (defaults to EXACT mode)
solution = propose_solution(include, exclude)

# Result: Pattern that matches all "fail" paths but no "pass" paths
print(solution.raw_expr)  # likely: *fail*
```

### Inverted Patterns (NOT Logic)

Sometimes it's easier to specify what you DON'T want:

```python
# Find everything EXCEPT debug paths
solution = propose_solution(
    include,  # All your paths
    exclude,  # Debug paths
    invert="always"  # Force inverted mode
)

# global_inverted=True means: "everything EXCEPT <pattern>"
print(solution.global_inverted)  # True
print(solution.raw_expr)  # *debug*
# Interpretation: Match everything EXCEPT paths with "debug"
```

**Inversion Strategies:**
- `"never"`: Normal mode (find what matches)
- `"always"`: Complement mode (everything except pattern)
- `"auto"`: Solver chooses based on cost (default)

**See:** `examples/02_single_field_patterns.py` Example 6

### Tokenization

Tokenization controls how patterns are generated from your data. It doesn't affect matching (patterns still use wildcard rules), only candidate generation.

#### splitmethod='classchange' (Default)
Splits on character class changes (alpha, digit, other):
- `SRAMController_512x64` → `[sram, controller, 512, x, 64]`
- `chip/cpu/core0` → `[chip, cpu, core, 0]`

#### splitmethod='char'
Splits into individual characters:
- `chip/cpu/core0` → `[c, h, i, p, /, c, p, u, /, c, o, r, e, 0]`
- Useful for finding character-level patterns
- Automatically uses `min_token_len=1` (ignores global `min_token_len` setting)

```python
# Use classchange for CamelCase, numbers (RECOMMENDED)
solution = propose_solution(include, exclude, splitmethod='classchange')

# Use char for character-level patterns (advanced use)
solution = propose_solution(include, exclude, splitmethod='char')
```

**See:** `examples/02_single_field_patterns.py` Example 8

## Structured Multi-Field Matching

For data with multiple fields (like database rows, hardware signals with module/instance/pin, etc.).

### Basic Example

```python
from patternforge.engine.solver import propose_solution_structured

include_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DOUT[0]"},
]
exclude_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "CLK"},
    {"module": "SRAM_512x64", "instance": "chip/gpu/shader0/cache", "pin": "DIN[0]"},
]

solution = propose_solution_structured(include_rows, exclude_rows)

# Atoms have 'field' attribute showing which field they match
for pattern in solution['patterns']:
    print(f"{pattern['field']}: {pattern['text']}")
# Output might be:
#   pin: *DIN* | *DOUT*
#   instance: *cpu*
```

**Key Differences from Single-Field:**
- Patterns apply to individual fields, not concatenated string
- Each pattern has a `field` attribute
- More precise (can filter on field combinations)

**See:** `examples/03_structured_patterns.py` for 7 comprehensive examples

### Field Weights

Prefer patterns on certain fields over others:

```python
solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    w_field={
        "pin": 3.0,      # Strongly prefer pin patterns
        "module": 1.5,   # Moderately prefer module patterns
        "instance": 0.3  # Discourage instance patterns (too broad)
    }
)
```

**How it works:**
- `w_field` multiplies pattern scores during candidate generation
- Higher weight = more likely to select patterns on that field
- Unspecified fields default to 1.0
- Typical range: 0.1 (discourage) to 5.0 (strongly prefer)

**See:** `examples/04_performance_scaling.py` Test Suite 5

### Per-Field Tokenization

Different fields may need different tokenization:

```python
solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    splitmethod={
        "instance": "char",        # Split paths on /
        "module": "classchange",   # Split CamelCase
        "pin": "char"             # Split bus notation DIN[0]
    },
    min_token_len={              # Can also be per-field!
        "instance": 2,
        "module": 3,
        "pin": 2
    }
)
```

**See:** `examples/03_structured_patterns.py` uses per-field tokenization

### None/NaN Wildcards in Excludes

Use `None` (or `NaN` in DataFrames) to create "don't care" fields in excludes:

```python
exclude_rows = [
    {"module": None, "instance": "debug/*", "pin": None},
    # Excludes ANY module/pin on debug instances
]

# With pandas DataFrame
import pandas as pd
import numpy as np

df_exclude = pd.DataFrame({
    'module': [np.nan, '*SRAM*'],
    'instance': ['debug/*', np.nan],
    'pin': [np.nan, 'CLK']
})
# Row 1: Exclude debug instances regardless of module/pin
# Row 2: Exclude CLK pin on any SRAM module, any instance
```

**See:** STRUCTURED_SOLVER_GUIDE.md Section 4

## Configuration Reference

All configuration is done via direct keyword arguments to `propose_solution()` and `propose_solution_structured()`.

### Core Settings

```python
solution = propose_solution(include, exclude,
    # Quality & Mode
    mode="EXACT",          # or "APPROX" (case-insensitive)
    effort="medium",       # "low", "medium", "high", "exhaustive"
    invert="auto",         # "never", "auto", "always"

    # Tokenization (can be string or dict for per-field)
    splitmethod="classchange",  # or "char", or {"field": "method"}
    min_token_len=3,            # or {"field": int}

    # Candidate generation
    per_word_substrings=16,     # Substrings per token
    max_multi_segments=3,       # Multi-segment pattern limit
    allowed_patterns=None,      # or ["prefix", "suffix", "substring"]

    # Hard constraints (budgets)
    max_candidates=4000,        # Max candidates to consider
    max_patterns=None,          # Max patterns (int or 0<float<1 for %)
    max_fp=0,                   # Max FP (int or percentage)
    max_fn=None,                # Max FN (int or percentage)

    # Soft penalties (weights) - scalar or dict
    w_field={"pin": 2.0},       # Field preference (structured only, always dict)
    w_fp=1.0,                   # FP cost (scalar or dict)
    w_fn=1.0,                   # FN cost (scalar or dict)
    w_pattern=0.05,             # Pattern complexity cost
    w_op=0.02,                  # Operator complexity cost
    w_wc=0.01,                  # Wildcard cost
    w_len=0.001,                # Length cost

    # Advanced
    allow_complex_expressions=False,  # Allow conjunctive expressions
)
```

### Parameter Details

#### Quality & Mode

**mode**: `"EXACT"` or `"APPROX"` (case-insensitive)
- **EXACT**: Zero false positives (guaranteed)
- **APPROX**: Allows some FP for simpler patterns (2-10x faster)

**effort**: `"low"`, `"medium"`, `"high"`, `"exhaustive"`
- Controls quality vs speed trade-off
- **low**: Fastest, single-field only
- **medium**: Balanced (default)
- **high**: Best quality, slower
- **exhaustive**: Try everything (small datasets only)

**invert**: `"never"`, `"auto"`, `"always"`
- **never**: Normal mode (find what matches)
- **always**: Complement mode (everything except pattern)
- **auto**: Solver chooses based on cost (default)

#### Budget Constraints (Hard Limits)

These are hard constraints that the solver MUST satisfy:

**max_candidates**: int (default: 4000)
- Maximum candidate patterns to consider
- Higher = more thorough search, slower

**max_patterns**: int or float (default: None)
- Maximum patterns in solution
- `8` = at most 8 patterns
- `0.10` = at most 10% of include rows
- `None` = no limit

**max_fp**: int or float (default: 0 in EXACT mode)
- Maximum false positives allowed
- `0` = zero FP (EXACT mode automatic)
- `5` = at most 5 false positives
- `0.01` = at most 1% FP
- `None` = no limit

**max_fn**: int or float (default: None)
- Maximum false negatives allowed
- `0` = full coverage required
- `0.05` = at most 5% FN
- `None` = no limit

**Percentage Interpretation:**
- `0 < value < 1`: Percentage of include rows
- `value >= 1`: Absolute count
- `0`: Zero (exact)
- `None`: No limit

#### Weights (Soft Penalties)

These affect the cost function used during greedy selection:

**w_field**: dict[str, float] (structured only, default: {})
- Field preference during candidate generation
- Higher weight = prefer patterns on this field
- Example: `{"pin": 3.0, "module": 1.5, "instance": 0.3}`
- Range: 0.1 (discourage) to 5.0 (strongly prefer)

**w_fp**: float or dict (default: 1.0)
- Cost per false positive
- Can be per-field: `{"module": 2.0, "pin": 1.0}`
- Higher = penalize FP more heavily

**w_fn**: float or dict (default: 1.0)
- Cost per false negative
- Can be per-field for structured data

**w_pattern**: float or dict (default: 0.05)
- Cost per pattern in solution
- Higher = prefer fewer patterns (simpler solutions)

**w_op**: float or dict (default: 0.02)
- Cost per boolean operation (OR between patterns)

**w_wc**: float or dict (default: 0.01)
- Cost per wildcard character

**w_len**: float or dict (default: 0.001)
- Cost per character length

**Weight Usage:**
- All weights can be scalar (apply globally) or dict (per-field for structured data)
- `w_field` is always dict (structured mode only)
- Higher weight = higher penalty = less likely to use

#### Pattern Generation

**allowed_patterns**: list[str] or None (default: None)
- Restrict pattern types
- Values: `"exact"`, `"substring"`, `"prefix"`, `"suffix"`, `"multi"`
- Example: `["prefix", "suffix"]` (only prefix/suffix patterns)
- `None` = allow all types

**min_token_len**: int or dict (default: 3)
- Minimum token length to consider
- Can be per-field: `{"module": 3, "pin": 2}`

**splitmethod**: str or dict (default: "classchange")
- Tokenization method
- `"classchange"`: Split on character class changes (alpha/digit/other) - RECOMMENDED
- `"char"`: Split into individual characters (advanced - for character-level patterns)
- Can be per-field: `{"instance": "char", "module": "classchange"}`
- Note: `splitmethod='char'` automatically uses `min_token_len=1`

**per_word_substrings**: int (default: 16)
- Top N substrings per token to consider

**max_multi_segments**: int (default: 3)
- Maximum segments in multi-segment patterns like `*a*b*c*`

**allow_complex_expressions**: bool (default: False)
- Allow conjunctive expressions (A & B) and subtraction (A - B)
- More expressive but potentially more complex solutions

## Performance and Scaling

### Algorithm Selection

PatternForge automatically selects the best algorithm based on dataset size:

| N (rows) | F (fields) | Effort | Algorithm | Complexity |
|----------|------------|--------|-----------|------------|
| < 100 | < 5 | exhaustive | EXHAUSTIVE | O(N²) |
| < 1k | < 8 | medium/high | BOUNDED | O(N) |
| ≥ 1k or ≥ 8 | any | any | SCALABLE | O(N) |
| any | any | low | SCALABLE | O(N) |

**BOUNDED Algorithm:**
- Row-centric expression generation
- Suitable for small-medium datasets
- Caps: 1000-2000 total expressions, 50-100 per row

**SCALABLE Algorithm:**
- Pattern-centric with lazy multi-field construction
- Suitable for large datasets
- Caps: 20-200 patterns per field

### Performance Characteristics

From `examples/04_performance_scaling.py`:

**Single-Field:**
```
N          Time      Atoms
10         ~0.01s    1-2
1,000      ~0.2s     2-5
10,000     ~2s       5-15
```

**Structured Multi-Field:**
```
N          Time      Atoms
10         ~0.01s    1-3
1,000      ~0.5s     3-8
10,000     ~5s       5-20
```

**Mode Comparison (N=1000):**
```
Mode       Time      FP    Atoms
EXACT      0.3s      0     5
APPROX     0.1s      2     3
Speedup: 3x faster
```

**See:** `examples/04_performance_scaling.py` for comprehensive benchmarks

## Best Practices

### When to Use Single-Field vs Structured

**Use Single-Field When:**
- Data is flat hierarchical paths (no natural field structure)
- You want patterns on full string concatenation
- Simpler problem, don't need field-level precision

**Use Structured When:**
- Data has natural field structure (module/instance/pin, database columns)
- You need per-field patterns
- Want to prefer/discourage specific fields
- More precise filtering requirements

### Choosing Quality Mode

**Use EXACT When:**
- Zero false positives required
- Precision > recall
- Dataset size manageable (< 10k rows)

**Use APPROX When:**
- Speed matters
- Some false positives acceptable
- Large datasets (> 10k rows)
- Exploratory analysis

### Field Weight Guidelines

**High weights (2.0-5.0):**
- Fields with discriminating patterns
- Fields that should dominate selection
- Example: `pin` field in hardware signals

**Low weights (0.1-0.5):**
- Fields with many similar values
- Fields that create too-broad patterns
- Example: `instance` paths that match too much

**Default weight (1.0):**
- Neutral preference

### Budget Settings

**max_patterns:**
- Start with `None` (no limit)
- If too many patterns, set to 5-10 for simplicity
- Or use percentage: `0.05` for 5% of rows max

**max_fp / max_fn:**
- EXACT mode: `max_fp=0` (automatic)
- APPROX mode: `max_fp=0.01` for 1% tolerance
- Full coverage: `max_fn=0`

## Troubleshooting

### Patterns Too Broad

**Symptoms:** Matches too many items, high FP

**Solutions:**
1. Use EXACT mode instead of APPROX
2. Add more exclude examples
3. Increase field weights (structured mode)
4. Decrease `max_fp` budget
5. Increase `w_fp` weight

### Patterns Too Specific

**Symptoms:** Too many patterns, low coverage

**Solutions:**
1. Use APPROX mode
2. Decrease `max_patterns` budget
3. Increase `w_pattern` cost
4. Add `max_fn` budget to allow some FN
5. Use lower effort level

### Slow Performance

**Symptoms:** Takes too long to complete

**Solutions:**
1. Use APPROX mode (2-10x faster)
2. Use `effort="low"`
3. Reduce `max_candidates` (default 4000)
4. For large datasets (>10k), ensure using APPROX + low effort
5. Check dataset size - structured mode slower for >5k rows

### Wrong Fields Selected

**Symptoms:** (Structured mode) Patterns on wrong fields

**Solutions:**
1. Adjust `w_field` weights
   ```python
   solution = propose_solution_structured(include, exclude,
       w_field={"desired_field": 3.0, "wrong_field": 0.3}
   )
   ```
2. Increase `w_fp` for wrong field
   ```python
   solution = propose_solution_structured(include, exclude,
       w_fp={"wrong_field": 5.0, "desired_field": 1.0}
   )
   ```
3. Add more exclude examples that use wrong field

### No Solution Found

**Symptoms:** Empty solution or no patterns

**Solutions:**
1. Check if include/exclude have overlap (unsolvable)
2. Relax budgets (`max_patterns=None`, `max_fn` tolerance)
3. Lower `min_token_len` (default=3)
4. Check tokenization method (try both `classchange` and `char`)

## Advanced Topics

### Custom Tokenization

For complete control over tokenization, provide custom `token_iter`:

```python
from patternforge.engine.tokens import Token, make_split_tokenizer, iter_structured_tokens_with_fields

# Per-field custom tokenizers
tk_module = make_split_tokenizer("classchange", min_token_len=3)
tk_instance = make_split_tokenizer("char", min_token_len=2)
tk_pin = make_split_tokenizer("char", min_token_len=2)

field_tokenizers = {"module": tk_module, "instance": tk_instance, "pin": tk_pin}

token_iter = list(iter_structured_tokens_with_fields(
    include_rows,
    field_tokenizers,
    field_order=["module", "instance", "pin"]
))

solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    token_iter=token_iter  # Pass custom tokens
)
```

**See:** README.md "Advanced: custom tokenizers (per-field)" section

### Boolean Expressions

The evaluator supports complex boolean logic:

```python
from patternforge.engine.solver import evaluate_expr

patterns = {
    "P1": "*cpu*",
    "P2": "*cache*",
    "P3": "*debug*"
}

# AND
metrics = evaluate_expr("P1 & P2", patterns, include, exclude)

# OR
metrics = evaluate_expr("P1 | P2", patterns, include, exclude)

# NOT
metrics = evaluate_expr("!P3", patterns, include, exclude)

# Complex
metrics = evaluate_expr("(P1 & P2) & !P3", patterns, include, exclude)
```

### Persistence

Save and load solutions:

```python
from patternforge import io

# Convert solution to dict for saving
solution_dict = solution.to_json()
io.save_solution(solution_dict, "solution.json")

# Load
loaded = io.load_solution("solution.json")

# Extract just patterns for evaluation
patterns_dict = {pattern["id"]: pattern["text"] for pattern in loaded["patterns"]}
```

### DataFrame Support

Direct pandas/polars support:

```python
import pandas as pd

df_include = pd.DataFrame({
    'module': ['SRAM_512x64', 'SRAM_1024x32'],
    'instance': ['cpu/l1_cache/bank0', 'cpu/l2_cache/bank0'],
    'pin': ['DIN[0]', 'DOUT[0]']
})

solution = propose_solution_structured(df_include, df_exclude)
# Auto-detects columns as fields!
```

### Explanation and Visualization

Generate human-readable explanations:

```python
from patternforge.engine.explain import explain_text, explain_dict

# Text format
explanation = explain_text(solution, include, exclude)
print(explanation)

# Dict format (programmatic)
summary = explain_dict(solution, include, exclude)
print(summary["expr"], summary["metrics"])
```

## Additional Resources

- **Examples:** See `examples/` directory for runnable code
- **Structured Guide:** See `STRUCTURED_SOLVER_GUIDE.md` for multi-field deep dive
- **README:** See `README.md` for CLI usage and quick reference
- **Tests:** See `tests/` for extensive usage patterns
- **API Reference:** See source code docstrings in `src/patternforge/engine/`

## Getting Help

1. Check this guide and examples first
2. Review the troubleshooting section
3. Run the relevant example file to see expected behavior
4. Check the issue tracker: https://github.com/anthropics/patternforge/issues

## Contributing

Contributions welcome! Please:
1. Add tests for new features
2. Update documentation
3. Add example if demonstrating new capability
4. Follow existing code style
