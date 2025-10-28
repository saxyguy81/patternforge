"""Explanation helpers for patternforge solutions."""
from __future__ import annotations

from collections.abc import Sequence

from .models import Atom
from .solver import _evaluate_atoms


def explain_dict(
    solution: dict[str, object], include: Sequence[str], exclude: Sequence[str]
) -> dict[str, object]:
    atoms = [Atom(**atom) for atom in solution.get("atoms", [])]
    matched_expr, fp_expr, fn_expr, per_atom = _evaluate_atoms(atoms, include, exclude)
    global_inverted = bool(solution.get("global_inverted", False))
    if global_inverted:
        matched = len(include) - matched_expr
        fp = len(exclude) - fp_expr
        fn = matched_expr
    else:
        matched = matched_expr
        fp = fp_expr
        fn = fn_expr
    # Build per-term details (top-level OR terms; currently atoms are terms)
    terms: list[dict[str, object]] = []
    for atom in atoms:
        # summarize per-term using existing per-atom counts
        terms.append(
            {
                "expr": atom.id,
                "raw_expr": atom.text,
                "field": atom.field,
                "tp": per_atom[atom.id]["tp"],
                "fp": per_atom[atom.id]["fp"],
            }
        )

    payload = {
        "expr": solution.get("expr", "FALSE"),
        "global_inverted": global_inverted,
        "term_method": ("subtractive" if global_inverted else "additive"),
        "metrics": {
            "covered": matched,
            "total_positive": len(include),
            "fp": fp,
            "fn": fn,
        },
        "atoms": [],
        "witnesses": solution.get("witnesses", {}),
        "terms": solution.get("terms", terms),
    }
    for atom in atoms:
        entry = {
            "id": atom.id,
            "text": atom.text,
            "kind": atom.kind,
            "wildcards": atom.wildcards,
            "length": atom.length,
            "tp": per_atom[atom.id]["tp"],
            "fp": per_atom[atom.id]["fp"],
        }
        payload["atoms"].append(entry)
    return payload


def explain_text(
    solution: dict[str, object], include: Sequence[str], exclude: Sequence[str]
) -> str:
    expr = solution.get("expr", "FALSE")
    raw_expr = solution.get("raw_expr") or " | ".join(
        atom.get("text", "?") for atom in solution.get("atoms", [])
    )
    metrics = solution.get("metrics", {})
    covered = metrics.get("covered", 0)
    total = metrics.get("total_positive", len(include))
    fp = metrics.get("fp", 0)
    fn = metrics.get("fn", total - covered)
    lines = [
        f"EXPR: {expr}",
        f"RAW:  {raw_expr}",
        f"COVERAGE: {covered}/{total} include matched (FN={fn}), FP={fp}",
        "ATOMS:",
    ]
    for atom in solution.get("atoms", []):
        lines.append(f"  {atom['id']}: {atom['text']} ({atom.get('kind','unknown')})")
    if fp or fn:
        witnesses = solution.get("witnesses", {})
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
    Heuristic per-field attribution of atoms based on substring hits in fields of include rows.

    Returns a mapping with for each field: list of atoms touching that field,
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

    atoms = solution.get("atoms", [])
    for atom in atoms:
        text = atom.get("text", "")
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
            field_hits.setdefault(fname, []).append(atom)
    return {"by_field": field_hits}


def summarize_text(solution: dict[str, object]) -> str:
    metrics = solution.get("metrics", {})
    covered = metrics.get("covered", 0)
    total = metrics.get("total_positive", 0)
    fp = metrics.get("fp", 0)
    fn = metrics.get("fn", 0)
    atoms = solution.get("atoms", [])
    if not atoms:
        return "No atoms were selected for this dataset."
    primary = atoms[0]
    return (
        "The selection covers "
        f"{covered} of {total} target items (FN={fn}) with {fp} false positives. "
        f"Primary coverage comes from {primary['text']} with {primary.get('tp','?')} matches. "
        f"In total the formula uses {len(atoms)} atoms."
    )


def explain_simple(
    solution: dict[str, object], include, exclude
) -> str:
    terms = solution.get("terms", []) or []
    # Determine if structured by presence of non-empty 'fields'
    structured = any(bool(t.get("fields")) for t in terms)
    # Sort descending by residual contribution first
    terms_sorted = sorted(terms, key=lambda t: t.get("incremental_tp", 0), reverse=True)
    # Label depends on term method: additive -> matches, subtractive -> removed
    term_method = solution.get("term_method", "additive")
    label = "removed" if term_method == "subtractive" else "matches"
    lines: list[str] = []
    if structured:
        order = ["module", "instance", "pin"]
        for t in terms_sorted:
            fields = t.get("fields", {}) or {}
            not_fields = t.get("not_fields", {}) or {}
            parts: list[str] = []
            # Show canonical fields in order, skip wildcard-only '*' fields
            for k in order:
                pat = fields.get(k)
                if pat and pat != "*":
                    parts.append(f"{k}: {pat}")
            # Include any additional fields deterministically, skipping '*'
            extra_keys = sorted(set(fields.keys()) - set(order))
            for k in extra_keys:
                pat = fields.get(k)
                if pat and pat != "*":
                    parts.append(f"{k}: {pat}")
            # Append negative fields as '- key: pattern'
            for k in order:
                npat = not_fields.get(k)
                if npat and npat != "*":
                    parts.append(f"- {k}: {npat}")
            for k in sorted(set(not_fields.keys()) - set(order)):
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
