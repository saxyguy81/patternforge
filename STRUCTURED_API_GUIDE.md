# Structured Field Matching API Guide

## Current API

The structured field matching feature generates patterns per field (e.g., module, instance, pin) and combines them for precise multi-dimensional filtering.

### Basic Usage (Current API)

```python
from patternforge.engine.solver import propose_solution_structured
from patternforge.engine.models import SolveOptions
from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields

# 1. Define your data as list of dicts
include_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/core0/cache", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/core0/cache", "pin": "DOUT[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/core1/cache", "pin": "DIN[0]"},
]

exclude_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/core0/cache", "pin": "CLK"},
    {"module": "SRAM_512x64", "instance": "chip/debug/trace", "pin": "DIN[0]"},
]

# 2. Create tokenizers for each field
tokenizer = make_split_tokenizer("classchange", min_token_len=3)
field_tokenizers = {
    "module": tokenizer,
    "instance": tokenizer,
    "pin": tokenizer
}

# 3. Generate token iterator with field information
token_iter = list(iter_structured_tokens_with_fields(
    include_rows,
    field_tokenizers,
    field_order=["module", "instance", "pin"]
))

# 4. Call the structured solver
solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    SolveOptions(splitmethod="classchange"),
    token_iter=token_iter
)

# 5. Results include per-field patterns
print(solution['raw_expr'])  # e.g., "*cache*" on instance field
for atom in solution['atoms']:
    print(f"Field: {atom['field']}, Pattern: {atom['text']}")
```

### What Happens Internally

1. **Tokenization**: Each field is tokenized separately to extract keywords
   - module "SRAM_512x64" → tokens: ["SRAM", "512", "64"]
   - instance "chip/cpu/core0/cache" → tokens: ["chip", "cpu", "core", "cache"]
   - pin "DIN[0]" → tokens: ["DIN"]

2. **Candidate Generation**: Patterns are generated PER FIELD
   - module patterns: `SRAM*`, `*512*`, `*64*`
   - instance patterns: `chip/*`, `*cpu*`, `*cache*`, `*cpu*cache*`
   - pin patterns: `*DIN*`, `*OUT*`

3. **Greedy Selection**: Best combination selected across all fields
   - Each atom in solution carries a 'field' attribute
   - Atoms on different fields are combined with AND logic
   - Atoms on same field are combined with OR logic

4. **Result**: Multi-dimensional filter
   - Example: `instance=*cache* AND pin=*DIN*`

---

## Current Issues / Complexity

### Issue 1: Too Much Boilerplate

**Problem:**
```python
# User has to manually:
# 1. Create tokenizers
# 2. Generate token iterator
# 3. Know about field_order
# 4. Import from multiple modules

tokenizer = make_split_tokenizer("classchange", min_token_len=3)
field_tokenizers = {"module": tokenizer, "instance": tokenizer, "pin": tokenizer}
token_iter = list(iter_structured_tokens_with_fields(...))
```

This is too verbose for a common use case.

### Issue 2: Not Exported in Public API

**Problem:**
```python
# This works but is not in __all__
from patternforge.engine.solver import propose_solution_structured

# Public API only has:
from patternforge import propose_solution  # Single-string only
```

Users might not discover the structured feature.

### Issue 3: Field Getter Confusion

**Problem:**
```python
# Optional field_getter parameter but unclear when needed
def field_getter(row, field):
    return row.get(field, "")

solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    options,
    token_iter=token_iter,
    field_getter=field_getter  # When is this needed?
)
```

The API defaults to assuming dict rows, but the field_getter option adds confusion.

### Issue 4: No Simple "Just Works" Mode

**Problem:** Users with simple dictionaries have to understand tokenization even though defaults would work fine.

---

## Proposed Simplified API

### Option 1: Auto-Detect Mode (Easiest)

```python
from patternforge import propose_solution_structured

# Simple case - auto-detect fields from dict keys
include_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/core0/cache", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/core0/cache", "pin": "DOUT[0]"},
]

exclude_rows = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/core0/cache", "pin": "CLK"},
]

# Just call it! Field detection and tokenization automatic
solution = propose_solution_structured(include_rows, exclude_rows)

# Access per-field patterns
for atom in solution['atoms']:
    field = atom['field']  # 'module', 'instance', or 'pin'
    pattern = atom['text']  # '*cache*', '*DIN*', etc.
    print(f"{field}: {pattern}")
```

**Benefits:**
- Zero boilerplate for common case
- Automatic field detection from dict keys
- Default tokenizer (classchange) works for most cases
- Still returns same rich result format

### Option 2: Explicit Field List (Medium)

```python
from patternforge import propose_solution_structured

# Specify fields explicitly if order matters or subset needed
solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    fields=["module", "instance", "pin"],  # Optional, inferred if omitted
    splitmethod="classchange"  # Optional, default is "classchange"
)
```

**Benefits:**
- Control over which fields to use
- Control over field order
- Still minimal boilerplate

### Option 3: Advanced Control (Power Users)

```python
from patternforge import propose_solution_structured
from patternforge.engine.models import SolveOptions

# Full control for power users
solution = propose_solution_structured(
    include_rows,
    exclude_rows,
    fields=["module", "instance", "pin"],
    options=SolveOptions(
        splitmethod="classchange",
        min_token_len=3,
        mode=QualityMode.EXACT  # Zero false positives
    ),
    # Advanced: custom tokenizer per field
    field_tokenizers={
        "module": custom_module_tokenizer,
        "instance": custom_path_tokenizer,
        "pin": custom_pin_tokenizer
    }
)
```

**Benefits:**
- Full control when needed
- Custom tokenizers per field
- All SolveOptions available

---

## Implementation Plan

### Step 1: Simplify API with Smart Defaults

```python
def propose_solution_structured(
    include_rows: Sequence[dict | tuple],
    exclude_rows: Sequence[dict | tuple],
    fields: list[str] | None = None,  # Auto-detect from dict keys if None
    splitmethod: str = "classchange",  # Default tokenization
    options: SolveOptions | None = None,  # Use defaults if None
    field_tokenizers: dict | None = None,  # Advanced: custom per field
) -> dict[str, object]:
    """
    Generate patterns for structured data with multiple fields.

    Args:
        include_rows: Data to match (list of dicts or tuples)
        exclude_rows: Data to exclude (list of dicts or tuples)
        fields: Field names (auto-detected from dict keys if None)
        splitmethod: Tokenization method ('classchange' or 'char')
        options: Advanced options (uses smart defaults if None)
        field_tokenizers: Custom tokenizers per field (optional)

    Returns:
        Solution dict with per-field patterns in 'atoms'

    Example:
        >>> include = [
        ...     {"module": "SRAM", "instance": "cpu/cache", "pin": "DIN"},
        ...     {"module": "SRAM", "instance": "cpu/cache", "pin": "DOUT"},
        ... ]
        >>> exclude = [
        ...     {"module": "SRAM", "instance": "cpu/cache", "pin": "CLK"},
        ... ]
        >>> solution = propose_solution_structured(include, exclude)
        >>> # Returns patterns per field, e.g.:
        >>> # atoms[0]: field='pin', text='*DIN*'
        >>> # atoms[1]: field='pin', text='*DOUT*'
    """
    # Auto-detect fields from dict keys
    if fields is None:
        if include_rows and isinstance(include_rows[0], dict):
            fields = list(include_rows[0].keys())
        else:
            raise ValueError("fields must be specified for non-dict rows")

    # Create default tokenizers if not provided
    if field_tokenizers is None:
        tokenizer = make_split_tokenizer(splitmethod, min_token_len=3)
        field_tokenizers = {f: tokenizer for f in fields}

    # Create default options if not provided
    if options is None:
        options = SolveOptions(splitmethod=splitmethod)

    # Generate token iterator automatically
    token_iter = list(iter_structured_tokens_with_fields(
        include_rows,
        field_tokenizers,
        field_order=fields
    ))

    # Call internal implementation
    return _propose_solution_structured_impl(
        include_rows,
        exclude_rows,
        options,
        token_iter=token_iter
    )
```

### Step 2: Export in Public API

```python
# src/patternforge/__init__.py
from .engine.solver import propose_solution, propose_solution_structured

__all__ = [
    "propose_solution",
    "propose_solution_structured",  # NEW!
    "evaluate_expr",
    "main"
]
```

### Step 3: Add Helper for Common Hardware Use Case

```python
def propose_solution_for_pins(
    include_pins: list[tuple[str, str, str]],  # (module, instance, pin)
    exclude_pins: list[tuple[str, str, str]] = [],
    **kwargs
) -> dict[str, object]:
    """
    Convenience wrapper for hardware pin selection.

    Args:
        include_pins: List of (module, instance, pin) tuples to match
        exclude_pins: List of (module, instance, pin) tuples to exclude
        **kwargs: Additional options for propose_solution_structured

    Example:
        >>> include = [
        ...     ("SRAM_512x64", "chip/cpu/core0/cache", "DIN[0]"),
        ...     ("SRAM_512x64", "chip/cpu/core0/cache", "DOUT[0]"),
        ... ]
        >>> exclude = [
        ...     ("SRAM_512x64", "chip/cpu/core0/cache", "CLK"),
        ... ]
        >>> solution = propose_solution_for_pins(include, exclude)
    """
    include_rows = [
        {"module": m, "instance": i, "pin": p}
        for m, i, p in include_pins
    ]
    exclude_rows = [
        {"module": m, "instance": i, "pin": p}
        for m, i, p in exclude_pins
    ]
    return propose_solution_structured(
        include_rows,
        exclude_rows,
        fields=["module", "instance", "pin"],
        **kwargs
    )
```

---

## Migration Path

### Current Code (Complex)
```python
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
```

### New Code (Simple)
```python
from patternforge import propose_solution_structured

solution = propose_solution_structured(include_rows, exclude_rows)
```

**90% reduction in boilerplate!**

---

## Use Case Examples

### Use Case 1: SRAM Data Pins in Caches

```python
from patternforge import propose_solution_structured

include = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DIN[31]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "DOUT[0]"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank1", "pin": "DIN[0]"},
]

exclude = [
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "CLK"},
    {"module": "SRAM_512x64", "instance": "chip/cpu/l1_cache/bank0", "pin": "WEN"},
    {"module": "SRAM_512x64", "instance": "chip/debug/trace", "pin": "DIN[0]"},
]

solution = propose_solution_structured(include, exclude)

# Result might be:
# instance: *l1_cache* (rejects debug/trace)
# pin: *DIN* | *DOUT* (rejects CLK, WEN)
```

### Use Case 2: AXI VALID Signals on Masters

```python
include = [
    {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_port", "pin": "AWVALID"},
    {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_port", "pin": "ARVALID"},
    {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core1/axi_port", "pin": "AWVALID"},
]

exclude = [
    {"module": "AXI_MASTER", "instance": "soc/cpu_cluster/core0/axi_port", "pin": "AWREADY"},
    {"module": "AXI_SLAVE", "instance": "soc/mem_ctrl/axi_port", "pin": "AWVALID"},
    {"module": "AXI_MASTER", "instance": "soc/gpu_cluster/core0/axi_port", "pin": "AWVALID"},
]

solution = propose_solution_structured(include, exclude)

# Result might be:
# module: AXI_MASTER (rejects AXI_SLAVE)
# instance: *cpu_cluster* (rejects gpu_cluster)
# pin: *VALID (rejects *READY)
```

### Use Case 3: Clock Pins in Specific Pipeline Stage

```python
include = [
    {"module": "DFF", "instance": "cpu/core0/execute/alu/reg0", "pin": "CK"},
    {"module": "DFF", "instance": "cpu/core0/execute/alu/reg1", "pin": "CK"},
    {"module": "DFF", "instance": "cpu/core0/execute/fpu/reg0", "pin": "CK"},
]

exclude = [
    {"module": "DFF", "instance": "cpu/core0/execute/alu/reg0", "pin": "D"},
    {"module": "DFF", "instance": "cpu/core0/decode/reg0", "pin": "CK"},
]

solution = propose_solution_structured(include, exclude)

# Result might be:
# instance: *execute*alu* | *execute*fpu* (multi-segment patterns!)
# pin: CK (exact match)
```

---

## Recommendation

Implement **Option 1 (Auto-Detect Mode)** as the default with backward compatibility:

1. Add smart defaults to `propose_solution_structured`
2. Export it in public API (`__all__`)
3. Keep advanced options for power users
4. Document clearly with examples
5. Maintain backward compatibility with existing code

This makes structured matching as easy as:
```python
solution = propose_solution_structured(include_rows, exclude_rows)
```

Which is **much** easier than the current 10+ lines of boilerplate!
