# patternforge

Fast, deterministic glob-pattern discovery & human-readable explanations for hierarchical names.

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user guide with examples and best practices
- **[STRUCTURED_SOLVER_GUIDE.md](STRUCTURED_SOLVER_GUIDE.md)** - Deep dive into multi-field pattern matching
- **[examples/](examples/)** - Runnable examples (quick start, patterns, performance tests)

## Quick Start

Python API in 30 seconds:

```python
from patternforge.engine.solver import propose_solution

include = [
    "alpha/module1/mem/i0",
    "alpha/module2/io/i1",
    "beta/cache/bank0",
]
exclude = [
    "gamma/module1/mem/i0",
    "beta/router/debug",
]

# Find patterns that match include but not exclude
solution = propose_solution(include, exclude)

print(f"Expression: {solution.expr}")        # P1 | P2
print(f"Raw patterns: {solution.raw_expr}")  # alpha/* | *bank*
print(f"Coverage: {solution.metrics['covered']}/{solution.metrics['total_positive']}")
print(f"False positives: {solution.metrics['fp']}")  # FP = items in exclude that match

for pattern in solution.patterns:
    print(f"  {pattern.id}: {pattern.text} (kind: {pattern.kind})")
```

Output:
```
Expression: P1 | P2
Raw patterns: alpha/* | *bank*
Coverage: 3/3
False positives: 0
  P1: alpha/* (kind: prefix)
  P2: *bank* (kind: substring)
```

**Terminology:**
- **FP (False Positive)**: Item in `exclude` that incorrectly matches the pattern (bad)
- **FN (False Negative)**: Item in `include` that doesn't match the pattern (bad)
- **TP (True Positive)**: Item in `include` that correctly matches (good)
- **Coverage**: Fraction of include items matched = `covered / total_positive`

Load from files:

```python
from patternforge import io

# Auto-detects format (.txt, .csv, .json, .jsonl)
include = io.read_items("include.txt")
exclude = io.read_items("exclude.txt")
solution = propose_solution(include, exclude)
```

Customize with direct parameters:

```python
# Pass parameters directly - no classes needed!
solution = propose_solution(include, exclude,
    mode="EXACT",        # Zero false positives (string, not enum!)
    max_patterns=5,      # At most 5 patterns
    w_fp=2.0,            # Penalize false positives heavily
)
```

## Python API

### Core Workflow

The library provides a simple API for pattern discovery:

```python
from patternforge.engine.solver import propose_solution
from patternforge.engine.explain import explain_text

# 1. Prepare data
include = ["alpha/module1/mem/i0", "alpha/module2/io/i1", "beta/cache/bank0"]
exclude = ["gamma/module1/mem/i0", "beta/router/debug"]

# 2. Find patterns (pass parameters directly as kwargs)
solution = propose_solution(include, exclude)

# 3. Access results
solution.expr          # Symbolic: "P1 | P2"
solution.raw_expr      # Raw: "alpha/* | *bank*"
solution.patterns      # list[Pattern]
solution.metrics       # {covered, total_positive, fp, fn, ...}
solution.witnesses     # {tp_examples, fp_examples, fn_examples}

# 4. Get human-readable explanation
print(explain_text(solution, include, exclude))
```

### File I/O

Auto-detect format and load from files:

```python
from patternforge import io

# Supports .txt, .csv, .json, .jsonl
include = io.read_items("paths.txt")
exclude = io.read_items("exclude.csv")

solution = propose_solution(include, exclude)

# Save solution
io.save_solution(solution, "solution.json")

# Load solution
loaded = io.load_solution("solution.json")
```

### Customization

Control solver behavior by passing parameters directly:

```python
from patternforge.engine.solver import propose_solution

# Quality modes (string values)
solution = propose_solution(include, exclude, mode="EXACT")  # Zero FP guaranteed
solution = propose_solution(include, exclude, mode="APPROX")  # Faster, may allow FP

# Control solution size and accuracy
solution = propose_solution(include, exclude,
    max_patterns=5,      # At most 5 patterns
    max_fp=0,            # Zero false positives (hard constraint)
    max_fn=0.1,          # Allow 10% false negatives (0.1 = 10%)
)

# Control weights (higher = penalize more)
solution = propose_solution(include, exclude,
    w_fp=2.0,            # Penalize false positives heavily
    w_fn=1.0,            # Penalize false negatives moderately
    w_pattern=0.1,       # Slight penalty for many patterns
)

# Combine multiple parameters
solution = propose_solution(include, exclude,
    mode="EXACT",
    effort="high",
    max_patterns=3,
    w_fp=2.0,
    allowed_patterns=["prefix", "suffix"]  # Only prefix/suffix, no substrings
)
```

**Available Parameters:**

**Quality & Mode:**
- `mode`: `"EXACT"` or `"APPROX"` (default: `"APPROX"`)
- `effort`: `"low"`, `"medium"` (default), `"high"`, or `"exhaustive"`
- `invert`: `"auto"` (default), `"never"`, or `"always"`

**Budget Constraints** (hard limits that stop search early):
- `max_candidates`: Max candidate patterns to consider (default: 4000)
- `max_patterns`: Max patterns in solution (int or 0<float<1 for %)
- `max_fp`: Max false positives allowed (int or 0<float<1 for %)
- `max_fn`: Max false negatives allowed (int or 0<float<1 for %)

**Weights** (soft penalties in cost function):
- `w_fp`: False positive penalty (default: 1.0)
- `w_fn`: False negative penalty (default: 1.0)
- `w_pattern`: Pattern count penalty (default: 0.05)
- `w_op`: Boolean operator penalty (default: 0.02)
- `w_wc`: Wildcard count penalty (default: 0.01)
- `w_len`: Pattern length penalty (default: 0.001)

**Pattern Generation:**
- `allowed_patterns`: List of pattern types, e.g., `["prefix", "suffix", "substring"]`
- `min_token_len`: Min token length to consider (default: 3)
- `splitmethod`: `"classchange"` (default) or `"char"`

See [USER_GUIDE.md](USER_GUIDE.md) for comprehensive parameter documentation.

### Multi-Field / Structured Data

For data with multiple fields (e.g., CSV with module/instance/pin columns):

```python
from patternforge.engine.solver import propose_solution_structured

# Data as list of dicts
include_rows = [
    {"module": "cache", "instance": "bank0", "pin": "data_in"},
    {"module": "cache", "instance": "bank1", "pin": "data_out"},
]
exclude_rows = [
    {"module": "router", "instance": "debug", "pin": "trace"},
]

# Find patterns across fields
solution = propose_solution_structured(include_rows, exclude_rows)

# Patterns carry field information
for pattern in solution.patterns:
    print(f"{pattern.field}: {pattern.text}")
```

CSV files are automatically parsed:
```python
from patternforge import io

# Auto-detects CSV and composes paths from module/instance/pin
include = io.read_items("connections.csv")
solution = propose_solution(include, exclude)
```

See [STRUCTURED_SOLVER_GUIDE.md](STRUCTURED_SOLVER_GUIDE.md) for comprehensive multi-field documentation.

## Use Cases

### Regression Triage

Identify patterns in failing test runs:

```python
from patternforge import io
from patternforge.engine.solver import propose_solution

# Load test results
failed = io.read_items("regress_failed.txt")
passed = io.read_items("regress_passed.txt")

# Find what's common in failures
solution = propose_solution(failed, passed)
print(f"Failure pattern: {solution.raw_expr}")
print(f"Covers {solution.metrics['covered']}/{solution.metrics['total_positive']} failures")
```

Example: If `regress_failed.txt` contains paths like:
```
regress/nightly/ipA/test_fifo/fail
regress/nightly/ipB/test_cache/fail
regress/nightly/ipC/test_uart/fail
```

The solver might find: `*fail*` or more specific patterns.

### Hardware Signal Selection

Select signals from hardware hierarchy:

```python
# Find all cache bank data pins, excluding debug
include = [
    "fabric_cache/cache0/bank0/data_in",
    "fabric_cache/cache0/bank1/data_out",
    "fabric_cache/cache1/bank0/data_in",
]
exclude = [
    "fabric_cache/cache_dbg/trace/data_tap",
    "fabric_router/rt0/debug/trace",
]

solution = propose_solution(include, exclude)
# Might find: *cache*bank*data* or similar
```

## Performance


The CLI remains responsive across common dataset sizes. Measuring synthetic workloads on this machine
shows near-linear scaling while keeping runtimes well under a second:

| include size | elapsed (s) | patterns | FP | FN |
|--------------|-------------|----------|----|----|
| 50           | 0.140       | 1     | 17 | 0  |
| 100          | 0.150       | 1     | 34 | 0  |
| 250          | 0.150       | 1     | 84 | 0  |
| 500          | 0.200       | 1     | 167 | 0 |
| 1000         | 0.200       | 1     | 334 | 0 |

These timings come from invoking `patternforge propose` with randomly generated hierarchical paths and recording
process CPU time (see `python - <<'PY' ...` in the repository history for the exact script).

## Pattern Syntax

PatternForge uses wildcard patterns with these rules:

- `*` matches any substring (including `/`)
- Pattern without leading `*` is anchored at start
- Pattern without trailing `*` is anchored at end
- Multiple `*` enforce order: `a*b*c` means "a ... b ... c" in sequence
- Boolean operators: `|` (OR), `&` (AND), `!` (NOT), `()` (grouping)

Examples:
```python
# Pattern types
"video*"           # Prefix: starts with "video"
"*cache*"          # Substring: contains "cache"
"*debug"           # Suffix: ends with "debug"
"*io/*/hdmi*"      # Multi-segment: io ... / ... hdmi

# Boolean expressions (used with evaluate_expr)
"P1 | P2"          # Matches P1 OR P2
"P1 & P2"          # Matches both P1 AND P2
"P1 & !P2"         # Matches P1 but NOT P2
"(P1 | P2) & !P3"  # Complex: (P1 or P2) and not P3
```

Pattern matching example:
```python
from patternforge.engine.solver import propose_solution

paths = [
    "video/display/pixel0",
    "video/shader/vector0",
    "compute/dsp/vector1",
]

solution = propose_solution(paths, [])
# Might find patterns like: "video*", "*vector*", etc.

for p in solution.patterns:
    print(f"{p.id}: {p.text} (kind: {p.kind})")
```

## CLI Usage

PatternForge includes a CLI for quick exploration:

```bash
# Propose patterns
python -m patternforge.cli propose \
  --include paths.txt --exclude debug.txt \
  --format json --out solution.json

# Explain solution
python -m patternforge.cli explain --solution solution.json --format text
```

See [examples/](examples/) for more CLI examples. For most use cases, the Python API (above) is recommended.

## Advanced Topics

For advanced usage, see:
- **[USER_GUIDE.md](USER_GUIDE.md)** - Custom tokenizers, detailed SolveOptions, optimization strategies
- **[STRUCTURED_SOLVER_GUIDE.md](STRUCTURED_SOLVER_GUIDE.md)** - Multi-field pattern matching, per-field weights
- **[examples/](examples/)** - Runnable examples and performance tests
