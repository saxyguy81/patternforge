# PatternForge Examples

This directory contains comprehensive examples demonstrating all features of PatternForge.

## Quick Start

Run examples from this directory:

```bash
cd examples
python3 01_quick_start.py
```

Or from the project root:

```bash
PYTHONPATH=src python3 examples/01_quick_start.py
```

## Example Files

### 01_quick_start.py
**Best for: First-time users**

The simplest possible examples to get started:
- Basic single-field pattern matching
- Basic multi-field structured matching
- Quality modes (EXACT vs APPROX)

Run time: < 1 second

### 02_single_field_patterns.py
**Best for: Understanding pattern types**

Comprehensive guide to all pattern types for single-field matching:
- PREFIX patterns (token/*)
- SUFFIX patterns (*/token)
- SUBSTRING patterns (*token*)
- MULTI-SEGMENT patterns (*a*b*c*)
- Pattern ranking and selection
- Inverted patterns (NOT logic)
- Tokenization methods
- Real-world use cases

Run time: < 5 seconds

### 03_structured_patterns.py
**Best for: Multi-field data (hardware signals, databases, etc.)**

Seven detailed examples of structured multi-field pattern generation:
- SRAM data pins (module + pin patterns)
- Register file ports (instance path patterns)
- Pipeline stage clocks (multi-segment instance patterns)
- Memory write enables (module patterns across different sizes)
- AXI interface signals (multi-field combinations)
- Scan chain outputs (three-field patterns)
- Clock gating cells (anchored patterns on multiple fields)

Real-world use cases:
- Hardware signal selection
- Clock tree analysis
- Power analysis
- Scan chain generation
- Interface validation

Run time: < 10 seconds

### 04_performance_scaling.py
**Best for: Understanding scalability and benchmarking**

Comprehensive performance tests across various scenarios:
- Single-field scaling (10 to 10,000 rows)
- Structured multi-field scaling
- Quality mode comparison (EXACT vs APPROX)
- Effort level impact (low/medium/high)
- Field weight impact
- Worst-case stress tests

Generates performance tables showing:
- Time vs dataset size
- Algorithm selection impact
- Memory characteristics
- Scalability limits

Run time: 30-60 seconds (includes large dataset tests)

## Usage Patterns

### Single-Field Matching

For simple hierarchical paths or flat strings:

```python
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution

include = ["alpha/module1/mem/i0", "alpha/module2/io/i1"]
exclude = ["gamma/module1/mem/i0"]

solution = propose_solution(include, exclude, SolveOptions())
print(solution["expr"])  # P1
print(solution["raw_expr"])  # *alpha*
```

### Structured Multi-Field Matching

For data with multiple fields (module/instance/pin, etc.):

```python
from patternforge.engine.models import SolveOptions, OptimizeWeights
from patternforge.engine.solver import propose_solution_structured

include_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DIN[0]"},
]
exclude_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l2_cache/bank0", "pin": "DIN[0]"},
]

# With field preferences
solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    options=SolveOptions(
        weights=OptimizeWeights(
            w_field={"pin": 2.0, "instance": 0.5}  # Prefer pin patterns
        )
    )
)
print(solution["expr"])
```

## Learning Path

**Complete Beginner:**
1. Start with `01_quick_start.py` - run it and read the output
2. Read the comments to understand what each example does
3. Try modifying the include/exclude lists to see how patterns change

**Understanding Patterns:**
1. Run `02_single_field_patterns.py`
2. Study each example's input and output
3. Understand when each pattern type is used
4. Experiment with your own hierarchical paths

**Multi-Field Data:**
1. Run `03_structured_patterns.py`
2. See how patterns work across multiple fields
3. Learn about field weights and preferences
4. Apply to your own structured data (hardware signals, database rows, etc.)

**Performance Tuning:**
1. Run `04_performance_scaling.py`
2. Understand scaling characteristics
3. Learn which settings to use for different dataset sizes
4. Benchmark your own data

## Common Workflows

### Regression Triage

Find patterns in failing test paths:

```python
# See: 02_single_field_patterns.py, Example 7
include = ["regress/.../fail", ...]
exclude = ["regress/.../pass", ...]
solution = propose_solution(include, exclude, SolveOptions())
```

### Hardware Signal Selection

Select specific signals from netlists or databases:

```python
# See: 03_structured_patterns.py, Examples 1-7
include_rows = [{"module": ..., "instance": ..., "pin": ...}, ...]
solution = propose_solution_structured(include_rows, exclude_rows)
```

### Log File Filtering

Create filters for log entries:

```python
# See: 02_single_field_patterns.py, Examples 1-6
include = ["2024-01-15 ERROR ...", "2024-01-16 ERROR ...", ...]
exclude = ["2024-01-15 INFO ...", ...]
solution = propose_solution(include, exclude, SolveOptions())
```

## Advanced Topics

### Custom Tokenization

See the main README.md for examples of custom tokenizers and per-field tokenization.

### Inverted Patterns

Use `InvertStrategy.ALWAYS` to get "everything EXCEPT pattern":

```python
from patternforge.engine.models import InvertStrategy
solution = propose_solution(
    include, exclude,
    SolveOptions(invert=InvertStrategy.ALWAYS)
)
# Solution now represents: "everything EXCEPT <pattern>"
```

### Percentage Budgets

Allow a percentage of false positives instead of absolute counts:

```python
from patternforge.engine.models import OptimizeBudgets
solution = propose_solution(
    include, exclude,
    SolveOptions(
        budgets=OptimizeBudgets(
            max_fp=0.01,  # Allow 1% FP
            max_atoms=0.10  # Use at most 10% of rows as atoms
        )
    )
)
```

### Per-Field Cost Functions

Customize cost function per field:

```python
from patternforge.engine.models import OptimizeWeights
solution = propose_solution_structured(
    include_rows, exclude_rows,
    options=SolveOptions(
        weights=OptimizeWeights(
            w_fp={"module": 2.0, "pin": 1.0},  # Per-field FP cost
            w_fn=1.0,  # Global FN cost
        )
    )
)
```

## Troubleshooting

**Patterns are too broad:**
- Use EXACT mode instead of APPROX
- Add more exclude examples
- Increase field weights for specific fields (structured mode)
- Decrease max_fp budget

**Patterns are too specific (too many atoms):**
- Use APPROX mode
- Decrease max_atoms budget
- Adjust cost function weights (increase w_atom penalty)

**Too slow:**
- Use APPROX mode
- Use effort="low"
- Consider dataset size (> 10k rows may be slow in EXACT mode)

**Wrong fields selected (structured mode):**
- Adjust w_field weights to prefer/discourage specific fields
- Example: `w_field={"pin": 2.0, "instance": 0.3}`

## Next Steps

After working through the examples:
1. Read the **USER_GUIDE.md** for comprehensive documentation
2. Check the **README.md** for CLI usage
3. See the **STRUCTURED_SOLVER_GUIDE.md** for multi-field advanced features
4. Explore the test suite in `tests/` for more usage patterns

## Contributing Examples

If you have interesting use cases, please contribute examples via pull request!
