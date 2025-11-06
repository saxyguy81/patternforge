# EXACT Mode Bug Fix - Critical Finding and Resolution

## Executive Summary

**CONFIRMED**: The user's colleague's observation was correct. EXACT mode WAS producing false positives in violation of its zero-FP guarantee. This critical bug has been identified, fixed, and thoroughly tested.

## The Bug

### Symptoms
When using `mode="EXACT"`, which is supposed to guarantee zero false positives (`fp=0`), the solver was returning solutions with false positives in certain scenarios.

### Root Cause
The bug was in the inversion logic in `src/patternforge/engine/solver.py` at lines 787-803.

When the greedy selector couldn't find any patterns that satisfied the `max_fp=0` constraint (which is automatically set in EXACT mode), it would:
1. Return an empty pattern selection
2. The code would then automatically try an inverted solution
3. **BUG**: The inverted solution was returned WITHOUT checking if it violated the `max_fp=0` constraint

Specifically, lines 787-789:
```python
if options.invert == InvertStrategy.ALWAYS or not base_solution.patterns:
    inverted_solution = _make_solution(include, exclude, selection, options, inverted=True)
    return inverted_solution  # <-- BUG: No FP check!
```

When no patterns could be found, the inverted solution would be `"FALSE"` with `global_inverted=True`, which effectively creates a "match everything" pattern. This would match all exclude items, causing false positives.

### Example Failure Case
```python
include = ["module/instance[0]/mem/i0", "module/instance[1]/mem/i0", "module/instance[2]/mem/i0"]
exclude = ["module/instance[3]/mem/i0", "module/instance[4]/mem/i0", "debug/instance[0]/mem/i0"]
solution = propose_solution(include, exclude, mode="EXACT")

# BEFORE FIX:
# solution.metrics['fp'] = 3  # WRONG! Violates EXACT mode guarantee
# solution.global_inverted = True
# solution.expr = "FALSE"  # With inversion = match everything

# AFTER FIX:
# solution.metrics['fp'] = 0  # CORRECT!
# solution.global_inverted = False
# solution.metrics['covered'] = 0  # No coverage, but maintains FP=0 guarantee
```

## The Fix

Added FP validation before returning inverted solutions at two locations in `solver.py`:

### Location 1: Lines 789-793
```python
if options.invert == InvertStrategy.ALWAYS or not base_solution.patterns:
    inverted_solution = _make_solution(include, exclude, selection, options, inverted=True)
    # NEW: In EXACT mode (or when max_fp is set), verify inverted solution doesn't violate FP constraint
    if options.budgets.max_fp is not None and inverted_solution.metrics['fp'] > options.budgets.max_fp:
        # Inverted solution violates FP constraint - return base solution instead
        return base_solution
    return inverted_solution
```

### Location 2: Lines 806-810
```python
if options.invert == InvertStrategy.ALWAYS or inverted_cost < base_cost:
    # NEW: In EXACT mode (or when max_fp is set), verify inverted solution doesn't violate FP constraint
    if options.budgets.max_fp is not None and inverted_solution.metrics['fp'] > options.budgets.max_fp:
        # Inverted solution violates FP constraint - return base solution instead
        return base_solution
    return inverted_solution
```

## Testing

### New Test Suite
Created `tests/test_exact_mode.py` with 22 comprehensive tests covering:
- Simple and complex hierarchical paths
- Array indices and special characters
- Unicode paths
- Empty exclude lists
- Structured data with wildcards
- Various split methods (char vs classchange)
- Inversion strategies
- Budget constraints
- Large-scale stress testing (100 instances)
- Real production hardware paths

**Result**: All 22 tests pass, confirming `metrics['fp'] == 0` in every EXACT mode scenario.

### Test Failures Found Before Fix
The new test suite exposed 5 failures where EXACT mode produced false positives:
1. `test_exact_mode_with_array_indices` - 3 FP
2. `test_exact_mode_very_similar_paths` - 2 FP
3. `test_exact_mode_with_special_characters` - 2 FP
4. `test_exact_mode_char_vs_classchange_splitmethod` - 2 FP
5. `test_exact_mode_realistic_production_case` - 3 FP

All now pass after the fix.

### Regression Testing
Fixed 4 existing tests that relied on the old (buggy) behavior:
- `test_propose_solution_inversion` - Updated to use `mode="APPROX"`
- `test_terms_flag_inverted_subtractive` - Updated to use `mode="APPROX"`
- `test_longest` - Updated to use `mode="APPROX"`
- `test_real_world_28_instances` - Updated to use `mode="APPROX"`

These tests were testing inversion or coverage behavior, not the FP guarantee, so they should use APPROX mode which allows FP for better compression.

**Full test suite**: All 132 tests pass.

## Behavior Changes

### EXACT Mode (mode="EXACT")
**Before Fix**: Could return solutions with false positives when inverted patterns were used.

**After Fix**: ALWAYS guarantees `metrics['fp'] == 0`. May return solutions with:
- Zero patterns (`patterns=[]`)
- Zero coverage (`covered=0`)
- High false negatives (`fn=N`)

This is CORRECT behavior: In EXACT mode, if no patterns can cover items without FP, the solver returns an empty solution rather than violating the FP constraint.

### APPROX Mode (mode="APPROX")
No changes. APPROX mode continues to optimize for coverage and compression, potentially allowing some false positives.

## Recommendations

1. **Use APPROX mode for compression**: When the goal is pattern compression and some false positives are acceptable, use `mode="APPROX"`.

2. **Use EXACT mode for strict validation**: When zero false positives is critical (e.g., security, compliance), use `mode="EXACT"`.

3. **Check coverage metrics**: In EXACT mode, always check `solution.metrics['covered']` to see if the solver found any patterns. If coverage is 0 or low, consider:
   - Adjusting the exclude list to be less restrictive
   - Using APPROX mode with a small `max_fp` budget
   - Breaking the problem into smaller subproblems

## Files Modified

1. `src/patternforge/engine/solver.py` - Added FP validation for inverted solutions
2. `tests/test_exact_mode.py` - NEW: 22 comprehensive EXACT mode tests
3. `tests/test_solver.py` - Updated `test_propose_solution_inversion` to use APPROX mode
4. `tests/test_terms.py` - Updated `test_terms_flag_inverted_subtractive` to use APPROX mode
5. `tests/test_integration.py` - Updated 2 tests to use APPROX mode
6. `debug_exact_mode.py` - NEW: Diagnostic script used to investigate the bug

## Verification

To verify the fix works correctly:
```bash
# Run EXACT mode test suite
pytest tests/test_exact_mode.py -v

# Run full test suite
pytest tests/ -v

# Run diagnostic script
python3 debug_exact_mode.py
```

All should pass with zero false positives in EXACT mode.

## Conclusion

The bug was real and critical. EXACT mode was not enforcing its zero false positive guarantee. The fix ensures that inverted solutions are only returned if they respect the `max_fp` constraint. This restores the correctness of EXACT mode while maintaining backward compatibility for APPROX mode.
