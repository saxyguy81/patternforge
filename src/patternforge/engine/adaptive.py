"""Adaptive algorithm selection and effort level management for structured solver.

Selects the best algorithm based on dataset size (N, F) and user-specified effort level.

After comprehensive performance analysis, SCALABLE algorithm is used for all cases
(BOUNDED algorithm was removed due to inferior quality and performance).
"""
from __future__ import annotations
from enum import Enum


class EffortLevel(str, Enum):
    """Effort level for pattern generation and search.

    Higher effort = better quality solutions but slower.
    """
    LOW = "low"           # Fast, minimal candidates
    MEDIUM = "medium"     # Balanced (default)
    HIGH = "high"         # Best quality, more candidates
    EXHAUSTIVE = "exhaustive"  # Try everything (future: small datasets only)


class AlgorithmChoice(str, Enum):
    """Which algorithm to use for structured solving.

    Note: BOUNDED algorithm was removed after performance analysis showed
    SCALABLE to be 1.3-7.4x faster for typical datasets with equal or better quality.
    """
    SCALABLE = "scalable"         # Pattern-centric, O(F × P × N) - used for all cases
    # EXHAUSTIVE = "exhaustive"   # Future: Row-centric for tiny datasets with effort=exhaustive


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

    Algorithm Selection:
        After performance analysis (see PERFORMANCE_ANALYSIS.md), SCALABLE algorithm
        is used for all cases. It provides:
        - 1.3-7.4x faster performance for typical datasets (N<100)
        - Equal or better quality (fewer patterns, 0 FP)
        - Simpler codebase (single algorithm to maintain)

    Effort Level Controls:
        - LOW: Fewer patterns per field, single-field only
        - MEDIUM: Balanced (default)
        - HIGH: More patterns per field, enables multi-field expressions
        - EXHAUSTIVE: Reserved for future EXHAUSTIVE algorithm (tiny datasets)
    """
    # Adjust SCALABLE parameters based on effort level
    if effort == EffortLevel.LOW:
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 50,
            "enable_multi_field": False,  # Single-field only for speed
        }
    elif effort == EffortLevel.HIGH or effort == EffortLevel.EXHAUSTIVE:
        return AlgorithmChoice.SCALABLE, {
            "max_patterns_per_field": 200,
            "enable_multi_field": True,
        }
    else:  # MEDIUM (default)
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
