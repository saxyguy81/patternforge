"""Expression-based candidate generation for structured data."""
from __future__ import annotations
from collections.abc import Sequence
from itertools import combinations
from typing import Callable

from . import matcher
from . import bitset


class StructuredExpression:
    """An expression is a conjunction of field patterns."""

    def __init__(self, fields: dict[str, str]):
        """
        Args:
            fields: Mapping from field name to pattern (e.g., {"module": "*sram*", "pin": "*din*"})
        """
        self.fields = fields
        self.include_mask = 0
        self.exclude_mask = 0
        self.score = 0.0

    def matches_row(self, row: dict[str, str], field_getter: Callable) -> bool:
        """Check if this expression matches a row."""
        for field_name, pattern in self.fields.items():
            if pattern == "*":
                continue  # Wildcard field - always matches
            value = field_getter(row, field_name)
            if not matcher.match_pattern(value, pattern):
                return False
        return True

    def compute_masks(
        self,
        include_rows: Sequence[dict],
        exclude_rows: Sequence[dict],
        field_getter: Callable
    ):
        """Compute include/exclude masks for this expression."""
        for idx, row in enumerate(include_rows):
            if self.matches_row(row, field_getter):
                self.include_mask |= (1 << idx)

        for idx, row in enumerate(exclude_rows):
            if self.matches_row(row, field_getter):
                self.exclude_mask |= (1 << idx)

    def compute_score(self, field_weights: dict[str, float] | None = None):
        """
        Compute score for this expression.

        Scoring:
        - More fields specified (non-*) = higher score
        - Fewer wildcards in patterns = higher score
        - Field weights multiply score
        - More path components = higher score
        """
        score = 0.0
        num_fields = 0

        for field_name, pattern in self.fields.items():
            if pattern == "*":
                continue  # Wildcard field doesn't add specificity

            num_fields += 1

            # Base score from pattern length
            pattern_score = len(pattern)

            # Bonus for anchored patterns (fewer wildcards)
            wildcard_count = pattern.count("*")
            if wildcard_count == 0:
                pattern_score *= 2.0  # Exact match
            elif wildcard_count == 1:
                pattern_score *= 1.5  # Prefix or suffix

            # Bonus for more path components (hierarchical specificity)
            component_count = pattern.count("/") + 1
            if component_count > 1:
                pattern_score *= (1 + 0.2 * (component_count - 1))

            # Apply field weight
            if field_weights and field_name in field_weights:
                pattern_score *= field_weights[field_name]

            score += pattern_score

        # Bonus for multi-field expressions (encourages specificity)
        if num_fields > 1:
            score *= (1 + 0.3 * (num_fields - 1))

        self.score = score

    def __repr__(self):
        parts = [f"{k}={v}" for k, v in self.fields.items() if v != "*"]
        return f"Term({' & '.join(parts)})"


def generate_structured_expression_candidates(
    include_rows: Sequence[dict],
    exclude_rows: Sequence[dict],
    field_names: list[str],
    field_patterns: dict[tuple[int, str], list[str]],  # (row_idx, field_name) -> patterns
    field_getter: Callable,
    field_weights: dict[str, float] | None = None,
    max_expressions_per_row: int = 50,
    max_total_expressions: int = 1000,  # Cap total expressions for O(N) scaling
) -> list[StructuredExpression]:
    """
    Generate candidate expressions for structured data.

    Complexity: O(N × F × P + T × log T) where:
    - N = number of include rows
    - F = number of fields (typically constant, e.g., 3)
    - P = patterns per field (capped at 10)
    - T = total expressions generated (capped at max_total_expressions)

    Args:
        include_rows: Rows to match
        exclude_rows: Rows to avoid
        field_names: List of field names
        field_patterns: Mapping from (row_idx, field_name) to list of patterns for that field
        field_getter: Function to extract field value from row
        field_weights: Optional weights per field
        max_expressions_per_row: Max expressions to generate per row (default 50)
        max_total_expressions: Max total expressions to prevent quadratic blowup (default 1000)

    Returns:
        List of StructuredExpression candidates sorted by score (descending)
    """
    all_expressions = []
    expressions_per_row_limit = min(max_expressions_per_row, max_total_expressions // max(len(include_rows), 1))

    # For each include row, generate expressions
    # Complexity: O(N × F × P) where N=rows, F=fields, P=patterns/field
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

        # Two-field expressions - O(F² × P²) but F and P are small constants
        if len(field_names) >= 2:
            for field1, field2 in combinations(field_names, 2):
                patterns1 = field_patterns.get((row_idx, field1), [])[:3]
                patterns2 = field_patterns.get((row_idx, field2), [])[:3]
                for pat1 in patterns1:
                    for pat2 in patterns2:
                        fields = {fn: "*" for fn in field_names}
                        fields[field1] = pat1
                        fields[field2] = pat2
                        expression = StructuredExpression(fields)
                        row_expressions.append(expression)

        # Three-field expressions (if 3 fields) - O(P³) but P is small constant
        if len(field_names) == 3:
            patterns = {fn: field_patterns.get((row_idx, fn), [])[:2] for fn in field_names}
            for pat1 in patterns[field_names[0]]:
                for pat2 in patterns[field_names[1]]:
                    for pat3 in patterns[field_names[2]]:
                        fields = {
                            field_names[0]: pat1,
                            field_names[1]: pat2,
                            field_names[2]: pat3,
                        }
                        expression = StructuredExpression(fields)
                        row_expressions.append(expression)

        # Limit expressions per row to prevent explosion
        all_expressions.extend(row_expressions[:expressions_per_row_limit])

        # Early termination if we've generated enough expressions
        if len(all_expressions) >= max_total_expressions:
            break

    # Remove duplicates - O(T) where T is bounded
    unique_expressions = {}
    for expression in all_expressions:
        key = tuple(sorted(expression.fields.items()))
        if key not in unique_expressions:
            unique_expressions[key] = expression

    expressions = list(unique_expressions.values())

    # Compute masks and scores - O(T × (N + M)) where T is bounded
    # For large N, this is O(N) since T is capped
    for expression in expressions:
        expression.compute_masks(include_rows, exclude_rows, field_getter)
        expression.compute_score(field_weights)

    # Sort by score - O(T log T) where T is bounded, so O(1) in practice
    expressions.sort(key=lambda t: (-t.score, -bitset.count_bits(t.include_mask)))

    return expressions


def greedy_select_structured_expressions(
    expressions: list[StructuredExpression],
    num_include: int,
    num_exclude: int,
    max_fp: int = 0,
) -> list[StructuredExpression]:
    """
    Greedy select expressions to cover include rows while minimizing false positives.

    Complexity: O(T × K) where:
    - T = number of candidate expressions (capped at 1000)
    - K = number of selected expressions (typically << T)
    Overall: O(T) since K is bounded by coverage requirements

    Strategy:
    - Prefer expressions covering more uncovered rows (better coverage efficiency)
    - Use score as tiebreaker for expressions with same coverage
    - Stop when all rows covered or no more valid expressions

    Args:
        expressions: Candidate expressions sorted by score (T expressions, capped)
        num_include: Number of include rows
        num_exclude: Number of exclude rows
        max_fp: Maximum false positives allowed

    Returns:
        Selected expressions (typically K << T)
    """
    selected = []
    covered_mask = 0
    fp_mask = 0
    selected_set = set()  # O(1) lookup

    # Complexity: O(T × K) where K is number of iterations (selected expressions)
    # Since K is typically small (< 10), this is effectively O(T)
    while bitset.count_bits(covered_mask) < num_include:
        best_term = None
        best_new_coverage = 0
        best_score = -1

        # Single pass through expressions - O(T)
        for expression in expressions:
            # O(1) lookup in set
            if id(expression) in selected_set:
                continue

            # Calculate new coverage this expression would add - O(1) bitwise ops
            new_coverage = expression.include_mask & (~covered_mask)
            new_coverage_count = bitset.count_bits(new_coverage)

            if new_coverage_count == 0:
                continue  # Doesn't add any new coverage

            # Check if adding this expression would violate max_fp - O(1)
            new_fp_mask = fp_mask | expression.exclude_mask
            if bitset.count_bits(new_fp_mask) > max_fp:
                continue  # Would add too many false positives

            # Prefer expressions with more new coverage
            # Use score as tiebreaker
            if (new_coverage_count > best_new_coverage or
                (new_coverage_count == best_new_coverage and expression.score > best_score)):
                best_term = expression
                best_new_coverage = new_coverage_count
                best_score = expression.score

        if best_term is None:
            break  # No more valid expressions

        # Select this expression - O(1)
        selected.append(best_term)
        selected_set.add(id(best_term))
        covered_mask |= best_term.include_mask
        fp_mask |= best_term.exclude_mask

    return selected
