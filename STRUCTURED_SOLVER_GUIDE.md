# PatternForge Structured Solver - Complete Feature Guide

## Overview

The structured solver generates conjunctive expressions (multi-field patterns) for matching structured data like hardware signals, database rows, or any multi-field records.

### Key Concepts

**Terminology**:
- **Term**: A single field pattern (e.g., `module: *sram*`)
- **Expression**: A conjunction of terms (e.g., `(module: *sram*) & (instance: *cpu*)`)
- **Solution**: A disjunction of expressions (e.g., `expr1 | expr2`)

**Example**:
```
Input: 4 rows with fields [module, instance, pin]
Output: ((module: sram_512x64) & (instance: *cpu*) & (pin: *din*))
         ↑ One expression covering all 4 rows
```

## All Features

### ✅ 1. Expression-Based Generation

Generates conjunctive multi-field patterns instead of flat field patterns.

```python
include = [
    {"module": "SRAM", "instance": "cpu/cache", "pin": "DIN"},
    {"module": "SRAM", "instance": "cpu/cache", "pin": "DOUT"},
    {"module": "SRAM", "instance": "gpu/cache", "pin": "DIN"},
]
exclude = [
    {"module": "SRAM", "instance": "cpu/cache", "pin": "CLK"},
]

solution = propose_solution_structured(include, exclude)
# Result: Fewer expressions, each covering multiple rows
```

### ✅ 2. Field Weights and Per-Field Parameters

Prefer patterns on certain fields and customize parameters per field.

```python
# Field preference weights (multiplies pattern scores during candidate generation)
solution = propose_solution_structured(
    include, exclude,
    w_field={
        "module": 2.0,      # High priority
        "pin": 2.0,         # High priority
        "instance": 0.5     # Low priority (discourage)
    }
)
# Will prefer patterns on module/pin rather than instance

# All weights can be per-field! Unspecified fields default to 1.0
solution = propose_solution_structured(
    include, exclude,
    w_fp={"module": 2.0, "pin": 1.0, "instance": 0.5},  # Per-field FP cost
    w_fn=1.0,                                             # Global FN cost
    w_pattern={"pin": 0.1, "module": 0.05},              # Per-field pattern cost
)
```

### ✅ 3. Per-Field Tokenization

Different tokenization methods for different fields.

```python
solution = propose_solution_structured(
    include, exclude,
    splitmethod={
        "instance": "char",        # Split on / for paths
        "module": "classchange",   # Split on case changes
        "pin": "char"             # Split on [ and ]
    },
    min_token_len={              # Can also be per-field!
        "instance": 2,
        "module": 3,
        "pin": 2
    }
)
```

### ✅ 4. None/NaN Wildcard Support

Use None or NaN for "don't care" fields in excludes.

```python
exclude = [
    {"module": None, "instance": "debug/*", "pin": None},
    # Excludes ANY module/pin on debug instances

    {"module": "*SRAM*", "instance": None, "pin": "CLK"},
    # Excludes CLK pin on any SRAM module, any instance
]

solution = propose_solution_structured(include, exclude)
```

Works with DataFrame inputs (NaN values):
```python
import pandas as pd
import numpy as np

df_exclude = pd.DataFrame({
    'module': [np.nan, '*SRAM*'],
    'instance': ['debug/*', np.nan],
    'pin': [np.nan, 'CLK']
})

solution = propose_solution_structured(df_include, df_exclude)
```

### ✅ 5. DataFrame Input Support

Direct pandas/polars DataFrame support.

```python
import pandas as pd

df = pd.DataFrame({
    'module': ['SRAM', 'SRAM', 'SRAM'],
    'instance': ['cpu/cache', 'cpu/cache', 'gpu/cache'],
    'pin': ['DIN', 'DOUT', 'DIN']
})

solution = propose_solution_structured(df, df_exclude)
# Auto-detects fields from columns
```

### ✅ 6. Percentage-Based Budgets

Specify constraints as percentages or absolute counts.

```python
# Allow up to 1% false positives
solution = propose_solution_structured(
    include, exclude,
    max_fp=0.01,     # 1% of include rows
    max_fn=0.0,      # 0 false negatives (exact)
    max_patterns=0.10   # Use at most 10% of rows as patterns
)

# Or use absolute counts
solution = propose_solution_structured(
    include, exclude,
    max_fp=5,        # At most 5 false positives
    max_fn=None,     # No limit on false negatives
    max_patterns=8   # At most 8 patterns
)
```

### ✅ 7. Adaptive Algorithm Selection

Automatically selects best algorithm based on dataset size.

**Decision Matrix**:
| N (rows) | F (fields) | Effort | Algorithm | Complexity |
|----------|------------|--------|-----------|------------|
| < 100 | < 5 | exhaustive | EXHAUSTIVE | O(N²) |
| < 1k | < 8 | medium/high | BOUNDED | O(N) |
| ≥ 1k or ≥ 8 | any | any | SCALABLE | O(N) |
| any | any | low | SCALABLE | O(N) |

**Transparent to user** - just works optimally!

### ✅ 8. Effort Level Parameter

Control complexity vs quality trade-off.

```python
# Fast mode - for quick results
solution = propose_solution_structured(
    large_dataset,  # 10k rows
    large_excludes,
    effort="low"  # O(N), single-field only, ~1s
)

# Default - balanced
solution = propose_solution_structured(
    include, exclude,
    effort="medium"  # Adaptive, multi-field when needed
)

# Best quality - for important use cases
solution = propose_solution_structured(
    include, exclude,
    effort="high"  # More candidates, multi-field, ~10x slower
)

# Exhaustive - try everything (small datasets only)
solution = propose_solution_structured(
    tiny_include,   # < 100 rows
    tiny_exclude,
    effort="exhaustive"  # O(N²), all combinations
)
```

### ✅ 9. Scalable Solver for Large Datasets

Pattern-centric approach for N up to 100k rows.

**How it works**:
1. Generate global patterns per field (not per row)
2. Compute coverage for each pattern once
3. Greedy set cover with lazy multi-field construction
4. Only combine fields when needed to reduce FP

**Performance**:
- N=1k: ~0.1s
- N=10k: ~1s
- N=100k: ~10s (estimated)

```python
# Automatically uses scalable solver for large datasets
large_data = [...]  # 50k rows
solution = propose_solution_structured(large_data, large_excludes)
# Uses pattern-centric algorithm automatically
```

### ✅ 10. Multi-Field Lazy Construction

Intelligently combines fields only when necessary.

**Strategy**:
- Start with single-field patterns
- If max_fp=0 and pattern has FP, try adding second field
- Avoids O(F² × P²) explosion
- Only constructs combinations on-demand

**Example**:
```
Single-field: (instance: *cpu*) → 4 TP, 2 FP
Add second field: (module: *SRAM*) & (instance: *cpu*) → 4 TP, 0 FP
✓ Selected second one!
```

## Complete API Reference

### Function Signature
```python
def propose_solution_structured(
    include_rows,           # Data to match (list of dicts or DataFrame)
    exclude_rows=None,      # Data to exclude
    fields=None,            # Auto-detected from dict keys
    token_iter=None,        # Advanced: pre-generated tokens
    field_getter=None,      # Advanced: custom field extraction
    **kwargs                # All configuration parameters
) -> Solution
```

### Configuration Parameters

All parameters from `propose_solution()` are supported. See USER_GUIDE.md Configuration Reference for complete details.

**Key parameters for structured data:**

```python
solution = propose_solution_structured(
    include_rows, exclude_rows,

    # Quality & Mode
    mode="EXACT",              # or "APPROX" (case-insensitive)
    effort="medium",           # "low", "medium", "high", "exhaustive"

    # Tokenization (per-field supported)
    splitmethod="classchange",  # str or {"field": "method"}
    min_token_len=3,            # int or {"field": int}

    # Budget constraints
    max_candidates=4000,
    max_patterns=None,          # int or 0<float<1 for %
    max_fp=0,                   # int or 0<float<1 for %
    max_fn=None,                # int or 0<float<1 for %

    # Weights (all can be per-field)
    w_field={"pin": 2.0},       # Field preference (always dict)
    w_fp=1.0,                   # False positive cost (scalar or dict)
    w_fn=1.0,                   # False negative cost (scalar or dict)
    w_pattern=0.05,             # Pattern complexity cost
    w_op=0.02,                  # Operator cost
    w_wc=0.01,                  # Wildcard cost
    w_len=0.001,                # Length cost

    # Pattern generation
    per_word_substrings=16,
    max_multi_segments=3,
    allowed_patterns=None,      # ["prefix", "suffix", etc.]
    allow_complex_expressions=False,
)
```

## Usage Patterns

### Pattern 1: Simple Usage
```python
include = [{"module": "SRAM", "instance": "cpu/cache", "pin": "DIN"}]
exclude = [{"module": "SRAM", "instance": "cpu/cache", "pin": "CLK"}]

solution = propose_solution_structured(include, exclude)
```

### Pattern 2: Field Weights + Per-Field Tokenization
```python
solution = propose_solution_structured(
    include, exclude,
    w_field={"module": 2.0, "pin": 2.0, "instance": 0.3},
    splitmethod={"instance": "char", "module": "classchange"}
)
```

### Pattern 3: DataFrame with Wildcards
```python
import pandas as pd
import numpy as np

df_exclude = pd.DataFrame({
    'module': [np.nan, '*SRAM*'],  # NaN = don't care
    'instance': ['debug/*', np.nan],
    'pin': [np.nan, 'CLK']
})

solution = propose_solution_structured(df_include, df_exclude)
```

### Pattern 4: Large Dataset with Low Effort
```python
# 50k rows - use fast mode
solution = propose_solution_structured(
    large_data,
    large_excludes,
    effort="low"  # Single-field only, very fast
)
```

### Pattern 5: Critical Use Case with High Effort
```python
# Important signals - use best quality
solution = propose_solution_structured(
    critical_signals,
    all_other_signals,
    effort="high",
    w_field={"module": 3.0, "pin": 3.0}
)
```

## Algorithm Details

### Bounded Algorithm (N < 1k)
**When**: Small-medium datasets
**How**: Row-centric expression generation with caps
**Complexity**: O(N) with bounded candidates
**Config**:
- effort=medium: max 1000 total expressions, 50 per row
- effort=high: max 2000 total expressions, 100 per row

### Scalable Algorithm (N ≥ 1k)
**When**: Large datasets or high field count
**How**: Pattern-centric with lazy multi-field
**Complexity**: O(F × P × N) where F, P bounded
**Config**:
- effort=low: 20 patterns/field, single-field only
- effort=medium: 100 patterns/field, multi-field enabled
- effort=high: 200 patterns/field, multi-field enabled

### Exhaustive Algorithm (N < 100, F < 5)
**When**: Tiny datasets with effort="exhaustive"
**How**: Try all field combinations
**Complexity**: O(N²)
**Config**: No caps, explore all combinations

## Performance Characteristics

| Dataset Size | Fields | Effort | Time | Algorithm | Expressions |
|--------------|--------|--------|------|-----------|-------------|
| 10 rows | 3 | medium | < 0.01s | BOUNDED | 1-2 |
| 100 rows | 3 | medium | ~0.01s | BOUNDED | 2-5 |
| 1k rows | 5 | medium | ~0.1s | SCALABLE | 3-8 |
| 10k rows | 10 | medium | ~1s | SCALABLE | 5-15 |
| 100k rows | 20 | medium | ~10s | SCALABLE | 10-30 |
| 100k rows | 20 | low | ~3s | SCALABLE | 10-20 |

## Migration Guide

### From Old API (Pre-Unified)
```python
# Old (manual tokenizer setup)
from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields

tokenizer = make_split_tokenizer("classchange", min_token_len=3)
field_tokenizers = {"module": tokenizer, "instance": tokenizer, "pin": tokenizer}
token_iter = list(iter_structured_tokens_with_fields(...))
solution = propose_solution_structured(
    include, exclude,
    splitmethod="classchange",
    token_iter=token_iter
)
```

```python
# New (one line)
solution = propose_solution_structured(include, exclude)
```

### Enabling New Features
```python
# Add field weights
solution = propose_solution_structured(
    include, exclude,
    w_field={"pin": 2.0}  # Direct parameter!
)

# Add effort control
solution = propose_solution_structured(
    include, exclude,
    effort="high"  # Direct parameter!
)

# Add percentage budgets
solution = propose_solution_structured(
    include, exclude,
    max_fp=0.01,        # 1% FP allowed - direct!
    max_patterns=0.10   # 10% of rows max - direct!
)

# Use None wildcards in excludes
exclude = [{"module": None, "instance": "debug/*", "pin": None}]
solution = propose_solution_structured(include, exclude)

# Per-field weights for cost function
solution = propose_solution_structured(
    include, exclude,
    w_fp={"module": 2.0, "pin": 1.0},  # Per-field FP cost!
    w_pattern=0.05  # Global pattern cost
)
```

## Tips and Best Practices

### 1. Field Weights
- Use high weights (2.0-3.0) for fields with good discriminating patterns
- Use low weights (0.3-0.5) for fields with many similar values
- Default weight is 1.0

### 2. Effort Levels
- **low**: Quick prototyping, large datasets, don't care about optimality
- **medium**: Default, good balance
- **high**: Critical use cases, willing to wait for best solution
- **exhaustive**: Only for tiny datasets (< 100 rows)

### 3. None/NaN Wildcards
- Use in exclude_rows to exclude based on subset of fields
- Example: Exclude all debug instances regardless of module/pin
- Works seamlessly with pandas DataFrames (use np.nan)

### 4. Tokenization
- **classchange**: Good for CamelCase, SRAM_512x64 → [sram, 512, 64]
- **char**: Good for paths, chip/cpu/cache → [chip, cpu, cache]
- Use dict to mix methods: `{"instance": "char", "module": "classchange"}`

### 5. Scaling
- N < 1k: Don't worry, everything is fast
- 1k ≤ N < 10k: Use effort="medium" (default)
- N ≥ 10k: Consider effort="low" for speed
- N ≥ 100k: Use effort="low" and limit fields if possible

## Complete Example

```python
from patternforge.engine.solver import propose_solution_structured
import pandas as pd
import numpy as np

# DataFrame input with 1000 hardware signals
df_include = pd.DataFrame({
    'module': ['SRAM_512x64'] * 500 + ['SRAM_1024x32'] * 500,
    'instance': [f'chip/cpu/l1_cache/bank{i%4}' for i in range(1000)],
    'pin': ['DIN[0]'] * 250 + ['DIN[31]'] * 250 + ['DOUT[0]'] * 250 + ['DOUT[31]'] * 250,
})

# Excludes with None wildcards
df_exclude = pd.DataFrame({
    'module': [np.nan, np.nan, '*SRAM*'],
    'instance': ['debug/*', 'test/*', np.nan],
    'pin': [np.nan, np.nan, 'CLK'],
})

# Generate solution with all features - no classes needed!
solution = propose_solution_structured(
    df_include,
    df_exclude,
    effort="high",
    w_field={"module": 1.5, "pin": 2.0, "instance": 0.5},
    splitmethod={"instance": "char", "module": "classchange", "pin": "char"}
)

print(f"Expression: {solution.raw_expr}")
print(f"Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
print(f"FP: {solution.metrics['fp']}")
print(f"Expressions: {len(solution.expressions)}")
```

## Summary

The structured solver now features:
✅ Expression-based generation (multi-field patterns)
✅ Field weights (prefer certain fields) - now via `w_field` parameter
✅ Per-field tokenization (`splitmethod`, `min_token_len`)
✅ Per-field cost function weights (`w_fp`, `w_fn`, `w_pattern`, etc. can all be dicts)
✅ Percentage-based budgets (`max_fp=0.01` for 1% FP rate)
✅ None/NaN wildcards
✅ DataFrame support
✅ Adaptive algorithm selection
✅ Effort levels (low/medium/high/exhaustive)
✅ Scalable to 100k rows
✅ Multi-field lazy construction
✅ O(N) complexity for large datasets
✅ **Unified kwargs API** - no more nested classes!

**API Update**: The API has been simplified. All configuration now uses direct keyword arguments. No need to import or construct `SolveOptions`, `OptimizeWeights`, or `OptimizeBudgets` - just pass parameters directly!

