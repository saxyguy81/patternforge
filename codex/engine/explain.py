"""Explanation helpers for codex solutions."""
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
    payload = {
        "expr": solution.get("expr", "FALSE"),
        "global_inverted": global_inverted,
        "metrics": {
            "covered": matched,
            "total_positive": len(include),
            "fp": fp,
            "fn": fn,
        },
        "atoms": [],
        "witnesses": solution.get("witnesses", {}),
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
    metrics = solution.get("metrics", {})
    covered = metrics.get("covered", 0)
    total = metrics.get("total_positive", len(include))
    fp = metrics.get("fp", 0)
    fn = metrics.get("fn", total - covered)
    lines = [
        f"EXPR: {expr}",
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
