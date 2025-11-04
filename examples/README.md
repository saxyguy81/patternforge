# PatternForge Examples

This directory contains comprehensive examples demonstrating pattern generation capabilities.

## Overview

All examples use **EXACT mode** (default), which enforces **zero false positives** (max_fp=0).

## Example Files

### Basic Examples

**`showcase_examples.py`** - Best introduction to pattern types
- Example 1: Prefix + Suffix patterns working together
- Example 2: Multi-segment patterns with ordered keywords
- Example 3: Candidate analysis showing all pattern types
- Shows PREFIX, SUFFIX, MULTI-SEGMENT, and SUBSTRING patterns
- Includes candidate generation analysis

### Advanced Examples

**`advanced_examples.py`** - Mixed anchored and substring patterns
- Example 1: Mixed prefix + substring patterns
- Example 2: Multi-segment patterns (multiple keywords required)
- Example 3: Suffix patterns (anchored at end)
- Example 4: Complex chip hierarchy with mixed pattern types
- Real-world SoC scenarios with hierarchical paths

**`truly_advanced_examples.py`** - Complex pattern combinations
- Example 1: Multi-segment patterns avoiding false positives
- Example 2: Prefix + multi-segment combination
- Example 3: Real-world complex chip with 80% compression
- Shows power domains, NoC routers, and cache hierarchies

**`complex_pattern_examples.py`** - Sophisticated anchored + multi-segment
- 7 examples showing advanced pattern combinations
- SoC memory hierarchy: `*array*sram*` multi-segment pattern
- GPU shader units: prefix + multi-segment combo
- NoC routers: suffix patterns for port types
- Power domains: `*retention*ram*` | `*backup*` combination
- I/O peripherals: 3-way pattern split
- CPU execution units: precise multi-segment filtering

### Structured Data Examples

**`structured_examples.py`** - Multi-field pattern generation
- Demonstrates patterns across multiple fields (module/instance/pin)
- Example 1: SRAM data pins (module + pin filtering)
- Example 2: Register file read ports (instance path pattern)
- Example 3: Clock pins with multi-segment instance pattern
- Example 4: Memory modules with write enable (module + pin)
- Example 5: AXI interface valid signals (multi-field combo)
- Example 6: Scan chain outputs (three-field pattern)
- Example 7: Clock gating cells (anchored patterns on multiple fields)

## Pattern Types

### 1. PREFIX Patterns (`token/*`)
- **Wildcards:** 1
- **Anchored:** Start
- **Score Boost:** 1.5x
- **Best for:** Top-level hierarchy grouping
- **Example:** `project/*` matches all project paths

### 2. SUFFIX Patterns (`*/token`)
- **Wildcards:** 1
- **Anchored:** End
- **Score Boost:** 1.5x
- **Best for:** Common endpoints
- **Example:** `*/fifo` matches paths ending with fifo

### 3. MULTI-SEGMENT Patterns (`*tok1*tok2*`)
- **Wildcards:** Variable (2n+1 for n segments)
- **Anchored:** No
- **Best for:** Ordered keyword requirements
- **Example:** `*array*sram*` requires both keywords in order

### 4. SUBSTRING Patterns (`*token*`)
- **Wildcards:** 2
- **Anchored:** No
- **Best for:** Flexible matching
- **Example:** `*cache*` matches anywhere containing "cache"

### 5. EXACT Patterns
- **Wildcards:** 0
- **Anchored:** Both
- **Best for:** Exact match
- **Example:** `chip/cpu/core0/cache` matches only this path

## Running Examples

```bash
# Run any example
python3 examples/showcase_examples.py

# Or with explicit PYTHONPATH
PYTHONPATH=src python3 examples/advanced_examples.py
```

## Key Insights

### Multi-Segment Pattern Power
```python
# Problem: Select cache SRAMs, reject debug SRAMs
*array*sram*  # Requires both "array" AND "sram" in order
              # Avoids false positives from *sram* alone
```

### Anchored Pattern Efficiency
```python
project/*     # 1 wildcard (prefix)
*project*     # 2 wildcards (substring)
              # Prefix is more specific!
```

### Multi-Field Precision
```python
# Structured data: module + instance + pin
module=*SRAM* AND instance=*cache* AND pin=WEN
# Selects only write enable pins on SRAMs in caches
```

### Pattern Combinations
```python
*retention*ram* | *backup*
# Multi-segment for complex filtering
# Substring for simple matching
# Combined for complete coverage
```

## EXACT Mode Behavior

- **Default:** mode=QualityMode.EXACT
- **Constraint:** max_fp=0 (automatically enforced)
- **Guarantee:** Patterns NEVER match items in exclude list
- **Trade-off:** May achieve <100% coverage to avoid false positives
- **Use case:** When precision is more important than recall

## Real-World Applications

1. **Clock Tree Analysis:** All clock pins in specific domains
2. **Power Analysis:** Write enables on memories in active domains
3. **Scan Chain Generation:** Scan flops in specific modules
4. **Interface Validation:** Protocol signals on specific interfaces
5. **Timing Analysis:** Critical paths through specific units

## Further Reading

- See `tests/test_integration.py` for integration test examples
- Check `src/patternforge/engine/candidates.py` for pattern generation logic
- Review `src/patternforge/engine/solver.py` for greedy selection algorithm
