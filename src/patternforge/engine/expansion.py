"""Pattern expansion utilities for refining patterns to be more specific."""

from . import bitset
from .matcher import match_pattern


def expand_pattern(pattern: str, include: list[str], exclude: list[str]) -> str:
    """
    Try to expand a pattern to be more specific while maintaining same coverage.

    Uses incremental honing strategy:
    1. Find common prefix of ALL matching items
    2. Binary search for longest prefix at delimiter boundaries
    3. Early termination when coverage changes

    For example:
    - *sio* → pd_sio/* → pd_sio/asio/asio_spis/* (if still matches same items)
    - pd_sio/* → pd_sio/asio/* → pd_sio/asio/asio_spis/* (if still matches same items)

    Args:
        pattern: Current pattern (e.g., "*sio*")
        include: Items that should match
        exclude: Items that should NOT match

    Returns:
        Expanded pattern (e.g., "pd_sio/asio/asio_spis/*")
    """
    # Safety check to prevent hangs
    if not include:
        return pattern

    # Calculate current coverage - use bitsets for efficiency
    try:
        current_match_bits = 0
        for idx, item in enumerate(include[:100]):  # Safety limit
            if match_pattern(item, pattern):
                current_match_bits |= (1 << idx)

        current_fp_bits = 0
        for idx, item in enumerate(exclude[:100]):  # Safety limit
            if match_pattern(item, pattern):
                current_fp_bits |= (1 << idx)
    except:
        return pattern

    if current_match_bits == 0:
        return pattern

    best_pattern = pattern
    best_length = len(pattern.replace('*', ''))

    # Extract matching items from bitset for common prefix calculation
    current_matches = [include[idx] for idx in range(min(len(include), 100)) if (current_match_bits >> idx) & 1]

    if not current_matches:
        return pattern

    # Find common prefix of all matching items - optimized
    common_prefix = current_matches[0]
    for item in current_matches[1:]:
        i = 0
        max_check = min(len(common_prefix), len(item), 200)  # Safety limit
        while i < max_check and common_prefix[i] == item[i]:
            i += 1
        common_prefix = common_prefix[:i]
        if not common_prefix:  # Early exit if no common prefix
            return best_pattern

    # Strategy 1: If pattern is *something*, try converting to prefix/*
    if pattern.startswith('*') and pattern.endswith('*'):
        # Find delimiter positions - these are natural breakpoints
        delimiters = ['/', '_', '.', '-']
        candidate_positions = []

        for i, ch in enumerate(common_prefix):
            if ch in delimiters:
                candidate_positions.append(i + 1)

        # Always try full common prefix
        if len(common_prefix) > 0:
            candidate_positions.append(len(common_prefix))

        # Binary search strategy: try longest first, stop on first failure
        # This hones in on the best pattern without trying everything
        candidate_positions.sort(reverse=True)

        for pos in candidate_positions[:10]:  # Limit to 10 candidates
            if pos == 0:
                continue

            prefix = common_prefix[:pos]
            new_pattern = prefix + '*'

            # Incremental validation: check matches using bitsets
            try:
                new_match_bits = 0
                for idx, item in enumerate(include[:100]):
                    if match_pattern(item, new_pattern):
                        new_match_bits |= (1 << idx)

                # Quick check: if coverage changed, stop trying shorter prefixes
                if new_match_bits != current_match_bits:
                    break  # Coverage changed, shorter prefixes won't work either

                new_fp_bits = 0
                for idx, item in enumerate(exclude[:100]):
                    if match_pattern(item, new_pattern):
                        new_fp_bits |= (1 << idx)

                # Count FP using bitset
                fp_count = bitset.count_bits(new_fp_bits)
                current_fp_count = bitset.count_bits(current_fp_bits)

                new_length = len(new_pattern.replace('*', ''))

                if fp_count <= current_fp_count and new_length > best_length:
                    best_pattern = new_pattern
                    best_length = new_length
                    # Early termination: found longest possible match
                    if new_length == len(common_prefix):
                        return best_pattern
            except:
                continue

    # Strategy 2: If pattern is prefix/*, try extending the prefix
    elif pattern.endswith('/*'):
        prefix_part = pattern[:-2]  # Remove /*

        # Find where in common_prefix we should extend to
        if common_prefix.startswith(prefix_part):
            remaining = common_prefix[len(prefix_part):]

            # Find delimiter positions in the remaining part
            delimiters = ['/', '_', '.', '-']
            candidate_positions = []

            for i, ch in enumerate(remaining):
                if ch in delimiters:
                    candidate_positions.append(len(prefix_part) + i + 1)

            # Add full length
            if len(common_prefix) > len(prefix_part):
                candidate_positions.append(len(common_prefix))

            # Sort by position (longest first) for binary search strategy
            candidate_positions.sort(reverse=True)

            # Hone in on best pattern: try longest first, stop on coverage change
            for pos in candidate_positions[:10]:  # Limit to 10 candidates
                extended_prefix = common_prefix[:pos]
                new_pattern = extended_prefix + '/*'

                # Incremental validation with bitsets
                try:
                    new_match_bits = 0
                    for idx, item in enumerate(include[:100]):
                        if match_pattern(item, new_pattern):
                            new_match_bits |= (1 << idx)

                    # Early termination: coverage changed, shorter won't work
                    if new_match_bits != current_match_bits:
                        break

                    new_fp_bits = 0
                    for idx, item in enumerate(exclude[:100]):
                        if match_pattern(item, new_pattern):
                            new_fp_bits |= (1 << idx)

                    fp_count = bitset.count_bits(new_fp_bits)
                    current_fp_count = bitset.count_bits(current_fp_bits)

                    new_length = len(new_pattern.replace('*', ''))

                    if fp_count <= current_fp_count and new_length > best_length:
                        best_pattern = new_pattern
                        best_length = new_length
                        # Early termination: found longest possible
                        if new_length >= len(common_prefix):
                            return best_pattern
                except:
                    continue

    return best_pattern


def expand_patterns(patterns: list, include: list[str], exclude: list[str]) -> list:
    """
    Expand all patterns in a solution to be more specific.

    Args:
        patterns: List of Pattern objects
        include: Items that should match
        exclude: Items that should NOT match

    Returns:
        List of expanded Pattern objects
    """
    expanded = []
    for pattern in patterns:
        expanded_text = expand_pattern(pattern.text, include, exclude)
        # Create new pattern with expanded text
        from patternforge.engine.models import Pattern
        expanded_pattern = Pattern(
            id=pattern.id,
            text=expanded_text,
            kind=pattern.kind,
            wildcards=expanded_text.count('*'),
            length=len(expanded_text),
            negated=pattern.negated,
            tp=pattern.tp,
            fp=pattern.fp,
        )
        expanded.append(expanded_pattern)
    return expanded
