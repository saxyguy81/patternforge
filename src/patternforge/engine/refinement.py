"""
Pattern Refinement Module
=========================

Post-processing phase that attempts to simplify/merge patterns after greedy selection.

Always runs (not conditional on pattern count) to maximize quality.
"""

from __future__ import annotations
from typing import List, Sequence, Optional
from . import matcher, bitset
from .models import Pattern, Solution


def refine_patterns(
    solution: Solution,
    include: Sequence[str],
    exclude: Sequence[str],
) -> Solution:
    """
    Refine patterns by attempting to:
    1. Replace multiple specific patterns with one general pattern
    2. Expand patterns while maintaining 0 FP (in EXACT mode)
    3. Merge similar patterns

    This always runs to maximize quality, regardless of pattern count.

    Args:
        solution: Initial solution from greedy solver
        include: Include dataset
        exclude: Exclude dataset

    Returns:
        Refined solution (same or better quality)
    """

    # Skip refinement if no patterns or only one pattern
    if len(solution.patterns) <= 1:
        return solution

    # Try to find a single pattern that covers all includes
    refined = _try_single_pattern_coverage(solution, include, exclude)
    if refined:
        return refined

    # Try to merge pairs of patterns
    refined = _try_merge_patterns(solution, include, exclude)
    if refined:
        return refined

    # No refinement found - return original
    return solution


def _try_single_pattern_coverage(
    solution: Solution,
    include: Sequence[str],
    exclude: Sequence[str],
) -> Optional[Solution]:
    """
    Try to find a single pattern that covers all includes with 0 FP.

    This is useful when greedy selected multiple patterns that could be
    replaced by one more general pattern.
    """

    # Generate candidate generalizations
    candidates = _generate_generalizations(include)

    # Test each candidate
    for pattern_text in candidates:
        include_mask = 0
        exclude_mask = 0

        # Check if this pattern covers all includes
        for idx, text in enumerate(include):
            if matcher.match_pattern(text.lower(), pattern_text):
                include_mask |= (1 << idx)

        # Check excludes
        for idx, text in enumerate(exclude):
            if matcher.match_pattern(text.lower(), pattern_text):
                exclude_mask |= (1 << idx)

        # Perfect coverage?
        if (bitset.count_bits(include_mask) == len(include) and
            bitset.count_bits(exclude_mask) == 0):

            # Found a single pattern! Create refined solution
            patterns = [
                Pattern(
                    id="P1",
                    text=pattern_text,
                    kind=_classify_pattern(pattern_text),
                    wildcards=pattern_text.count("*"),
                    length=len(pattern_text.replace("*", "")),
                    matches=len(include),
                    fp=0,
                )
            ]

            return Solution(
                expr="P1",
                raw_expr=pattern_text,
                global_inverted=solution.global_inverted,
                term_method=solution.term_method,
                mode=solution.mode,
                options=solution.options,
                patterns=patterns,
                metrics={
                    "covered": len(include),
                    "total_positive": len(include),
                    "fp": 0,
                    "fn": 0,
                    "patterns": 1,
                    "boolean_ops": 0,
                    "wildcards": pattern_text.count("*"),
                    "pattern_chars": len(pattern_text.replace("*", "")),
                },
                witnesses=solution.witnesses,
                expressions=[{
                    "expr": "P1",
                    "raw_expr": pattern_text,
                    "matches": len(include),
                    "fp": 0,
                    "fn": 0,
                }],
            )

    return None


def _generate_generalizations(include: Sequence[str]) -> List[str]:
    """Generate candidate generalization patterns from include set."""

    candidates = set()

    # Find longest common prefix
    if len(include) >= 2:
        include_lower = [s.lower() for s in include]
        common_prefix = include_lower[0]

        for s in include_lower[1:]:
            i = 0
            while i < len(common_prefix) and i < len(s) and common_prefix[i] == s[i]:
                i += 1
            common_prefix = common_prefix[:i]

        # Extend to last delimiter
        if common_prefix:
            last_delim = 0
            for i, ch in enumerate(common_prefix):
                if not ch.isalnum():
                    last_delim = i + 1

            if last_delim > 0:
                candidates.add(common_prefix[:last_delim] + "*")

    # Extract common tokens/segments
    from .tokens import tokenize

    token_freq = {}
    for item in include:
        tokens = tokenize(item.lower(), splitmethod="classchange", min_token_len=3)
        for token in tokens:
            token_freq[token.value] = token_freq.get(token.value, 0) + 1

    # Tokens that appear in all includes
    common_tokens = [tok for tok, freq in token_freq.items() if freq == len(include)]

    for token in common_tokens[:5]:  # Limit
        candidates.add(f"*{token}*")

    # Multi-token patterns
    if len(common_tokens) >= 2:
        for i in range(len(common_tokens)):
            for j in range(i + 1, min(i + 3, len(common_tokens))):
                candidates.add(f"*{common_tokens[i]}*{common_tokens[j]}*")

    return list(candidates)


def _try_merge_patterns(
    solution: Solution,
    include: Sequence[str],
    exclude: Sequence[str],
) -> Optional[Solution]:
    """
    Try to merge pairs of patterns into one more general pattern.

    For each pair, try to find a generalization that covers both.
    """

    if len(solution.patterns) < 2:
        return None

    # Try all pairs
    for i in range(len(solution.patterns)):
        for j in range(i + 1, len(solution.patterns)):
            p1 = solution.patterns[i]
            p2 = solution.patterns[j]

            # Try to find generalization
            generalizations = _generalize_pair(p1.text, p2.text)

            for gen_pattern in generalizations:
                # Test if this generalization maintains 0 FP
                include_mask = 0
                exclude_mask = 0

                for idx, text in enumerate(include):
                    if matcher.match_pattern(text.lower(), gen_pattern):
                        include_mask |= (1 << idx)

                for idx, text in enumerate(exclude):
                    if matcher.match_pattern(text.lower(), gen_pattern):
                        exclude_mask |= (1 << idx)

                # Does it cover both patterns' includes with 0 FP?
                p1_coverage = bitset.count_bits(p1.include_bits) if hasattr(p1, 'include_bits') else 0
                p2_coverage = bitset.count_bits(p2.include_bits) if hasattr(p2, 'include_bits') else 0
                gen_coverage = bitset.count_bits(include_mask)

                if (gen_coverage >= p1_coverage + p2_coverage and
                    bitset.count_bits(exclude_mask) == 0):

                    # Found a merge! Build new solution with this pattern replacing the pair
                    new_patterns = [
                        p for k, p in enumerate(solution.patterns)
                        if k != i and k != j
                    ]

                    new_patterns.append(
                        Pattern(
                            id=f"P{len(new_patterns) + 1}",
                            text=gen_pattern,
                            kind=_classify_pattern(gen_pattern),
                            wildcards=gen_pattern.count("*"),
                            length=len(gen_pattern.replace("*", "")),
                            matches=gen_coverage,
                            fp=0,
                        )
                    )

                    # Rebuild solution
                    # (simplified - would need full evaluation in production)
                    return solution  # TODO: Build proper refined solution

    return None


def _generalize_pair(pattern1: str, pattern2: str) -> List[str]:
    """Generate generalizations that could cover both patterns."""

    generalizations = []

    # Find common prefix/suffix
    common_prefix_len = 0
    for i in range(min(len(pattern1), len(pattern2))):
        if pattern1[i] == pattern2[i]:
            common_prefix_len += 1
        else:
            break

    if common_prefix_len > 3:
        # Extend to delimiter
        prefix = pattern1[:common_prefix_len]
        last_delim = 0
        for i, ch in enumerate(prefix):
            if not ch.isalnum():
                last_delim = i + 1
        if last_delim > 0:
            generalizations.append(prefix[:last_delim] + "*")

    # Common tokens
    from .tokens import tokenize

    tokens1 = set(t.value for t in tokenize(pattern1, splitmethod="classchange", min_token_len=3))
    tokens2 = set(t.value for t in tokenize(pattern2, splitmethod="classchange", min_token_len=3))

    common_tokens = tokens1 & tokens2

    for token in list(common_tokens)[:3]:
        generalizations.append(f"*{token}*")

    return generalizations


def _classify_pattern(pattern: str) -> str:
    """Classify pattern kind based on structure."""

    wildcard_count = pattern.count("*")

    if wildcard_count == 0:
        return "exact"
    elif pattern.startswith("*") and pattern.endswith("*"):
        if wildcard_count == 2:
            return "substring"
        else:
            return "multi"
    elif pattern.startswith("*"):
        return "suffix"
    elif pattern.endswith("*"):
        return "prefix"
    else:
        return "multi"
