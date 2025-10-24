"""Greedy solver and expression evaluator."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import matcher
from .candidates import generate_candidates
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
    matched = selection.include_bits.bit_count()
    fp = selection.exclude_bits.bit_count()
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
    )
    candidates: list[Candidate] = []
    limit = ctx.options.budgets.max_candidates
    for pattern, kind, score in generated[:limit]:
        include_bits = 0
        exclude_bits = 0
        for idx, text in enumerate(ctx.include):
            if matcher.match_pattern(text, pattern):
                include_bits |= 1 << idx
        for idx, text in enumerate(ctx.exclude):
            if matcher.match_pattern(text, pattern):
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
            trial_cost = _cost(trial, len(ctx.include), weights)
            gain = selection.include_bits.bit_count()
            new_gain = new_include_bits.bit_count()
            if trial_cost < best_candidate_cost or (
                trial_cost == best_candidate_cost and new_gain > gain
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
            )
        )
    return atoms


def _evaluate_atoms(
    atoms: list[Atom], include: Sequence[str], exclude: Sequence[str]
) -> tuple[int, int, int, dict[str, dict[str, int]]]:
    include_mask = 0
    exclude_mask = 0
    per_atom: dict[str, dict[str, int]] = {}
    for atom in atoms:
        mask_in = 0
        mask_ex = 0
        for idx, text in enumerate(include):
            if matcher.match_pattern(text, atom.text):
                mask_in |= 1 << idx
        for idx, text in enumerate(exclude):
            if matcher.match_pattern(text, atom.text):
                mask_ex |= 1 << idx
        include_mask |= mask_in
        exclude_mask |= mask_ex
        per_atom[atom.id] = {
            "tp": mask_in.bit_count(),
            "fp": mask_ex.bit_count(),
        }
    matched = include_mask.bit_count()
    fp = exclude_mask.bit_count()
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
    witnesses = {"tp_examples": [], "fp_examples": [], "fn_examples": []}
    dataset_pos = include
    dataset_neg = exclude
    mask_pos = 0
    mask_neg = 0
    for atom in atoms:
        for idx, text in enumerate(dataset_pos):
            if matcher.match_pattern(text, atom.text):
                mask_pos |= 1 << idx
        for idx, text in enumerate(dataset_neg):
            if matcher.match_pattern(text, atom.text):
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
    return Solution(
        expr=expr,
        global_inverted=inverted,
        mode=options.mode.value,
        options={
            "mode": options.mode.value,
            "splitmethod": options.splitmethod,
            "min_token_len": options.min_token_len,
        },
        atoms=atoms,
        metrics=metrics,
        witnesses=witnesses,
    )


def propose_solution(
    include: Sequence[str], exclude: Sequence[str], options: SolveOptions
) -> dict[str, object]:
    ctx = _Context(include=include, exclude=exclude, options=options)
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


def _eval_atom(pattern: str, dataset: Sequence[str]) -> int:
    mask = 0
    for idx, item in enumerate(dataset):
        if matcher.match_pattern(item, pattern):
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
    matched = include_mask.bit_count()
    fp = exclude_mask.bit_count()
    fn = len(include) - matched
    return {
        "covered": matched,
        "total_positive": len(include),
        "fp": fp,
        "fn": fn,
    }
