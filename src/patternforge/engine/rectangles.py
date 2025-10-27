"""Simple rectangle planner for CLI support."""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence


def plan_rectangles(
    include: Sequence[str],
    rect_budget: int,
    rect_penalty: float,
    exception_weight: float,
) -> dict[str, object]:
    counter = Counter()
    for item in include:
        parts = item.split("/")
        if parts:
            counter[parts[0]] += 1
        else:
            counter["*"] += 1
    top = counter.most_common(rect_budget)
    rectangles: list[dict[str, object]] = []
    for prefix, count in top:
        rectangles.append(
            {
                "prefix": prefix,
                "count": count,
                "score": max(count - rect_penalty, 0) * exception_weight,
                "pattern": f"{prefix}*",
                "kind": "prefix",
            }
        )
    return {"rectangles": rectangles, "total": len(include)}
