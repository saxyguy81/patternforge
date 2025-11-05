# Improved Structured API Design

## Your Suggestions (Excellent Ideas!)

### 1. Remove token_iter (Implementation Detail)
✅ **Agreed** - Users shouldn't see this internal detail

### 2. splitmethod as string or dict
✅ **Great idea** - Simple default with per-field override:
```python
# Simple: all fields use same method
splitmethod="classchange"

# Advanced: per-field control
splitmethod={"instance": "char", "module": "classchange", "pin": "char"}
```

### 3. Field weights
✅ **Brilliant** - Prefer certain fields:
```python
field_weights={"module": 2.0, "pin": 2.0, "instance": 0.5}
# Prefer patterns on module/pin over instance
```

### 4. None/NaN for "don't care" fields
✅ **Very practical**:
```python
exclude_rows = [
    {"module": None, "instance": "chip/debug/*", "pin": None},
    # Exclude this instance regardless of module/pin
]
```

### 5. Support DataFrames and other types
✅ **Essential for real use**

### 6. Pattern merging (hierarchical patterns)
🤔 **Interesting** - needs design discussion

### 7. Encourage multi-field patterns
✅ **Smart** - use weights to prefer richer solutions

### 8. Unify APIs
🤔 **Worth discussing** - pros/cons analysis

---

## Proposed New API

```python
def propose_solution_structured(
    include_rows: Sequence[dict] | pd.DataFrame | Sequence[tuple],
    exclude_rows: Sequence[dict] | pd.DataFrame | Sequence[tuple] | None = None,

    # Field configuration
    fields: list[str] | None = None,  # Auto-detect from dict keys or DataFrame columns
    field_weights: dict[str, float] | None = None,  # Prefer certain fields

    # Tokenization
    splitmethod: str | dict[str, str] = "classchange",  # Unified or per-field
    min_token_len: int = 3,

    # Solve options
    options: SolveOptions | None = None,  # Advanced control
    mode: str = "EXACT",  # "EXACT" or "APPROX"

) -> dict[str, object]:
    """
    Generate patterns for structured data with multiple fields.

    Args:
        include_rows: Data to match
            - List of dicts: [{"module": "SRAM", "instance": "cpu/cache", "pin": "DIN"}]
            - DataFrame: pd.DataFrame with columns [module, instance, pin]
            - List of tuples: [("SRAM", "cpu/cache", "DIN")] with fields parameter

        exclude_rows: Data to exclude (same format as include_rows)
            - Use None in dict fields as wildcard (don't care)
            - Example: {"module": None, "instance": "debug/*", "pin": None}

        fields: Field names (auto-detected from dict keys or DataFrame columns)

        field_weights: Prefer patterns on certain fields
            - Higher weight = prefer patterns on this field
            - Lower weight = discourage patterns on this field
            - Example: {"module": 2.0, "pin": 2.0, "instance": 0.5}
            - A single wildcard (*) on instance doesn't count as a pattern

        splitmethod: Tokenization method
            - String: Same method for all fields ("classchange" or "char")
            - Dict: Per-field methods {"instance": "char", "module": "classchange"}
            - Unspecified fields use "classchange" default

        min_token_len: Minimum token length (default 3)

        options: Advanced SolveOptions (overrides other parameters)

        mode: "EXACT" (zero false positives) or "APPROX" (allow some FP)

    Returns:
        Solution dict with per-field patterns:
        {
            'atoms': [
                {'field': 'module', 'text': 'SRAM*', 'kind': 'prefix', ...},
                {'field': 'pin', 'text': '*DIN*', 'kind': 'substring', ...}
            ],
            'raw_expr': 'module:SRAM* & pin:*DIN*',
            'metrics': {...}
        }

    Examples:
        >>> # Example 1: Simple dict list with auto-detection
        >>> include = [
        ...     {"module": "SRAM_512x64", "instance": "cpu/l1_cache", "pin": "DIN"},
        ...     {"module": "SRAM_512x64", "instance": "cpu/l1_cache", "pin": "DOUT"},
        ... ]
        >>> exclude = [
        ...     {"module": "SRAM_512x64", "instance": "cpu/l1_cache", "pin": "CLK"},
        ... ]
        >>> solution = propose_solution_structured(include, exclude)

        >>> # Example 2: With field weights
        >>> solution = propose_solution_structured(
        ...     include, exclude,
        ...     field_weights={"module": 2.0, "pin": 2.0, "instance": 0.5}
        ... )

        >>> # Example 3: Exclude instances regardless of module/pin (wildcards)
        >>> exclude = [
        ...     {"module": None, "instance": "chip/debug/*", "pin": None},
        ...     {"module": None, "instance": "chip/test/*", "pin": None},
        ... ]
        >>> solution = propose_solution_structured(include, exclude)

        >>> # Example 4: DataFrame input
        >>> import pandas as pd
        >>> df_include = pd.DataFrame({
        ...     'module': ['SRAM_512x64', 'SRAM_512x64'],
        ...     'instance': ['cpu/cache', 'cpu/cache'],
        ...     'pin': ['DIN', 'DOUT']
        ... })
        >>> solution = propose_solution_structured(df_include, df_exclude)

        >>> # Example 5: Per-field split methods
        >>> solution = propose_solution_structured(
        ...     include, exclude,
        ...     splitmethod={"instance": "char", "module": "classchange", "pin": "char"}
        ... )
    """
```

---

## Design Details

### 1. Field Weights Implementation

Field weights affect pattern scoring and selection:

```python
# Internal scoring
def score_pattern(pattern, field, field_weights):
    base_score = len(pattern.token) * type_multiplier(pattern.kind)
    field_weight = field_weights.get(field, 1.0)
    return base_score * field_weight

# Effect on greedy selection
# - Patterns on high-weight fields scored higher
# - Solver prefers patterns on module/pin over instance
# - Single wildcard on low-weight field doesn't count as a pattern
```

**Use Cases:**
- Prefer `module=SRAM*` over `instance=*cache*` if both work
- Discourage broad instance patterns like `*cpu*`
- Encourage specific pin patterns like `*VALID`

### 2. None/NaN Handling in Exclude Rows

When exclude_row has None for a field, it means "don't care":

```python
exclude = [
    {"module": None, "instance": "chip/debug/*", "pin": None},
    # Matches ANY module + "chip/debug/*" instance + ANY pin
]

# Implementation
def matches_exclude(candidate_row, exclude_row):
    for field in fields:
        if exclude_row[field] is None or pd.isna(exclude_row[field]):
            continue  # Wildcard - always matches
        if not pattern_matches(candidate_row[field], exclude_row[field]):
            return False
    return True
```

**Use Cases:**
- Exclude all pins on certain instances: `{module: None, instance: "debug/*", pin: None}`
- Exclude certain modules anywhere: `{module: "DEBUG*", instance: None, pin: None}`
- Exclude certain pins anywhere: `{module: None, instance: None, pin: "CLK"}`

### 3. splitmethod as String or Dict

```python
# Parse splitmethod
if isinstance(splitmethod, str):
    # All fields use same method
    field_splitmethods = {f: splitmethod for f in fields}
else:
    # Per-field methods with default fallback
    field_splitmethods = {}
    default = splitmethod.get("__default__", "classchange")
    for f in fields:
        field_splitmethods[f] = splitmethod.get(f, default)

# Create tokenizers per field
field_tokenizers = {
    f: make_split_tokenizer(method, min_token_len)
    for f, method in field_splitmethods.items()
}
```

**Use Cases:**
- Instance paths: `"char"` splits on `/` → better hierarchy patterns
- Module names: `"classchange"` splits on transitions → `SRAM_512x64` → `["SRAM", "512", "64"]`
- Pin names: `"char"` splits on `[`, `]` → `DIN[0]` → `["DIN", "0"]`

### 4. DataFrame Support

```python
def normalize_input(rows, fields):
    """Convert various input types to list of dicts."""
    if rows is None:
        return []

    # Already list of dicts
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return rows

    # DataFrame
    if hasattr(rows, 'to_dict'):  # pandas/polars DataFrame
        return rows.to_dict('records')

    # List of tuples with field names
    if isinstance(rows, list) and rows and isinstance(rows[0], tuple):
        if fields is None:
            raise ValueError("fields parameter required for tuple input")
        return [dict(zip(fields, row)) for row in rows]

    # CSV file path
    if isinstance(rows, str) and rows.endswith('.csv'):
        import pandas as pd
        df = pd.read_csv(rows)
        return df.to_dict('records')

    raise ValueError(f"Unsupported input type: {type(rows)}")
```

**Supported Types:**
- ✅ List of dicts: `[{"module": "SRAM", ...}]`
- ✅ pandas DataFrame: `pd.DataFrame(...)`
- ✅ polars DataFrame: `pl.DataFrame(...)`
- ✅ List of tuples: `[("SRAM", "cpu/cache", "DIN")]` with `fields=["module", "instance", "pin"]`
- ✅ CSV path: `"pins.csv"` (reads as DataFrame)

### 5. Pattern Merging (Hierarchical Patterns)

**Question:** Can we merge patterns hierarchically?

Example:
```
Input instances:
  chip/cpu/core0/cache
  chip/cpu/core1/cache
  chip/gpu/shader0/cache

Current output:
  *cache*  (substring)

Desired output:
  chip/*/cache  (hierarchical pattern with wildcard in middle)
```

**Challenge:** Current wildcards are substring-based, not hierarchy-aware.

**Possible Enhancement:**
```python
# New pattern type: HIERARCHICAL
# Format: "prefix/*/suffix" or "prefix/*/middle/*/suffix"
# Example: "chip/*/cache" matches "chip/cpu/core0/cache"

# Would require:
# 1. Path-aware tokenization
# 2. Common prefix/suffix detection
# 3. New pattern kind: 'hierarchical'
# 4. Updated matcher to handle path wildcards
```

**Recommendation:** Good future feature, but complex. Start with current pattern types and add this later if needed.

### 6. Encourage Multi-Field Patterns

**Goal:** Prefer solutions that use multiple fields for more specific filtering.

**Approach 1: Penalty for Single-Field Solutions**
```python
# In cost function
single_field_penalty = 0.1
if all_patterns_on_same_field(solution):
    cost += single_field_penalty
```

**Approach 2: Bonus for Multi-Field Coverage**
```python
# Reward solutions that use more fields
fields_used = set(atom['field'] for atom in solution.atoms)
multi_field_bonus = -0.05 * len(fields_used)  # Negative = lower cost
cost += multi_field_bonus
```

**Approach 3: Use Field Weights**
```python
# Set low weight on broad fields
field_weights = {"instance": 0.1}  # Very low weight
# Solver will prefer adding patterns on other fields
```

**Recommendation:** Use Approach 3 (field weights) - most flexible and doesn't require new parameters.

### 7. Should We Unify the APIs?

**Option A: Unified API (Auto-Detect)**
```python
def propose_solution(
    include,  # Could be list of strings OR list of dicts
    exclude=None,
    fields=None,  # If None and input is dicts, use structured solver
    **kwargs
):
    if _is_structured(include):
        return propose_solution_structured(include, exclude, fields, **kwargs)
    else:
        return propose_solution_single(include, exclude, **kwargs)
```

**Pros:**
- ✅ Single function to learn
- ✅ Cleaner imports

**Cons:**
- ❌ Ambiguous return type (single expr vs multi-field)
- ❌ Different options for each mode (field_weights only for structured)
- ❌ Harder to document
- ❌ Type checking becomes complex

**Option B: Separate APIs (Current)**
```python
propose_solution(include_strings, exclude_strings, ...)
propose_solution_structured(include_rows, exclude_rows, ...)
```

**Pros:**
- ✅ Clear intent
- ✅ Different return types
- ✅ Specific options for each mode
- ✅ Better type checking

**Cons:**
- ❌ Two functions to learn

**Recommendation: Keep Separate APIs**
- Clearer documentation
- Better type safety
- Explicit intent in code
- Less confusing for users

---

## Proposed Implementation Plan

### Phase 1: Simplify Current API ✅
```python
def propose_solution_structured(
    include_rows,
    exclude_rows=None,
    fields=None,  # Auto-detect
    splitmethod="classchange",  # String or dict
    options=None  # Optional SolveOptions
):
    # Remove token_iter from signature
    # Generate internally
    # Support DataFrame input
```

### Phase 2: Add Field Weights ✅
```python
def propose_solution_structured(
    ...,
    field_weights=None  # Dict of field -> weight
):
    # Modify scoring to use field weights
    # Lower weight = discourage patterns on that field
```

### Phase 3: Add None/NaN Support ✅
```python
# In matching logic
def matches_exclude(row, exclude_row):
    for field in fields:
        if exclude_row[field] is None or pd.isna(exclude_row[field]):
            continue  # Wildcard
        if not matches(row[field], exclude_row[field]):
            return False
    return True
```

### Phase 4: Enhanced Output Format ✅
```python
{
    'atoms': [
        {'field': 'module', 'text': 'SRAM*', 'weight': 2.0, ...},
        {'field': 'pin', 'text': '*DIN*', 'weight': 2.0, ...}
    ],
    'raw_expr': 'module:SRAM* & pin:*DIN*',  # Show field prefixes
    'field_coverage': {'module': 1, 'instance': 0, 'pin': 1},  # Fields used
    'metrics': {...}
}
```

### Phase 5: Hierarchical Patterns (Future) 🔮
- Path-aware tokenization
- Common prefix/suffix detection
- New pattern kind: 'hierarchical'
- Format: `"chip/*/cache"`

---

## Example Usage (Improved API)

```python
from patternforge import propose_solution_structured
import pandas as pd

# Example 1: Simple usage
include = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DOUT[0]"},
]
exclude = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "CLK"},
]
solution = propose_solution_structured(include, exclude)

# Example 2: Prefer module/pin patterns over instance
solution = propose_solution_structured(
    include, exclude,
    field_weights={"module": 2.0, "pin": 2.0, "instance": 0.5}
)

# Example 3: Exclude all pins on debug instances (wildcards)
exclude = [
    {"module": None, "instance": "chip/debug/*", "pin": None},
    {"module": None, "instance": "chip/test/*", "pin": None},
]
solution = propose_solution_structured(include, exclude)

# Example 4: DataFrame input
df = pd.DataFrame({
    'module': ['SRAM_512x64', 'SRAM_512x64'],
    'instance': ['chip/cpu/cache', 'chip/cpu/cache'],
    'pin': ['DIN[0]', 'DOUT[0]']
})
solution = propose_solution_structured(df, exclude_df)

# Example 5: Per-field tokenization
solution = propose_solution_structured(
    include, exclude,
    splitmethod={
        "instance": "char",      # Split on / for paths
        "module": "classchange", # Split on case changes
        "pin": "char"           # Split on [ and ]
    }
)

# Example 6: Encourage patterns on all fields
solution = propose_solution_structured(
    include, exclude,
    field_weights={"module": 1.5, "instance": 1.5, "pin": 1.5},
    # All fields equally preferred - encourages multi-field solutions
)
```

---

## Summary of Improvements

| Feature | Current | Proposed | Benefit |
|---------|---------|----------|---------|
| **token_iter** | Required | Removed | Cleaner API |
| **splitmethod** | String only | String or dict | Per-field control |
| **field_weights** | N/A | Dict[str, float] | Prefer certain fields |
| **None/NaN** | Not supported | Wildcard | Partial exclusions |
| **DataFrame** | Not supported | Supported | Real-world data |
| **Tuple lists** | Not supported | Supported | Simple data |
| **API complexity** | 10+ lines | 1 line | 90% reduction |
| **Unified API** | Separate | Keep separate | Clearer intent |

Would you like me to implement these improvements?
