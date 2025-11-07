"""Explanation helpers for patternforge solutions."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from .models import Pattern, Solution
from .solver import _evaluate_patterns


def explain_dict(
    solution: Union[Solution, dict[str, object]], include: Sequence[str], exclude: Sequence[str]
) -> dict[str, object]:
    # Handle both Solution objects and dicts
    if isinstance(solution, Solution):
        patterns = solution.patterns
        global_inverted = solution.global_inverted
        expr = solution.expr
    else:
        patterns_data = solution.get("patterns", [])
        # Handle both old 'tp' and new 'matches' formats
        def _make_pattern(p):
            if isinstance(p, Pattern):
                return p
            # Convert old 'tp' key to new 'matches' key if needed
            pattern_dict = dict(p)
            if 'tp' in pattern_dict and 'matches' not in pattern_dict:
                pattern_dict['matches'] = pattern_dict.pop('tp')
            return Pattern(**pattern_dict)
        patterns = [_make_pattern(p) for p in patterns_data]
        global_inverted = bool(solution.get("global_inverted", False))
        expr = solution.get("expr", "FALSE")

    matched_expr, fp_expr, fn_expr, per_pattern = _evaluate_patterns(patterns, include, exclude)
    if global_inverted:
        matched = len(include) - matched_expr
        fp = len(exclude) - fp_expr
        fn = matched_expr
    else:
        matched = matched_expr
        fp = fp_expr
        fn = fn_expr
    # Build per-term details (top-level OR expressions; currently patterns are expressions)
    expressions: list[dict[str, object]] = []
    for pattern in patterns:
        # summarize per-term using existing per-pattern counts
        expressions.append(
            {
                "expr": pattern.id,
                "raw_expr": pattern.text,
                "field": pattern.field,
                "tp": per_pattern[pattern.id]["tp"],
                "fp": per_pattern[pattern.id]["fp"],
            }
        )

    # Extract witnesses and expressions handling both types
    if isinstance(solution, Solution):
        witnesses = solution.witnesses
        expressions_data = solution.expressions if solution.expressions else expressions
    else:
        witnesses = solution.get("witnesses", {})
        expressions_data = solution.get("expressions", expressions)

    payload = {
        "expr": expr,
        "global_inverted": global_inverted,
        "term_method": ("subtractive" if global_inverted else "additive"),
        "metrics": {
            "covered": matched,
            "total_positive": len(include),
            "fp": fp,
            "fn": fn,
        },
        "patterns": [],
        "witnesses": witnesses,
        "expressions": expressions_data,
    }
    for pattern in patterns:
        entry = {
            "id": pattern.id,
            "text": pattern.text,
            "kind": pattern.kind,
            "wildcards": pattern.wildcards,
            "length": pattern.length,
            "tp": per_pattern[pattern.id]["tp"],
            "fp": per_pattern[pattern.id]["fp"],
        }
        payload["patterns"].append(entry)
    return payload


def explain_text(
    solution: Union[Solution, dict[str, object]], include: Sequence[str], exclude: Sequence[str]
) -> str:
    # Handle both Solution objects and dicts
    if isinstance(solution, Solution):
        expr = solution.expr
        raw_expr = solution.raw_expr or " | ".join(p.text for p in solution.patterns)
        metrics = solution.metrics
        patterns = solution.patterns
        witnesses = solution.witnesses
    else:
        expr = solution.get("expr", "FALSE")
        raw_expr = solution.get("raw_expr") or " | ".join(
            pattern.get("text", "?") for pattern in solution.get("patterns", [])
        )
        metrics = solution.get("metrics", {})
        patterns = solution.get("patterns", [])
        witnesses = solution.get("witnesses", {})

    covered = metrics.get("covered", 0)
    total = metrics.get("total_positive", len(include))
    fp = metrics.get("fp", 0)
    fn = metrics.get("fn", total - covered)
    lines = [
        f"EXPR: {expr}",
        f"RAW:  {raw_expr}",
        f"COVERAGE: {covered}/{total} include matched (FN={fn}), FP={fp}",
        "PATTERNS:",
    ]
    for pattern in patterns:
        if isinstance(pattern, Pattern):
            lines.append(f"  {pattern.id}: {pattern.text} ({pattern.kind})")
        else:
            lines.append(f"  {pattern['id']}: {pattern['text']} ({pattern.get('kind','unknown')})")
    if fp or fn:
        tp_examples = ", ".join(witnesses.get("tp_examples", [])[:3])
        fp_examples = ", ".join(witnesses.get("fp_examples", [])[:3])
        fn_examples = ", ".join(witnesses.get("fn_examples", [])[:3])
        lines.append("EXAMPLES:")
        if tp_examples:
            lines.append(f"  TP: {tp_examples}")
        if fp_examples:
            lines.append(f"  FP: {fp_examples}")
        if fn_examples:
            lines.append(f"  FN: {fn_examples}")
    return "\n".join(lines)


def explain_by_field(
    solution: dict[str, object],
    include_rows: Sequence[dict[str, str]] | Sequence[Sequence[str]],
    field_order: Sequence[str] | None = None,
    delimiter: str = "/",
) -> dict[str, object]:
    """
    Heuristic per-field attribution of patterns based on substring hits in fields of include rows.

    Returns a mapping with for each field: list of patterns touching that field,
    and simple coverage counts by field. This does not change matching semantics.
    """
    # Build field values per row as list[str]
    def row_fields(row: object) -> list[str]:
        if isinstance(row, dict):
            order = list(field_order) if field_order else list(row.keys())
            return [str(row.get(name, "")) for name in order]
        parts = list(row) if isinstance(row, (list, tuple)) else [str(row)]
        return [str(p) for p in parts]

    rows_fields: list[list[str]] = [row_fields(r) for r in include_rows]
    num_fields = max((len(f) for f in rows_fields), default=0)
    names = list(field_order) if field_order else [f"f{i}" for i in range(num_fields)]
    field_hits: dict[str, list[dict[str, object]]] = {name: [] for name in names}

    patterns = solution.get("patterns", [])
    for pattern in patterns:
        text = pattern.get("text", "")
        tokens = [t for t in text.split("*") if t]
        if not tokens:
            continue
        # Count how many tokens appear in each field across sample rows
        counts = [0] * num_fields
        for fields in rows_fields:
            for fi, fv in enumerate(fields):
                for tok in tokens:
                    if tok and tok in fv:
                        counts[fi] += 1
        if counts:
            best = max(range(len(counts)), key=lambda i: counts[i])
            fname = names[best]
            field_hits.setdefault(fname, []).append(pattern)
    return {"by_field": field_hits}


def summarize_text(solution: dict[str, object]) -> str:
    metrics = solution.get("metrics", {})
    covered = metrics.get("covered", 0)
    total = metrics.get("total_positive", 0)
    fp = metrics.get("fp", 0)
    fn = metrics.get("fn", 0)
    patterns = solution.get("patterns", [])
    if not patterns:
        return "No patterns were selected for this dataset."
    primary = patterns[0]
    return (
        "The selection covers "
        f"{covered} of {total} target items (FN={fn}) with {fp} false positives. "
        f"Primary coverage comes from {primary['text']} with {primary.get('tp','?')} matches. "
        f"In total the formula uses {len(patterns)} patterns."
    )


def explain_simple(
    solution: Union[Solution, dict[str, object]], include, exclude
) -> str:
    # Handle both Solution objects and dicts
    if isinstance(solution, Solution):
        expressions = solution.expressions or []
        term_method = solution.term_method
    else:
        expressions = solution.get("expressions", []) or []
        term_method = solution.get("term_method", "additive")

    # Determine if structured by presence of non-empty 'fields'
    structured = any(bool(t.get("fields")) for t in expressions)
    # Sort descending by residual contribution first
    terms_sorted = sorted(expressions, key=lambda t: t.get("incremental_tp", 0), reverse=True)
    # Label depends on term method: additive -> matches, subtractive -> removed
    label = "removed" if term_method == "subtractive" else "matches"
    lines: list[str] = []
    if structured:
        # Collect all field names from expressions to determine ordering
        all_field_names = set()
        for t in expressions:
            fields = t.get("fields", {}) or {}
            not_fields = t.get("not_fields", {}) or {}
            all_field_names.update(fields.keys())
            all_field_names.update(not_fields.keys())
        # Use sorted field names for consistent ordering
        order = sorted(all_field_names)

        for t in terms_sorted:
            fields = t.get("fields", {}) or {}
            not_fields = t.get("not_fields", {}) or {}
            parts: list[str] = []
            # Show fields in sorted order, skip wildcard-only '*' fields
            for k in order:
                pat = fields.get(k)
                if pat and pat != "*":
                    parts.append(f"{k}: {pat}")
            # Append negative fields as '- key: pattern'
            for k in order:
                npat = not_fields.get(k)
                if npat and npat != "*":
                    parts.append(f"- {k}: {npat}")
            tp = t.get("tp", 0)
            rtp = t.get("incremental_tp", 0)
            text = " ".join(parts) if parts else str(t.get("raw_expr", "*"))
            lines.append(f"{text}  (# incremental {label}: {rtp}, total {label}: {tp})")
    else:
        for t in terms_sorted:
            raw = str(t.get("raw_expr", t.get("expr", "*")))
            tp = t.get("tp", 0)
            rtp = t.get("incremental_tp", 0)
            lines.append(f"{raw}  (# incremental {label}: {rtp}, total {label}: {tp})")
    return "\n".join(lines)
