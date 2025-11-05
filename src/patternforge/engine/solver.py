"""Greedy solver and expression evaluator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import matcher
from . import bitset
from .candidates import generate_candidates
from .tokens import Token
from .models import Atom, Candidate, InvertStrategy, Solution, SolveOptions


@dataclass
class _Selection:
    chosen: list[Candidate]
    include_bits: int
    exclude_bits: int


@dataclass
class _Context:
    include: Sequence[str]
    exclude: Sequence[str]
    options: SolveOptions
    token_iter: list[tuple[int, Token]] | None = None
    include_rows: Sequence[object] | None = None
    exclude_rows: Sequence[object] | None = None
    field_getter: callable | None = None


_DEFAULT_WEIGHTS: dict[str, float] = {
    "w_fp": 1.0,
    "w_fn": 1.0,
    "w_atom": 0.05,
    "w_op": 0.02,
    "w_wc": 0.01,
    "w_len": 0.001,
}


def _resolve_weights(options: SolveOptions, field: str | None = None) -> dict[str, float]:
    """Resolve weights for cost function, with optional per-field support.

    Args:
        options: SolveOptions with weights
        field: Optional field name for per-field weight resolution

    Returns:
        Dict of resolved weight values for cost function
    """
    from .utils import get_weight_value

    weights = dict(_DEFAULT_WEIGHTS)
    weights["w_fp"] = get_weight_value(options.weights.w_fp, field)
    weights["w_fn"] = get_weight_value(options.weights.w_fn, field)
    weights["w_atom"] = get_weight_value(options.weights.w_atom, field)
    weights["w_op"] = get_weight_value(options.weights.w_op, field)
    weights["w_wc"] = get_weight_value(options.weights.w_wc, field)
    weights["w_len"] = get_weight_value(options.weights.w_len, field)
    return weights


def _cost(selection: _Selection, include_size: int, weights: dict[str, float]) -> float:
    matched = bitset.count_bits(selection.include_bits)
    fp = bitset.count_bits(selection.exclude_bits)
    fn = include_size - matched
    atoms = len(selection.chosen)
    wildcards = sum(c.wildcards for c in selection.chosen)
    length = sum(c.length for c in selection.chosen)
    ops = max(0, atoms - 1)
    return (
        weights["w_fp"] * fp
        + weights["w_fn"] * fn
        + weights["w_atom"] * atoms
        + weights["w_op"] * ops
        + weights["w_wc"] * wildcards
        + weights["w_len"] * length
    )


def _build_candidates(ctx: _Context) -> list[Candidate]:
    generated = generate_candidates(
        ctx.include,
        splitmethod=ctx.options.splitmethod if isinstance(ctx.options.splitmethod, str) else "classchange",
        min_token_len=ctx.options.min_token_len if isinstance(ctx.options.min_token_len, int) else 3,
        per_word_substrings=ctx.options.per_word_substrings,
        max_multi_segments=ctx.options.max_multi_segments,
        token_iter=ctx.token_iter,
        w_field=ctx.options.weights.w_field,
    )
    candidates: list[Candidate] = []
    limit = ctx.options.budgets.max_candidates
    for pattern, kind, score, field in generated[:limit]:
        include_bits = 0
        exclude_bits = 0
        for idx, text in enumerate(ctx.include):
            if field and ctx.include_rows is not None and ctx.field_getter is not None:
                value = str(ctx.field_getter(ctx.include_rows[idx], field))
                matched = matcher.match_pattern(value, pattern)
            else:
                matched = matcher.match_pattern(text, pattern)
            if matched:
                include_bits |= 1 << idx
        for idx, text in enumerate(ctx.exclude):
            if field and ctx.exclude_rows is not None and ctx.field_getter is not None:
                value = str(ctx.field_getter(ctx.exclude_rows[idx], field)) if idx < len(ctx.exclude_rows) else ""
                matched = matcher.match_pattern(value, pattern)
            else:
                matched = matcher.match_pattern(text, pattern)
            if matched:
                exclude_bits |= 1 << idx
        candidates.append(
            Candidate(
                text=pattern,
                kind=kind,
                score=score,
                include_bits=include_bits,
                exclude_bits=exclude_bits,
                wildcards=pattern.count("*"),
                length=len(pattern.replace("*", "")),
                field=field,
            )
        )
    return candidates


def _greedy_select(ctx: _Context, candidates: list[Candidate]) -> _Selection:
    from .utils import resolve_budget_limit

    weights = _resolve_weights(ctx.options)
    selection = _Selection(chosen=[], include_bits=0, exclude_bits=0)
    best_cost = _cost(selection, len(ctx.include), weights)

    # Convert percentage budgets to absolute limits
    max_fp = resolve_budget_limit(ctx.options.budgets.max_fp, len(ctx.include))
    max_fn = resolve_budget_limit(ctx.options.budgets.max_fn, len(ctx.include))
    max_atoms = resolve_budget_limit(ctx.options.budgets.max_atoms, len(ctx.include))

    changed = True
    while changed:
        changed = False
        best_candidate: Candidate | None = None
        best_candidate_cost = best_cost
        for candidate in candidates:
            new_include_bits = selection.include_bits | candidate.include_bits
            new_exclude_bits = selection.exclude_bits | candidate.exclude_bits
            trial = _Selection(
                chosen=selection.chosen + [candidate],
                include_bits=new_include_bits,
                exclude_bits=new_exclude_bits,
            )
            # Check budget constraints
            trial_fp = bitset.count_bits(trial.exclude_bits)
            trial_fn = len(ctx.include) - bitset.count_bits(trial.include_bits)
            if max_fp is not None and trial_fp > max_fp:
                continue  # Skip candidates that violate max_fp constraint
            if max_fn is not None and trial_fn > max_fn:
                continue  # Skip candidates that violate max_fn constraint
            trial_cost = _cost(trial, len(ctx.include), weights)
            gain = bitset.count_bits(selection.include_bits)
            new_gain = bitset.count_bits(new_include_bits)
            if trial_cost < best_candidate_cost or (
                trial_cost == best_candidate_cost and (
                    new_gain > gain
                    or (
                        new_gain == gain
                        and (
                            # tie-break by specificity: fewer wildcards, then longer length
                            (
                                best_candidate is None
                                or candidate.wildcards < best_candidate.wildcards
                                or (
                                    candidate.wildcards == best_candidate.wildcards
                                    and candidate.length > best_candidate.length
                                )
                            )
                        )
                    )
                )
            ):
                best_candidate_cost = trial_cost
                best_candidate = candidate
        within_limit = (
            max_atoms is None
            or len(selection.chosen) < max_atoms
        )
        if best_candidate is not None and within_limit:
            new_include_bits = selection.include_bits | best_candidate.include_bits
            new_exclude_bits = selection.exclude_bits | best_candidate.exclude_bits
            trial = _Selection(
                chosen=selection.chosen + [best_candidate],
                include_bits=new_include_bits,
                exclude_bits=new_exclude_bits,
            )
            trial_cost = _cost(trial, len(ctx.include), weights)
            if trial_cost <= best_cost:
                selection = trial
                best_cost = trial_cost
                changed = True
    return selection


def _atoms_from_selection(selection: _Selection) -> list[Atom]:
    atoms: list[Atom] = []
    for idx, candidate in enumerate(selection.chosen, start=1):
        atoms.append(
            Atom(
                id=f"P{idx}",
                text=candidate.text,
                kind=candidate.kind,
                wildcards=candidate.wildcards,
                length=candidate.length,
                field=candidate.field,
            )
        )
    return atoms


def _evaluate_atoms(
    atoms: list[Atom], include: Sequence[str], exclude: Sequence[str]
) -> tuple[int, int, int, dict[str, dict[str, int]]]:
    def _matches(text: str, pattern: str) -> bool:
        # Support simple conjunction '&' and difference '-' (A - B) operators in raw patterns
        def _match_piece(piece: str) -> bool:
            piece = piece.strip()
            if not piece:
                return True
            # A - B - C ... => A and not B and not C
            minus_parts = [p.strip().strip("()") for p in piece.split("-") if p.strip()]
            if not minus_parts:
                return True
            left = minus_parts[0]
            if not matcher.match_pattern(text, left):
                return False
            for right in minus_parts[1:]:
                if matcher.match_pattern(text, right):
                    return False
            return True

        parts = [p for p in pattern.split("&")]
        return all(_match_piece(p) for p in parts)
    include_mask = 0
    exclude_mask = 0
    per_atom: dict[str, dict[str, int]] = {}
    for atom in atoms:
        mask_in = 0
        mask_ex = 0
        for idx, text in enumerate(include):
            if _matches(text, atom.text):
                mask_in |= 1 << idx
        for idx, text in enumerate(exclude):
            if _matches(text, atom.text):
                mask_ex |= 1 << idx
        include_mask |= mask_in
        exclude_mask |= mask_ex
        per_atom[atom.id] = {
            "tp": bitset.count_bits(mask_in),
            "fp": bitset.count_bits(mask_ex),
        }
    matched = bitset.count_bits(include_mask)
    fp = bitset.count_bits(exclude_mask)
    fn = len(include) - matched
    return matched, fp, fn, per_atom


def _make_solution(
    include: Sequence[str],
    exclude: Sequence[str],
    selection: _Selection,
    options: SolveOptions,
    inverted: bool,
) -> Solution:
    base_atoms = _atoms_from_selection(selection)
    matched_expr, fp_expr, fn_expr, per_atom = _evaluate_atoms(base_atoms, include, exclude)
    atoms: list[Atom] = []
    for atom in base_atoms:
        stats = per_atom.get(atom.id, {"tp": 0, "fp": 0})
        atoms.append(
            Atom(
                id=atom.id,
                text=atom.text,
                kind=atom.kind,
                wildcards=atom.wildcards,
                length=atom.length,
                negated=atom.negated,
                tp=stats["tp"],
                fp=stats["fp"],
            )
        )
    if inverted:
        matched = len(include) - matched_expr
        fn = matched_expr
        fp = len(exclude) - fp_expr
    else:
        matched = matched_expr
        fp = fp_expr
        fn = fn_expr
    expr = " | ".join(atom.id for atom in atoms) if atoms else "FALSE"
    raw_expr = " | ".join(atom.text for atom in atoms) if atoms else "FALSE"
    def _matches(text: str, pattern: str) -> bool:
        def _match_piece(piece: str) -> bool:
            piece = piece.strip()
            if not piece:
                return True
            minus_parts = [p.strip().strip("()") for p in piece.split("-") if p.strip()]
            if not minus_parts:
                return True
            left = minus_parts[0]
            if not matcher.match_pattern(text, left):
                return False
            for right in minus_parts[1:]:
                if matcher.match_pattern(text, right):
                    return False
            return True

        parts = [p for p in pattern.split("&")]
        return all(_match_piece(p) for p in parts)
    witnesses = {"tp_examples": [], "fp_examples": [], "fn_examples": []}
    dataset_pos = include
    dataset_neg = exclude
    mask_pos = 0
    mask_neg = 0
    for atom in atoms:
        for idx, text in enumerate(dataset_pos):
            if _matches(text, atom.text):
                mask_pos |= 1 << idx
        for idx, text in enumerate(dataset_neg):
            if _matches(text, atom.text):
                mask_neg |= 1 << idx
    for idx, text in enumerate(dataset_pos):
        covered = bool(mask_pos & (1 << idx))
        if (not inverted and covered) or (inverted and not covered):
            witnesses["tp_examples"].append(text)
            if len(witnesses["tp_examples"]) >= 3:
                break
    for idx, text in enumerate(dataset_neg):
        covered = bool(mask_neg & (1 << idx))
        if (not inverted and covered) or (inverted and not covered):
            witnesses["fp_examples"].append(text)
            if len(witnesses["fp_examples"]) >= 3:
                break
    for idx, text in enumerate(dataset_pos):
        covered = bool(mask_pos & (1 << idx))
        if (not inverted and not covered) or (inverted and covered):
            witnesses["fn_examples"].append(text)
            if len(witnesses["fn_examples"]) >= 3:
                break
    metrics = {
        "covered": matched,
        "total_positive": len(include),
        "fp": fp,
        "fn": fn,
        "atoms": len(atoms),
        "boolean_ops": max(0, len(atoms) - 1),
        "wildcards": sum(atom.wildcards for atom in atoms),
        "pattern_chars": sum(atom.length for atom in atoms),
    }
    # Build top-level terms (OR of atoms, possibly conjunctions when enabled)
    terms: list[dict[str, object]] = []
    # Precompute per-atom masks to enable residual stats and potential conjunctions
    masks_in: list[int] = []
    masks_ex: list[int] = []
    for atom in atoms:
        mask_in = 0
        mask_ex = 0
        for idx, text in enumerate(include):
            if _matches(text, atom.text):
                mask_in |= 1 << idx
        for idx, text in enumerate(exclude):
            if _matches(text, atom.text):
                mask_ex |= 1 << idx
        masks_in.append(mask_in)
        masks_ex.append(mask_ex)
    # When allowed, try to pair atoms into conjunction terms that retain TP and reduce FP
    used = [False] * len(atoms)
    if options.allow_complex_expressions:
        for i, atom in enumerate(atoms):
            if used[i]:
                continue
            in_i = masks_in[i]
            ex_i = masks_ex[i]
            best = -1
            best_fp = bitset.count_bits(ex_i)
            best_neg = -1
            best_neg_fp = bitset.count_bits(ex_i)
            for j in range(i + 1, len(atoms)):
                if used[j]:
                    continue
                in_j = masks_in[j]
                ex_j = masks_ex[j]
                inter_in = in_i & in_j
                inter_ex = ex_i & ex_j
                # Only consider if preserves TP of the first while reducing FP
                if bitset.count_bits(inter_in) == bitset.count_bits(in_i) and bitset.count_bits(inter_ex) < best_fp:
                    best = j
                    best_fp = bitset.count_bits(inter_ex)
                    best_in = inter_in
                    best_ex = inter_ex
                # Consider subtraction A - B if B doesn't hit A's includes and reduces FP
                diff_in = in_i & (~in_j)
                diff_ex = ex_i & (~ex_j)
                if bitset.count_bits(diff_in) == bitset.count_bits(in_i) and bitset.count_bits(diff_ex) < best_neg_fp:
                    best_neg = j
                    best_neg_fp = bitset.count_bits(diff_ex)
                    best_neg_in = diff_in
                    best_neg_ex = diff_ex
            if best != -1:
                used[i] = used[best] = True
                a = atoms[i]
                b = atoms[best]
                terms.append(
                    {
                        "expr": f"{a.id} & {b.id}",
                        "raw_expr": f"({a.text}) & ({b.text})",
                        "field": a.field or b.field,
                        "fields": {k: v for k, v in ((a.field, a.text), (b.field, b.text)) if k},
                        "tp": bitset.count_bits(best_in),
                        "fp": bitset.count_bits(best_ex),
                        "fn": len(include) - bitset.count_bits(best_in),
                        "length": a.length + b.length,
                        "include_examples": [include[k] for k in range(len(include)) if (best_in >> k) & 1][:3],
                        "exclude_examples": [exclude[k] for k in range(len(exclude)) if (best_ex >> k) & 1][:3],
                        "_mask_in": best_in,
                        "_mask_ex": best_ex,
                    }
                )
            elif best_neg != -1:
                used[i] = used[best_neg] = True
                a = atoms[i]
                b = atoms[best_neg]
                # Build fields maps for positive and negative if possible
                fields_map = ( {a.field: a.text} if a.field else {} )
                not_fields = ( {b.field: b.text} if b.field else {} )
                terms.append(
                    {
                        "expr": f"{a.id} - {b.id}",
                        "raw_expr": f"({a.text}) - ({b.text})",
                        "field": a.field,
                        "fields": fields_map,
                        "not_fields": not_fields,
                        "tp": bitset.count_bits(best_neg_in),
                        "fp": bitset.count_bits(best_neg_ex),
                        "fn": len(include) - bitset.count_bits(best_neg_in),
                        "length": a.length + b.length,
                        "include_examples": [include[k] for k in range(len(include)) if (best_neg_in >> k) & 1][:3],
                        "exclude_examples": [exclude[k] for k in range(len(exclude)) if (best_neg_ex >> k) & 1][:3],
                        "_mask_in": best_neg_in,
                        "_mask_ex": best_neg_ex,
                    }
                )
            else:
                # fallback single expression
                used[i] = True
                in_m = masks_in[i]
                ex_m = masks_ex[i]
                terms.append(
                    {
                        "expr": atom.id,
                        "raw_expr": atom.text,
                        "field": atom.field,
                        "fields": ({atom.field: atom.text} if atom.field else {}),
                        "tp": bitset.count_bits(in_m),
                        "fp": bitset.count_bits(ex_m),
                        "fn": len(include) - bitset.count_bits(in_m),
                        "length": atom.length,
                        "include_examples": [include[k] for k in range(len(include)) if (in_m >> k) & 1][:3],
                        "exclude_examples": [exclude[k] for k in range(len(exclude)) if (ex_m >> k) & 1][:3],
                        "_mask_in": in_m,
                        "_mask_ex": ex_m,
                    }
                )
    else:
        for i, atom in enumerate(atoms):
            in_m = masks_in[i]
            ex_m = masks_ex[i]
            terms.append(
                {
                    "expr": atom.id,
                    "raw_expr": atom.text,
                    "field": atom.field,
                    "fields": ({atom.field: atom.text} if atom.field else {}),
                    "tp": bitset.count_bits(in_m),
                    "fp": bitset.count_bits(ex_m),
                    "fn": len(include) - bitset.count_bits(in_m),
                    "length": atom.length,
                    "include_examples": [include[k] for k in range(len(include)) if (in_m >> k) & 1][:3],
                    "exclude_examples": [exclude[k] for k in range(len(exclude)) if (ex_m >> k) & 1][:3],
                    "_mask_in": in_m,
                    "_mask_ex": ex_m,
                }
            )
        # end base-expression assembly

    # Residual coverage based on greedy order of atoms
    acc_in = 0
    acc_ex = 0
    for expression in terms:
        term_in = expression.pop("_mask_in", 0)
        term_ex = expression.pop("_mask_ex", 0)
        new_in = term_in & (~acc_in)
        new_ex = term_ex & (~acc_ex)
        expression["incremental_tp"] = bitset.count_bits(new_in)
        expression["incremental_fp"] = bitset.count_bits(new_ex)
        acc_in |= term_in
        acc_ex |= term_ex

    # Enrich with simple token-based conjunction suggestions if enabled and none created
    if options.allow_complex_expressions:
        import re

        def simple_tokens(s: str) -> list[str]:
            return [t.lower() for t in re.split(r"[^A-Za-z0-9]+", s) if len(t) >= 3]

        tokens_in = {t for item in include for t in simple_tokens(item)}
        tokens_ex = {t for item in exclude for t in simple_tokens(item)}
        tokens = sorted(tokens_in | tokens_ex)
        # Build masks for each token pattern *token*
        tok_in_masks: dict[str, int] = {}
        tok_ex_masks: dict[str, int] = {}
        for tok in tokens[:16]:  # limit
            pat = f"*{tok}*"
            m_in = 0
            m_ex = 0
            for idx, text in enumerate(include):
                if matcher.match_pattern(text, pat):
                    m_in |= 1 << idx
            for idx, text in enumerate(exclude):
                if matcher.match_pattern(text, pat):
                    m_ex |= 1 << idx
            tok_in_masks[tok] = m_in
            tok_ex_masks[tok] = m_ex
        # Try pairs that cover many includes and reduce FP
        added = 0
        for i, t1 in enumerate(tokens[:16]):
            for t2 in tokens[i + 1 : 16]:
                inter_in = tok_in_masks[t1] & tok_in_masks[t2]
                inter_ex = tok_ex_masks[t1] & tok_ex_masks[t2]
                if inter_in == 0:
                    continue
                # prefer pairs that cover all includes and 0 FP
                if bitset.count_bits(inter_in) == len(include) and bitset.count_bits(inter_ex) == 0:
                    raw = f"(*{t1}*) & (*{t2}*)"
                    terms.append(
                        {
                            "expr": raw,
                            "raw_expr": raw,
                            "tp": bitset.count_bits(inter_in),
                            "fp": bitset.count_bits(inter_ex),
                            "fn": len(include) - bitset.count_bits(inter_in),
                            "length": len(t1) + len(t2),
                            "include_examples": [include[k] for k in range(len(include)) if (inter_in >> k) & 1][:3],
                            "exclude_examples": [exclude[k] for k in range(len(exclude)) if (inter_ex >> k) & 1][:3],
                            "incremental_tp": 0,
                            "incremental_fp": 0,
                        }
                    )
                    added += 1
                if added >= 2:
                    break
            if added >= 2:
                break
        # Try subtraction pairs t1 - t2 where t2 doesn't hit includes and reduces FP
        if added < 2:
            for t1 in list(tokens_in)[:16]:
                for t2 in list(tokens_ex)[:16]:
                    if t1 == t2:
                        continue
                    diff_in = tok_in_masks[t1] & (~tok_in_masks[t2])
                    diff_ex = tok_ex_masks[t1] & (~tok_ex_masks[t2])
                    if bitset.count_bits(diff_in) == bitset.count_bits(tok_in_masks[t1]) and bitset.count_bits(diff_ex) < bitset.count_bits(tok_ex_masks[t1]):
                        raw = f"(*{t1}*) - (*{t2}*)"
                        terms.append(
                            {
                                "expr": raw,
                                "raw_expr": raw,
                                "tp": bitset.count_bits(diff_in),
                                "fp": bitset.count_bits(diff_ex),
                                "fn": len(include) - bitset.count_bits(diff_in),
                                "length": len(t1) + len(t2),
                                "include_examples": [include[k] for k in range(len(include)) if (diff_in >> k) & 1][:3],
                                "exclude_examples": [exclude[k] for k in range(len(exclude)) if (diff_ex >> k) & 1][:3],
                                "incremental_tp": 0,
                                "incremental_fp": 0,
                            }
                        )
                        added += 1
                        if added >= 2:
                            break
                if added >= 2:
                    break

    # Promote terms' field maps into final expression (OR of per-expression conjunctions)
    def term_to_text(expression: dict[str, object]) -> str:
        fields = expression.get("fields") or {}
        if isinstance(fields, dict) and fields:
            parts = []
            for _, pat in fields.items():
                parts.append(f"({pat})")
            return " & ".join(parts)
        # fallback to raw_expr
        return str(expression.get("raw_expr", "FALSE"))
    expr_text = " | ".join(term_to_text(t) for t in terms) if terms else "FALSE"

    return Solution(
        expr=expr_text,
        raw_expr=expr_text,
        global_inverted=inverted,
        term_method=("subtractive" if inverted else "additive"),
        mode=options.mode.value,
        options={
            "mode": options.mode.value,
            "splitmethod": options.splitmethod,
            "min_token_len": options.min_token_len,
        },
        atoms=atoms,
        metrics=metrics,
        witnesses=witnesses,
        expressions=terms,
    )


def propose_solution(
    include: Sequence[str],
    exclude: Sequence[str],
    options: SolveOptions,
    token_iter: list[tuple[int, Token]] | None = None,
) -> dict[str, object]:
    # In EXACT mode, automatically enforce max_fp=0 if not already set
    from .models import QualityMode, OptimizeBudgets
    if options.mode == QualityMode.EXACT and options.budgets.max_fp is None:
        options = SolveOptions(
            mode=options.mode,
            effort=options.effort,
            splitmethod=options.splitmethod,
            min_token_len=options.min_token_len,
            per_word_substrings=options.per_word_substrings,
            max_multi_segments=options.max_multi_segments,
            invert=options.invert,
            weights=options.weights,
            budgets=OptimizeBudgets(
                max_candidates=options.budgets.max_candidates,
                max_atoms=options.budgets.max_atoms,
                max_fp=0,  # Enforce zero false positives in EXACT mode
                max_fn=options.budgets.max_fn,
            ),
            allow_complex_expressions=options.allow_complex_expressions,
        )
    ctx = _Context(include=include, exclude=exclude, options=options, token_iter=token_iter)
    candidates = _build_candidates(ctx)
    selection = _greedy_select(ctx, candidates)
    base_solution = _make_solution(include, exclude, selection, options, inverted=False)
    if options.invert == InvertStrategy.NEVER:
        return base_solution.to_json()
    if options.invert == InvertStrategy.ALWAYS or not base_solution.atoms:
        inverted_solution = _make_solution(include, exclude, selection, options, inverted=True)
        return inverted_solution.to_json()
    inverted_solution = _make_solution(include, exclude, selection, options, inverted=True)
    weights = _resolve_weights(options)
    base_cost = _cost(selection, len(include), weights)
    include_universe = (1 << len(include)) - 1
    exclude_universe = (1 << len(exclude)) - 1 if exclude else 0
    inverted_selection = _Selection(
        chosen=selection.chosen,
        include_bits=include_universe ^ selection.include_bits,
        exclude_bits=exclude_universe ^ selection.exclude_bits,
    )
    inverted_cost = _cost(inverted_selection, len(include), weights)
    if options.invert == InvertStrategy.ALWAYS or inverted_cost < base_cost:
        return inverted_solution.to_json()
    return base_solution.to_json()


def _default_field_getter(row: object, field: str) -> str:
    """Get field value from row and lowercase it for case-insensitive matching."""
    if isinstance(row, dict):
        return str(row.get(field, "")).lower()
    if isinstance(row, (list, tuple)):
        if field.startswith("f") and field[1:].isdigit():
            idx = int(field[1:])
            return str(row[idx]).lower() if idx < len(row) else ""
        return ""
    return ""


def propose_solution_structured(
    include_rows: Sequence[object],
    exclude_rows: Sequence[object] | None = None,
    fields: list[str] | None = None,
    options: SolveOptions | None = None,
    token_iter: list[tuple] | None = None,
    field_getter: callable | None = None,
) -> dict[str, object]:
    """
    Generate patterns for structured data with multiple fields.

    Args:
        include_rows: Data to match
            - List of dicts: [{"module": "SRAM", "instance": "cpu/cache", "pin": "DIN"}]
            - DataFrame: pd.DataFrame with columns [module, instance, pin]
            - List of tuples: [("SRAM", "cpu/cache", "DIN")] with fields parameter

        exclude_rows: Data to exclude (same format as include_rows)
            - Use None in dict fields as wildcard (don't care)
            - Example: {"module": None, "instance": "debug/*", "pin": None}

        fields: Field names (auto-detected from dict keys or DataFrame columns)

        options: SolveOptions with all configuration
            - Use OptimizeWeights.w_field for field preferences
            - Use splitmethod/min_token_len (scalar or dict) for per-field tokenization
            - Use effort for algorithm selection

        token_iter: [Advanced] Pre-generated token iterator (auto-generated if None)

        field_getter: [Advanced] Custom field getter function(row, field) -> str

    Returns:
        Solution dict with per-field patterns in 'atoms', each with 'field' attribute

    Examples:
        >>> # Simple usage with auto-detection
        >>> include = [
        ...     {"module": "SRAM", "instance": "cpu/cache", "pin": "DIN"},
        ...     {"module": "SRAM", "instance": "cpu/cache", "pin": "DOUT"},
        ... ]
        >>> solution = propose_solution_structured(include, exclude)

        >>> # With field preferences
        >>> from patternforge.engine.models import SolveOptions, OptimizeWeights
        >>> options = SolveOptions(
        ...     weights=OptimizeWeights(
        ...         w_field={"module": 2.0, "pin": 2.0, "instance": 0.5}
        ...     )
        ... )
        >>> solution = propose_solution_structured(include, exclude, options=options)

        >>> # High effort for best quality (slower)
        >>> options = SolveOptions(effort="high")
        >>> solution = propose_solution_structured(include, exclude, options=options)

        >>> # Low effort for quick results
        >>> options = SolveOptions(effort="low")
        >>> solution = propose_solution_structured(large_dataset, large_excludes, options=options)
    """
    from .tokens import make_split_tokenizer, iter_structured_tokens_with_fields

    # Normalize input data
    def normalize_input(rows):
        if rows is None:
            return []

        # Already list of dicts
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows

        # DataFrame (pandas/polars)
        if hasattr(rows, 'to_dict'):
            return rows.to_dict('records')

        # List of tuples with field names
        if isinstance(rows, list) and rows and isinstance(rows[0], tuple):
            if fields is None:
                raise ValueError("fields parameter required for tuple input")
            return [dict(zip(fields, row)) for row in rows]

        # Single dict or other - wrap in list
        if isinstance(rows, dict):
            return [rows]

        return list(rows)

    include_rows = normalize_input(include_rows)
    exclude_rows = normalize_input(exclude_rows)

    # Auto-detect fields from dict keys if not provided
    if fields is None:
        if include_rows and isinstance(include_rows[0], dict):
            fields = list(include_rows[0].keys())
        else:
            raise ValueError("fields must be specified for non-dict rows")

    # Create default options if not provided
    if options is None:
        options = SolveOptions()

    # Extract per-field configuration with utils
    from .utils import get_field_value

    # Generate field tokenizers from options.splitmethod
    if token_iter is None:
        field_tokenizers = {}
        for f in fields:
            method = get_field_value(options.splitmethod, f, "classchange")
            min_len = get_field_value(options.min_token_len, f, 3)
            field_tokenizers[f] = make_split_tokenizer(method, min_token_len=min_len)

        # Generate token iterator automatically
        token_iter = list(iter_structured_tokens_with_fields(
            include_rows,
            field_tokenizers,
            field_order=fields
        ))

    # Adaptive algorithm selection based on N, F, and effort
    from .adaptive import select_algorithm, get_effort_from_string, AlgorithmChoice

    effort_level = get_effort_from_string(options.effort)
    algorithm, config = select_algorithm(
        num_include=len(include_rows),
        num_exclude=len(exclude_rows),
        num_fields=len(fields),
        effort=effort_level
    )

    # Route to appropriate algorithm
    if algorithm == AlgorithmChoice.SCALABLE:
        # Pattern-centric scalable solver for large datasets
        return _propose_solution_structured_scalable(
            include_rows,
            exclude_rows,
            fields,
            field_getter or _default_field_getter,
            options,
            config
        )
    else:
        # Bounded or exhaustive: use expression-based solver
        return _propose_solution_structured_bounded(
            include_rows,
            exclude_rows,
            options,
            token_iter=token_iter,
            field_getter=field_getter,
            config=config
        )


def _propose_solution_structured_scalable(
    include_rows: Sequence[dict],
    exclude_rows: Sequence[dict],
    field_names: list[str],
    field_getter: Callable,
    options: SolveOptions,
    config: dict,
) -> dict[str, object]:
    """
    Scalable pattern-centric implementation for large datasets.
    O(F × P × N) complexity.
    """
    from .structured_scalable import (
        generate_field_patterns_scalable,
        greedy_set_cover_structured,
    )
    from .models import Atom, Solution
    from . import bitset
    from .utils import resolve_budget_limit

    # Generate global patterns per field
    field_patterns = generate_field_patterns_scalable(
        include_rows,
        field_names,
        field_getter,
        max_patterns_per_field=config.get("max_patterns_per_field", 100)
    )

    # Greedy set cover with lazy multi-field construction
    max_fp = resolve_budget_limit(options.budgets.max_fp, len(include_rows))
    if max_fp is None:
        max_fp = 0  # Default to zero FP for structured
    selected_expressions = greedy_set_cover_structured(
        include_rows,
        exclude_rows,
        field_names,
        field_patterns,
        field_getter,
        max_fp=max_fp,
        field_weights=options.weights.w_field
    )

    # Build solution
    atoms = []
    expressions_output = []

    for expr_idx, expr_dict in enumerate(selected_expressions, 1):
        fields_dict = expr_dict["fields"]
        expressions_output.append({
            "expr": f"E{expr_idx}",
            "raw_expr": " & ".join(f"({field}: {pat})" for field, pat in fields_dict.items()),
            "fields": fields_dict,
            "tp": bitset.count_bits(expr_dict["include_mask"]),
            "fp": bitset.count_bits(expr_dict["exclude_mask"]),
            "fn": len(include_rows) - bitset.count_bits(expr_dict["include_mask"]),
        })

        # Create atoms
        for field_name, pattern in fields_dict.items():
            atoms.append(Atom(
                id=f"E{expr_idx}_{field_name}",
                text=pattern,
                kind="structured",
                wildcards=pattern.count("*"),
                length=len(pattern),
                field=field_name,
            ))

    # Compute metrics
    covered_mask = 0
    fp_mask = 0
    for expr_dict in selected_expressions:
        covered_mask |= expr_dict["include_mask"]
        fp_mask |= expr_dict["exclude_mask"]

    metrics = {
        "covered": bitset.count_bits(covered_mask),
        "total_positive": len(include_rows),
        "fp": bitset.count_bits(fp_mask),
        "fn": len(include_rows) - bitset.count_bits(covered_mask),
        "atoms": len(atoms),
        "expressions": len(expressions_output),
        "boolean_ops": max(0, len(expressions_output) - 1),
        "wildcards": sum(a.wildcards for a in atoms),
        "pattern_chars": sum(a.length for a in atoms),
    }

    # Build expression string
    if expressions_output:
        expr_parts = []
        for expr_dict in expressions_output:
            field_parts = [f"({field}: {pat})" for field, pat in expr_dict["fields"].items()]
            expr_parts.append(" & ".join(field_parts))
        expr_text = " | ".join(f"({part})" for part in expr_parts)
    else:
        expr_text = "FALSE"

    # Canonicalize for witnesses
    def canon(row):
        if isinstance(row, dict):
            return "/".join(str(v) for v in row.values() if v)
        return str(row)

    include_strs = [canon(r) for r in include_rows]
    exclude_strs = [canon(r) for r in exclude_rows]

    witnesses = {
        "tp_examples": [include_strs[i] for i in range(len(include_rows)) if (covered_mask >> i) & 1][:3],
        "fp_examples": [exclude_strs[i] for i in range(len(exclude_rows)) if (fp_mask >> i) & 1][:3],
        "fn_examples": [include_strs[i] for i in range(len(include_rows)) if not ((covered_mask >> i) & 1)][:3],
    }

    return Solution(
        expr=expr_text,
        raw_expr=expr_text,
        global_inverted=False,
        term_method="structured_scalable",
        mode=options.mode.value,
        options={
            "mode": options.mode.value,
            "splitmethod": options.splitmethod,
            "algorithm": "scalable",
        },
        atoms=atoms,
        metrics=metrics,
        witnesses=witnesses,
        expressions=expressions_output,
    ).to_json()


def _propose_solution_structured_bounded(
    include_rows: Sequence[object],
    exclude_rows: Sequence[object],
    options: SolveOptions,
    token_iter: list[tuple] | None = None,
    field_getter: callable | None = None,
    config: dict | None = None,
) -> dict[str, object]:
    """
    Bounded expression-based implementation for small-medium datasets.
    O(N) with capped candidates.
    """
    from .structured_expressions import (
        generate_structured_expression_candidates,
        greedy_select_structured_expressions,
    )
    from .utils import resolve_budget_limit

    # Determine field names
    if include_rows and isinstance(include_rows[0], dict):
        field_names = list(include_rows[0].keys())
    else:
        # Infer from token_iter
        field_names = list(set(field for _, _, field in (token_iter or [])))

    # Use default field_getter if not provided
    if field_getter is None:
        field_getter = _default_field_getter

    # Generate per-field patterns for each row
    from .candidates import generate_candidates

    field_patterns = {}  # (row_idx, field_name) -> list of patterns

    for row_idx, row in enumerate(include_rows):
        for field_name in field_names:
            # Get field value
            value = field_getter(row, field_name)
            if not value:
                continue

            # Generate patterns for this field value
            # Use a simplified token approach for per-field pattern generation
            from .tokens import tokenize

            tokens = tokenize(value, splitmethod=options.splitmethod, min_token_len=options.min_token_len)

            patterns = []

            # Exact pattern
            patterns.append(value.lower())

            # Token-based patterns
            for token in tokens:
                # Substring
                patterns.append(f"*{token.value}*")

            # Prefix
            if tokens:
                patterns.append(f"{tokens[0].value}/*")

            # Suffix
            if tokens:
                patterns.append(f"*/{tokens[-1].value}")

            # Multi-segment
            if len(tokens) >= 2:
                for i in range(len(tokens)):
                    for j in range(i + 1, min(i + 3, len(tokens))):
                        segment = [t.value for t in tokens[i:j + 1]]
                        patterns.append("*" + "*".join(segment) + "*")

            field_patterns[(row_idx, field_name)] = patterns

    # Generate expression candidates
    expression_candidates = generate_structured_expression_candidates(
        include_rows=include_rows,
        exclude_rows=exclude_rows,
        field_names=field_names,
        field_patterns=field_patterns,
        field_getter=field_getter,
        field_weights=options.weights.w_field,
        max_expressions_per_row=50,
    )

    # Greedy select terms
    max_fp = resolve_budget_limit(options.budgets.max_fp, len(include_rows))
    if max_fp is None:
        max_fp = 0  # Default to zero FP for structured
    selected_expressions = greedy_select_structured_expressions(
        expressions=expression_candidates,
        num_include=len(include_rows),
        num_exclude=len(exclude_rows),
        max_fp=max_fp,
    )

    # Build solution from selected terms
    from .models import Atom, Solution
    from . import bitset

    # Convert terms to solution format
    atoms = []
    expressions_output = []

    for expression_idx, expression in enumerate(selected_expressions, 1):
        # Create expression dict
        term_dict = {
            "expr": f"T{expression_idx}",
            "raw_expr": " & ".join(f"({field}: {pat})" for field, pat in expression.fields.items() if pat != "*"),
            "fields": {k: v for k, v in expression.fields.items() if v != "*"},
            "tp": bitset.count_bits(expression.include_mask),
            "fp": bitset.count_bits(expression.exclude_mask),
            "fn": len(include_rows) - bitset.count_bits(expression.include_mask),
        }
        expressions_output.append(term_dict)

        # Create atoms for each field pattern in expression
        for field_name, pattern in expression.fields.items():
            if pattern == "*":
                continue  # Skip wildcard fields
            atom = Atom(
                id=f"T{expression_idx}_{field_name}",
                text=pattern,
                kind="structured",
                wildcards=pattern.count("*"),
                length=len(pattern),
                field=field_name,
            )
            atoms.append(atom)

    # Compute final metrics
    covered_mask = 0
    fp_mask = 0
    for expression in selected_expressions:
        covered_mask |= expression.include_mask
        fp_mask |= expression.exclude_mask

    metrics = {
        "covered": bitset.count_bits(covered_mask),
        "total_positive": len(include_rows),
        "fp": bitset.count_bits(fp_mask),
        "fn": len(include_rows) - bitset.count_bits(covered_mask),
        "atoms": len(atoms),
        "terms": len(expressions_output),
        "boolean_ops": max(0, len(expressions_output) - 1),  # Number of OR operations
        "wildcards": sum(a.wildcards for a in atoms),
        "pattern_chars": sum(a.length for a in atoms),
    }

    # Build expression
    if expressions_output:
        expr_parts = []
        for term_dict in expressions_output:
            field_parts = [f"({field}: {pat})" for field, pat in term_dict["fields"].items()]
            expr_parts.append(" & ".join(field_parts))
        expr_text = " | ".join(f"({part})" for part in expr_parts)
    else:
        expr_text = "FALSE"

    # Canonicalize for witnesses
    def canon(row):
        if isinstance(row, dict):
            return "/".join(str(v) for v in row.values() if v)
        return str(row)

    include_strs = [canon(r) for r in include_rows]
    exclude_strs = [canon(r) for r in exclude_rows]

    witnesses = {
        "tp_examples": [include_strs[i] for i in range(len(include_rows)) if (covered_mask >> i) & 1][:3],
        "fp_examples": [exclude_strs[i] for i in range(len(exclude_rows)) if (fp_mask >> i) & 1][:3],
        "fn_examples": [include_strs[i] for i in range(len(include_rows)) if not ((covered_mask >> i) & 1)][:3],
    }

    return Solution(
        expr=expr_text,
        raw_expr=expr_text,
        global_inverted=False,
        term_method="structured",
        mode=options.mode.value,
        options={
            "mode": options.mode.value,
            "splitmethod": options.splitmethod,
            "min_token_len": options.min_token_len,
        },
        atoms=atoms,
        metrics=metrics,
        witnesses=witnesses,
        expressions=expressions_output,
    ).to_json()


def _eval_atom(pattern: str, dataset: Sequence[str]) -> int:
    def _matches(text: str, pat: str) -> bool:
        def _match_piece(piece: str) -> bool:
            piece = piece.strip()
            if not piece:
                return True
            minus_parts = [p.strip().strip("()") for p in piece.split("-") if p.strip()]
            if not minus_parts:
                return True
            left = minus_parts[0]
            if not matcher.match_pattern(text, left):
                return False
            for right in minus_parts[1:]:
                if matcher.match_pattern(text, right):
                    return False
            return True

        parts = [p for p in pat.split("&")]
        return all(_match_piece(p) for p in parts)
    mask = 0
    for idx, item in enumerate(dataset):
        if _matches(item, pattern):
            mask |= 1 << idx
    return mask


class _ExprParser:
    def __init__(self, expr: str) -> None:
        self.expr = expr
        self.pos = 0

    def parse(self) -> list:
        node = self._parse_expr()
        self._skip_spaces()
        if self.pos != len(self.expr):
            raise ValueError("unexpected trailing characters")
        return node

    def _skip_spaces(self) -> None:
        while self.pos < len(self.expr) and self.expr[self.pos].isspace():
            self.pos += 1

    def _parse_expr(self) -> list:
        node = self._parse_term()
        self._skip_spaces()
        while self._peek() == "|":
            self.pos += 1
            rhs = self._parse_term()
            node = ["|", node, rhs]
            self._skip_spaces()
        return node

    def _parse_term(self) -> list:
        node = self._parse_factor()
        self._skip_spaces()
        while self._peek() == "&":
            self.pos += 1
            rhs = self._parse_factor()
            node = ["&", node, rhs]
            self._skip_spaces()
        return node

    def _parse_factor(self) -> list:
        self._skip_spaces()
        ch = self._peek()
        if ch == "!":
            self.pos += 1
            return ["!", self._parse_factor()]
        if ch == "(":
            self.pos += 1
            node = self._parse_expr()
            if self._peek() != ")":
                raise ValueError("missing closing parenthesis")
            self.pos += 1
            return node
        return ["atom", self._parse_atom()]

    def _parse_atom(self) -> str:
        self._skip_spaces()
        if self._peek() != "P":
            raise ValueError("expected atom identifier")
        start = self.pos
        self.pos += 1
        while self.pos < len(self.expr) and self.expr[self.pos].isdigit():
            self.pos += 1
        return self.expr[start:self.pos]

    def _peek(self) -> str:
        if self.pos >= len(self.expr):
            return ""
        return self.expr[self.pos]


def _eval_ast(node: list, masks: dict[str, int], universe: int) -> int:
    op = node[0]
    if op == "atom":
        name = node[1]
        if name not in masks:
            raise KeyError(f"missing atom {name}")
        return masks[name]
    if op == "!":
        return universe ^ _eval_ast(node[1], masks, universe)
    if op == "&":
        return _eval_ast(node[1], masks, universe) & _eval_ast(node[2], masks, universe)
    if op == "|":
        return _eval_ast(node[1], masks, universe) | _eval_ast(node[2], masks, universe)
    raise ValueError(f"unknown op {op}")


def evaluate_expr(
    expr: str,
    atoms: dict[str, str],
    include: Sequence[str],
    exclude: Sequence[str],
) -> dict[str, int]:
    parser = _ExprParser(expr)
    ast = parser.parse()
    include_masks = {name: _eval_atom(pattern, include) for name, pattern in atoms.items()}
    exclude_masks = {name: _eval_atom(pattern, exclude) for name, pattern in atoms.items()}
    include_universe = (1 << len(include)) - 1
    exclude_universe = (1 << len(exclude)) - 1 if exclude else 0
    include_mask = _eval_ast(ast, include_masks, include_universe)
    exclude_mask = _eval_ast(ast, exclude_masks, exclude_universe)
    matched = bitset.count_bits(include_mask)
    fp = bitset.count_bits(exclude_mask)
    fn = len(include) - matched
    return {
        "covered": matched,
        "total_positive": len(include),
        "fp": fp,
        "fn": fn,
    }
