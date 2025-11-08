"""Adaptive algorithm selection and effort level management for structured solver.

Selects the best algorithm based on dataset size (N, F) and user-specified effort level.
"""
from __future__ import annotations
from enum import Enum
from typing import Callable, Sequence


class EffortLevel(str, Enum):
    """Effort level for pattern generation and search.

    Higher effort = better quality solutions but slower.
    """
    LOW = "low"           # Fast, minimal candidates, O(N)
    MEDIUM = "medium"     # Balanced, adaptive selection, O(N log N)
    HIGH = "high"         # Best quality, more candidates, O(N log N)
    EXHAUSTIVE = "exhaustive"  # Try everything, O(N²) - small datasets only


class AlgorithmChoice(str, Enum):
    """Which algorithm to use for structured solving."""
    EXHAUSTIVE = "exhaustive"    # Row-centric, enumerate all expression combinations
    BOUNDED = "bounded"           # Row-centric with caps on candidates
    SCALABLE = "scalable"         # Pattern-centric, lazy multi-field construction


def select_algorithm(
    num_include: int,
    num_exclude: int,
    num_fields: int,
    effort: EffortLevel = EffortLevel.MEDIUM,
) -> tuple[AlgorithmChoice, dict]:
    """
    Select the best algorithm based on dataset characteristics and effort level.

    Args:
        num_include: Number of include rows
        num_exclude: Number of exclude rows
        num_fields: Number of fields
        effort: User-specified effort level

    Returns:
        (algorithm_choice, config_params)

    Decision matrix:
        N < 100, F < 5, effort=exhaustive → EXHAUSTIVE (try all combinations)
        N < 1k, F < 8, effort≥medium      → BOUNDED (row-centric with caps)
        N ≥ 1k or F ≥ 8                   → SCALABLE (pattern-centric)
        effort=low                         → SCALABLE (always fastest)
    """
    N = num_include
    F = num_fields

    # Effort=low always uses fastest algorithm
    if effort == EffortLevel.LOW:
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 20,
            "enable_multi_field": False,  # Single-field only for speed
        }

    # Exhaustive only for tiny datasets
    if effort == EffortLevel.EXHAUSTIVE and N < 100 and F <= 4:
        return AlgorithmChoice.EXHAUSTIVE, {
            "max_expressions_per_row": 200,  # No cap
            "max_total_expressions": 10000,
            "explore_all_field_combinations": True,
        }

    # Use SCALABLE algorithm for small-medium datasets (better generalization)
    # BOUNDED algorithm had issues with exact-match explosion on small datasets
    if N < 1000 and F < 8:
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

    # Scalable algorithm for large datasets or high field count
    if effort == EffortLevel.HIGH:
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 200,
            "enable_multi_field": True,
        }
    else:  # MEDIUM
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 100,
            "enable_multi_field": True,
        }


def get_effort_from_string(effort_str: str | None) -> EffortLevel:
    """Convert string to EffortLevel enum."""
    if effort_str is None:
        return EffortLevel.MEDIUM
    try:
        return EffortLevel(effort_str.lower())
    except ValueError:
        return EffortLevel.MEDIUM
