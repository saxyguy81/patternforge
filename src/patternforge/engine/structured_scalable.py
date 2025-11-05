"""Scalable term-based structured solver for large datasets (N up to 100k, F up to 20).

Key insight: Don't enumerate all term combinations upfront. Use pattern frequency
and coverage-guided search to scale to O(N log N).
"""
from __future__ import annotations
from collections import defaultdict, Counter
from typing import Callable, Sequence

from . import bitset, matcher


class PatternStats:
    """Statistics for a single pattern on a single field."""

    def __init__(self, field: str, pattern: str):
        self.field = field
        self.pattern = pattern
        self.include_mask = 0
        self.exclude_mask = 0
        self.coverage = 0  # Number of include rows matched

    def compute_coverage(
        self,
        include_rows: Sequence[dict],
        exclude_rows: Sequence[dict],
        field_getter: Callable,
    ):
        """Compute which rows this pattern matches. O(N + M)."""
        for idx, row in enumerate(include_rows):
            value = field_getter(row, self.field)
            if matcher.match_pattern(value, self.pattern):
                self.include_mask |= (1 << idx)
                self.coverage += 1

        for idx, row in enumerate(exclude_rows):
            value = field_getter(row, self.field)
            if matcher.match_pattern(value, self.pattern):
                self.exclude_mask |= (1 << idx)


def generate_field_patterns_scalable(
    include_rows: Sequence[dict],
    field_names: list[str],
    field_getter: Callable,
    max_patterns_per_field: int = 100,
) -> dict[str, list[str]]:
    """
    Generate candidate patterns per field based on frequency.

    Complexity: O(N × F × P) where P = patterns per field value
    Returns: O(F × P_max) patterns total

    Args:
        include_rows: Rows to analyze
        field_names: List of field names
        field_getter: Function to get field value from row
        max_patterns_per_field: Max unique patterns per field

    Returns:
        Dict mapping field_name -> list of patterns
    """
    from .tokens import tokenize

    field_patterns = defaultdict(Counter)  # field -> pattern -> count

    # Generate patterns from include rows - O(N × F × P)
    for row in include_rows:
        for field_name in field_names:
            value = field_getter(row, field_name)
            if not value:
                continue

            # Tokenize once - O(len(value))
            tokens = tokenize(value, splitmethod="classchange", min_token_len=3)

            # Generate pattern candidates - O(P) where P is small constant
            patterns = set()

            # Exact
            patterns.add(value.lower())

            # Substrings from tokens
            for token in tokens[:5]:
                patterns.add(f"*{token.value}*")

            # Prefix/suffix
            if tokens:
                patterns.add(f"{tokens[0].value}/*")
                patterns.add(f"*/{tokens[-1].value}")

            # Multi-segment (limited)
            if len(tokens) >= 2:
                patterns.add(f"*{tokens[0].value}*{tokens[-1].value}*")

            # Count pattern frequency
            for pattern in patterns:
                field_patterns[field_name][pattern] += 1

    # Select top patterns by frequency - O(F × P log P)
    result = {}
    for field_name, pattern_counts in field_patterns.items():
        # Sort by frequency (descending)
        top_patterns = [
            pat for pat, _ in pattern_counts.most_common(max_patterns_per_field)
        ]
        result[field_name] = top_patterns

    return result


def greedy_set_cover_structured(
    include_rows: Sequence[dict],
    exclude_rows: Sequence[dict],
    field_names: list[str],
    field_patterns: dict[str, list[str]],  # field -> patterns
    field_getter: Callable,
    max_fp: int = 0,
    field_weights: dict[str, float] | None = None,
) -> list[dict]:
    """
    Greedy set cover algorithm for structured data.

    Complexity: O(F × P × N + K × F × P) where:
    - F = fields (~20)
    - P = patterns per field (~100)
    - N = rows (up to 100k)
    - K = selected terms (typically < 10)
    Total: O(F × P × N) = O(20 × 100 × 100k) = O(200M) operations
    But with early termination, typically much less.

    Strategy:
    1. Compute coverage for all single-field patterns - O(F × P × N)
    2. Greedily select best patterns, combining fields as needed - O(K × F × P)
    3. Construct multi-field terms lazily only when beneficial

    Returns:
        List of term dicts with 'fields' mapping field_name -> pattern
    """
    # Step 1: Compute pattern statistics - O(F × P × N)
    pattern_stats = {}  # (field, pattern) -> PatternStats
    for field_name in field_names:
        for pattern in field_patterns[field_name]:
            stats = PatternStats(field_name, pattern)
            stats.compute_coverage(include_rows, exclude_rows, field_getter)
            if stats.coverage > 0:  # Only keep patterns that match something
                pattern_stats[(field_name, pattern)] = stats

    # Step 2: Greedy selection - O(K × F × P) where K << N
    selected_terms = []
    covered_mask = 0
    fp_mask = 0
    num_include = len(include_rows)

    while bitset.count_bits(covered_mask) < num_include:
        best_term = None
        best_coverage = 0
        best_fp = float('inf')
        best_score = -1

        # Try single-field patterns first - O(F × P)
        for (field_name, pattern), stats in pattern_stats.items():
            new_coverage_mask = stats.include_mask & (~covered_mask)
            new_coverage = bitset.count_bits(new_coverage_mask)

            if new_coverage == 0:
                continue

            new_fp_mask = fp_mask | stats.exclude_mask
            new_fp = bitset.count_bits(new_fp_mask)

            if new_fp > max_fp:
                continue

            # Score: prefer more coverage, fewer FP, apply field weight
            weight = field_weights.get(field_name, 1.0) if field_weights else 1.0
            score = new_coverage * weight - new_fp * 10

            if score > best_score or (score == best_score and new_coverage > best_coverage):
                best_term = {field_name: pattern}
                best_coverage = new_coverage
                best_fp = new_fp
                best_score = score
                best_mask = stats.include_mask
                best_fp_mask = stats.exclude_mask

        # TODO: Try two-field combinations for better specificity
        # This would be O(F² × P²) but only if single-field patterns insufficient

        if best_term is None:
            break  # Can't cover more without violating constraints

        # Select this term
        selected_terms.append({
            "fields": best_term,
            "include_mask": best_mask,
            "exclude_mask": best_fp_mask,
            "coverage": best_coverage,
        })
        covered_mask |= best_mask
        fp_mask |= best_fp_mask

    return selected_terms
