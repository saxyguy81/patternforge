"""Utility functions for SolveOptions parameter resolution."""
from __future__ import annotations
from typing import TypeVar


T = TypeVar('T', int, float, str)


def get_field_value(param: T | dict[str, T], field: str | None, default: T) -> T:
    """Get value for a field from scalar or dict parameter.

    Args:
        param: Scalar value or dict with per-field values
        field: Field name to look up (None for single-field patterns)
        default: Hardcoded default if not found

    Returns:
        Resolved value for the field

    Examples:
        >>> get_field_value("classchange", "module", "classchange")
        "classchange"
        >>> get_field_value({"instance": "char"}, "instance", "classchange")
        "char"
        >>> get_field_value({"instance": "char"}, "module", "classchange")
        "classchange"
    """
    if isinstance(param, dict):
        return param.get(field, default) if field else default
    return param


def get_weight_value(weight: float | dict[str, float], field: str | None) -> float:
    """Get weight value for a field from scalar or dict weight.

    Args:
        weight: Scalar weight or dict with per-field weights
        field: Field name to look up (None for single-field patterns)

    Returns:
        Resolved weight for the field (implicit default = 1.0)

    Examples:
        >>> get_weight_value(1.0, "module")
        1.0
        >>> get_weight_value({"module": 10.0, "pin": 1.0}, "module")
        10.0
        >>> get_weight_value({"module": 10.0}, "pin")
        1.0
    """
    if isinstance(weight, dict):
        return weight.get(field, 1.0) if field else 1.0
    return weight


def resolve_budget_limit(limit: int | float | None, num_rows: int) -> int | None:
    """Resolve budget limit from absolute count or percentage.

    Args:
        limit: Budget limit (int=absolute, 0<float<1=percentage, 0=zero, None=no limit)
        num_rows: Total number of rows (for percentage calculation)

    Returns:
        Absolute count or None (no limit)

    Examples:
        >>> resolve_budget_limit(5, 100)
        5
        >>> resolve_budget_limit(0.01, 100)  # 1%
        1
        >>> resolve_budget_limit(0.05, 100)  # 5%
        5
        >>> resolve_budget_limit(0, 100)
        0
        >>> resolve_budget_limit(None, 100)
        None
    """
    if limit is None:
        return None

    if limit == 0:
        return 0

    if isinstance(limit, float) and 0 < limit < 1:
        # Percentage - convert to absolute count
        return int(limit * num_rows)

    # Absolute count
    return int(limit)
