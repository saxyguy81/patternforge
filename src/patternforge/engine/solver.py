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


def _resolve_weights(options: SolveOptions) -> dict[str, float]:
    weights = dict(_DEFAULT_WEIGHTS)
    weights["w_fp"] = options.weights.w_fp
    weights["w_fn"] = options.weights.w_fn
    weights["w_atom"] = options.weights.w_atom
    weights["w_op"] = options.weights.w_op
    weights["w_wc"] = options.weights.w_wc
    weights["w_len"] = options.weights.w_len
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
        splitmethod=ctx.options.splitmethod,
        min_token_len=ctx.options.min_token_len,
        per_word_substrings=ctx.options.per_word_substrings,
        per_word_multi=ctx.options.per_word_multi,
        max_multi_segments=ctx.options.max_multi_segments,
        token_iter=ctx.token_iter,
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
    weights = _resolve_weights(ctx.options)
    selection = _Selection(chosen=[], include_bits=0, exclude_bits=0)
    best_cost = _cost(selection, len(ctx.include), weights)
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
            if ctx.options.budgets.max_fp is not None and trial_fp > ctx.options.budgets.max_fp:
                continue  # Skip candidates that violate max_fp constraint
            if ctx.options.budgets.max_fn is not None and trial_fn > ctx.options.budgets.max_fn:
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
            ctx.options.budgets.max_atoms is None
            or len(selection.chosen) < ctx.options.budgets.max_atoms
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
    if options.allow_complex_terms:
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
                # fallback single term
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
        # end base-term assembly

    # Residual coverage based on greedy order of atoms
    acc_in = 0
    acc_ex = 0
    for term in terms:
        term_in = term.pop("_mask_in", 0)
        term_ex = term.pop("_mask_ex", 0)
        new_in = term_in & (~acc_in)
        new_ex = term_ex & (~acc_ex)
        term["incremental_tp"] = bitset.count_bits(new_in)
        term["incremental_fp"] = bitset.count_bits(new_ex)
        acc_in |= term_in
        acc_ex |= term_ex

    # Enrich with simple token-based conjunction suggestions if enabled and none created
    if options.allow_complex_terms:
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

    # Promote terms' field maps into final expression (OR of per-term conjunctions)
    def term_to_text(term: dict[str, object]) -> str:
        fields = term.get("fields") or {}
        if isinstance(fields, dict) and fields:
            parts = []
            for _, pat in fields.items():
                parts.append(f"({pat})")
            return " & ".join(parts)
        # fallback to raw_expr
        return str(term.get("raw_expr", "FALSE"))
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
        terms=terms,
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
            invert=options.invert,
            weights=options.weights,
            budgets=OptimizeBudgets(
                max_candidates=options.budgets.max_candidates,
                max_atoms=options.budgets.max_atoms,
                max_ops=options.budgets.max_ops,
                depth=options.budgets.depth,
                max_multi_segments=options.budgets.max_multi_segments,
                max_fp=0,  # Enforce zero false positives in EXACT mode
                max_fn=options.budgets.max_fn,
            ),
            allow_not_on_atoms=options.allow_not_on_atoms,
            allow_complex_terms=options.allow_complex_terms,
            min_token_len=options.min_token_len,
            per_word_substrings=options.per_word_substrings,
            per_word_multi=options.per_word_multi,
            per_word_cuts=options.per_word_cuts,
            max_multi_segments=options.max_multi_segments,
            splitmethod=options.splitmethod,
            seed=options.seed,
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
    if isinstance(row, dict):
        return str(row.get(field, ""))
    if isinstance(row, (list, tuple)):
        if field.startswith("f") and field[1:].isdigit():
            idx = int(field[1:])
            return str(row[idx]) if idx < len(row) else ""
        return ""
    return ""


def propose_solution_structured(
    include_rows: Sequence[object],
    exclude_rows: Sequence[object],
    options: SolveOptions,
    token_iter: list[tuple] | None = None,
    field_getter: callable | None = None,
) -> dict[str, object]:
    """
    Propose a solution over structured rows, with per-field atoms. Each atom carries a 'field'.
    - include_rows/exclude_rows: list of dicts or tuples representing fields
    - token_iter: expected to yield (row_index, Token, field_name) triples, e.g., from
      tokens.iter_structured_tokens_with_fields(...)
    - field_getter: optional function(row, field_name) -> str
    """
    # Build canonical strings for matching text/witnesses
    def canon(row: object) -> str:
        if isinstance(row, dict):
            return "/".join(str(v) for v in row.values() if v)
        if isinstance(row, (list, tuple)):
            return "/".join(str(v) for v in row if v)
        return str(row)

    include = [canon(r) for r in include_rows]
    exclude = [canon(r) for r in exclude_rows]

    ctx = _Context(
        include=include,
        exclude=exclude,
        options=options,
        token_iter=token_iter,  # should carry field info
        include_rows=include_rows,
        exclude_rows=exclude_rows,
        field_getter=field_getter or _default_field_getter,
    )
    candidates = _build_candidates(ctx)
    selection = _greedy_select(ctx, candidates)
    # For structured solutions, never invert automatically unless requested
    base_solution = _make_solution(include, exclude, selection, options, inverted=False)
    payload = base_solution.to_json()
    # Ensure atoms carry field; if any None slipped through, attribute by substring presence
    atoms = payload.get("atoms", [])
    if any(a.get("field") is None for a in atoms):
        # Build fields list per row for quick lookup
        def row_fields(row: object) -> dict[str, str]:
            if isinstance(row, dict):
                return {k: str(v) for k, v in row.items()}
            if isinstance(row, (list, tuple)):
                return {f"f{i}": str(v) for i, v in enumerate(row)}
            return {"f0": str(row)}

        rows_fields = [row_fields(r) for r in include_rows]
        field_names = set(n for rf in rows_fields for n in rf.keys())
        for atom in atoms:
            if atom.get("field") is not None:
                continue
            text = atom.get("text", "")
            tokens = [t for t in text.split("*") if t]
            best_field = None
            best_score = -1
            for name in field_names:
                score = 0
                for rf in rows_fields:
                    fv = rf.get(name, "")
                    for tok in tokens:
                        if tok and tok in fv:
                            score += 1
                if score > best_score:
                    best_score = score
                    best_field = name
            atom["field"] = best_field
    return payload


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
