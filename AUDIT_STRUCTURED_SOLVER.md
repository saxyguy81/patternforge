"""
COMPREHENSIVE AUDIT: Structured Solver Pattern Quality Issues
==============================================================

Date: 2025
Issue: Structured solver generating suboptimal patterns (exact matches instead of generalizations)

## PROBLEM STATEMENT

The structured solver is generating 4 separate exact-match expressions instead of 1 generalized pattern:

**Input:**
- Include: 4 rows with pattern: module=SRAM, instance=pd_sio/asio/fabric/dart/*/u[0-1], pin=DIN
- Exclude: 3 rows to avoid

**Optimal Solution:**
- Single expression: `module=SRAM AND instance=*/fabric/dart/* AND pin=DIN`
- Patterns: 3 (one per field)
- Coverage: 4/4, FP: 0/3

**Actual Solution:**
- Four expressions, one per row:
  1. `module=SRAM AND instance=pd_sio/asio/fabric/dart/tag_ram/u0 AND pin=DIN`
  2. `module=SRAM AND instance=pd_sio/asio/fabric/dart/tag_ram/u1 AND pin=DIN`
  3. `module=SRAM AND instance=pd_sio/asio/fabric/dart/pa_ram/u0 AND pin=DIN`
  4. `module=SRAM AND instance=pd_sio/asio/fabric/dart/pa_ram/u1 AND pin=DIN`
- Patterns: 12 (3 per row × 4 rows)
- Coverage: 4/4, FP: 0/3

**Impact:** 4x pattern bloat, poor generalization, not meeting "best pattern match" criteria

## ROOT CAUSE ANALYSIS

### 1. Algorithm Routing Issue

File: `src/patternforge/engine/adaptive.py`
Lines: 71-81

```python
# Bounded algorithm for small-medium datasets
if N < 1000 and F < 8:
    if effort == EffortLevel.HIGH:
        return AlgorithmChoice.BOUNDED, {...}
    else:  # MEDIUM
        return AlgorithmChoice.BOUNDED, {...}
```

With N=4 and F=3, routes to **BOUNDED algorithm** (per-row expression generation).

### 2. BOUNDED Algorithm Design Flaw

File: `src/patternforge/engine/structured_expressions.py`
Lines: 167-211

The BOUNDED algorithm generates expressions **per include row**:

```python
for row_idx, row in enumerate(include_rows):
    row_expressions = []

    # Single-field expressions - O(F × P)
    for field_name in field_names:
        patterns = field_patterns.get((row_idx, field_name), [])
        for pattern in patterns[:5]:  # Limit patterns per field
            fields = {fn: "*" for fn in field_names}
            fields[field_name] = pattern
            expression = StructuredExpression(fields)
            row_expressions.append(expression)
```

**Problem:** Each row generates its own exact-match pattern, which scores highly and gets selected.

### 3. Scoring Function Bias

File: `src/patternforge/engine/structured_expressions.py`
Lines: 89-124

```python
# Bonus for anchored patterns (fewer wildcards)
wildcard_count = pattern.count("*")
if wildcard_count == 0:
    pattern_score *= 2.0  # Exact match <- PROBLEM!
elif wildcard_count == 1:
    pattern_score *= 1.5  # Prefix or suffix
```

Exact matches get 2x score multiplier, heavily biasing toward exact matches over generalizations.

Example:
- Exact: `pd_sio/asio/fabric/dart/tag_ram/u0` → score = 40 × 2.0 = 80
- General: `*fabric*dart*` → score = 12 × 1.0 = 12

Exact match wins by 6.7x!

### 4. Greedy Selection Per-Row Bias

File: `src/patternforge/engine/structured_expressions.py`
Lines: 269-309

```python
while bitset.count_bits(covered_mask) < num_include:
    # ...
    # Prefer expressions with more new coverage
    if (new_coverage_count > best_new_coverage or
        (new_coverage_count == best_new_coverage and expression.score > best_score)):
        best_term = expression
```

**Issue:** All 4 exact-match expressions have equal coverage (1 row each), so they're all selected.
No preference for patterns covering multiple rows.

## COMPARISON: SCALABLE vs BOUNDED Algorithms

### SCALABLE Algorithm (structured_scalable.py)
**Strengths:**
- Generates GLOBAL patterns across ALL rows (frequency-based)
- Prefers patterns that cover multiple rows
- Complexity: O(F × P × N) - linear in dataset size
- Better for generalization

**Weaknesses:**
- Might miss some nuanced per-row patterns
- Less exhaustive for tiny datasets

### BOUNDED Algorithm (structured_expressions.py)
**Strengths:**
- More exhaustive for small datasets
- Can find complex multi-field combinations

**Weaknesses:**
- Generates per-row expressions (exact match explosion)
- Biased toward exact matches
- Doesn't prefer patterns covering multiple rows
- Poor generalization for small-medium datasets

## PROPOSED SOLUTIONS

### Option 1: Force SCALABLE Algorithm for Small Datasets (RECOMMENDED)

**Change:** Modify adaptive.py routing to use SCALABLE for N < 1000 (not BOUNDED)

**Rationale:**
- SCALABLE has O(F × P × N) complexity, which is perfectly fine for N < 1000
- SCALABLE generates global patterns, leading to better generalization
- Avoids exact-match explosion

**Implementation:**
```python
# In adaptive.py, lines 71-81
if N < 1000 and F < 8:
    # Use SCALABLE instead of BOUNDED for better pattern quality
    if effort == EffortLevel.HIGH:
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 150,
            "enable_multi_field": True,
        }
    else:  # MEDIUM
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 100,
            "enable_multi_field": True,
        }
```

**Impact:**
- Fixes the memory instances test (4 rows → optimal pattern)
- Better generalization across all small-medium datasets
- No performance impact (SCALABLE is O(N) anyway)

### Option 2: Fix BOUNDED Algorithm Scoring

**Change:** Reduce exact-match bonus, prefer patterns covering multiple rows

**Implementation:**
```python
# In structured_expressions.py, line 103
if wildcard_count == 0:
    pattern_score *= 1.2  # Reduced from 2.0
elif wildcard_count == 1:
    pattern_score *= 1.1  # Reduced from 1.5

# In structured_expressions.py, line 294
# Prefer expressions with more coverage, then fewer wildcards
if (new_coverage_count > best_new_coverage or
    (new_coverage_count == best_new_coverage and
     bitset.count_bits(expression.include_mask) > best_total_coverage) or  # NEW
    (new_coverage_count == best_new_coverage and
     bitset.count_bits(expression.include_mask) == best_total_coverage and
     expression.score > best_score)):
```

**Rationale:**
- Reduces exact-match bias
- Prefers patterns that cover more total rows

**Impact:**
- Fixes BOUNDED algorithm for small datasets
- More complex implementation
- May still have issues with per-row generation

### Option 3: Hybrid Approach

**Change:** Use SCALABLE for pattern generation, BOUNDED for refinement

**Rationale:**
- Get best of both: global patterns + exhaustive combinations
- May be overkill for small datasets

## EARLY TERMINATION ANALYSIS

### Single-Field Solver (solver.py:209)

```python
# Early termination: if we've covered all includes with no FP, we're done
if bitset.count_bits(selection.include_bits) == len(ctx.include) and bitset.count_bits(selection.exclude_bits) == 0:
    break
```

**Analysis:** ✅ **This is CORRECT and OPTIMAL**

**Reasoning:**
1. Greedy algorithm considers ALL candidates in each iteration
2. If a single pattern could cover 100% with 0 FP, it would be selected in first iteration
3. Once we have 100% coverage with 0 FP, any additional patterns can only:
   - Add redundancy (increases pattern count) ← BAD
   - Do nothing (pointless)
4. Greedy doesn't support pattern removal/replacement
5. Therefore, early termination at 100% + 0 FP is optimal

**Potential Issue:** Could we achieve same coverage with MORE SPECIFIC patterns?

Answer: Yes, but that's a different optimization (pattern minimization/refinement).
The greedy algorithm already prefers more specific patterns via the cost function (w_len < 0 rewards longer patterns).

**Evidence from Tests:**
- All 136 tests pass (including exact_mode tests)
- User test case works: `pd_sio/asio/asio_spis/*` correctly generated
- No reported issues with premature termination

**Recommendation:** Keep early termination as-is. It's optimal for greedy set cover.

### Structured Solvers

**SCALABLE (structured_scalable.py:155):**
```python
while bitset.count_bits(covered_mask) < num_include:
```

Naturally stops when all covered, no early termination needed.

**BOUNDED (structured_expressions.py:269):**
```python
while bitset.count_bits(covered_mask) < num_include:
```

Same - naturally stops when all covered.

**Analysis:** ✅ **Both are CORRECT**

Loop condition ensures we keep going until full coverage OR no more valid patterns.
No need for additional early termination.

## RECOMMENDATIONS

### Immediate Actions (High Priority)

1. **Switch to SCALABLE algorithm for small datasets**
   - File: src/patternforge/engine/adaptive.py
   - Change routing for N < 1000 to use SCALABLE
   - Expected impact: Fixes pattern quality, maintains performance

2. **Update tests**
   - File: tests/test_structured_comprehensive.py
   - Adjust assertion: `self.assertLessEqual(solution.metrics['patterns'], 5)` should pass

### Medium Priority

3. **Add pattern quality metrics**
   - Add metric: "generalization_ratio" = patterns / include_rows
   - Target: < 1.0 (fewer patterns than rows)
   - Alert if > 0.75 (too specific)

4. **Add coverage efficiency metric**
   - Add metric: "coverage_per_pattern" = covered_rows / num_patterns
   - Target: > 1.5 (each pattern covers multiple rows on average)

### Low Priority

5. **Consider deprecating BOUNDED algorithm**
   - SCALABLE works well for all dataset sizes
   - BOUNDED adds complexity without clear benefits
   - Keep EXHAUSTIVE for effort=exhaustive cases

6. **Add pattern refinement phase** (future work)
   - After greedy selection, try to minimize pattern count
   - Replace multiple patterns with single more general pattern
   - Only run if pattern_count > threshold

## TEST RESULTS SUMMARY

From `tests/test_structured_comprehensive.py`:

✅ **Passing Tests (9/10):**
1. test_common_prefix_in_hierarchy - Correctly finds prefix in instance
2. test_field_specificity_preference - Prefers specific module pattern
3. test_identical_rows - Handles duplicates well
4. test_large_dataset_scalability - Scales to 50 rows
5. test_multi_field_expression_reduces_fp - Uses multi-field when needed
6. test_no_exclude_rows - Handles empty exclude set
7. test_single_field_difference_should_use_that_field - Correct field selection
8. test_early_termination_vs_exhaustive - Achieves full coverage
9. test_greedy_vs_optimal_pattern_count - Finds single module pattern

❌ **Failing Test (1/10):**
1. test_memory_instances_exact_mode - Generates 12 patterns instead of ≤5
   - Root cause: BOUNDED algorithm exact-match explosion
   - Fix: Use SCALABLE algorithm

**Overall Assessment:** 90% pass rate, single root cause identified

## CONCLUSION

The structured solver has ONE critical issue: algorithm routing causes pattern quality problems for small datasets.

**Root Cause:** BOUNDED algorithm generates per-row exact matches instead of global patterns.

**Fix:** Use SCALABLE algorithm for all dataset sizes (it's O(N) and works great).

**Early Termination:** No issues - current implementation is optimal.

**Next Steps:**
1. Implement adaptive.py routing change (5 lines)
2. Verify all tests pass
3. Consider long-term deprecation of BOUNDED algorithm
"""
