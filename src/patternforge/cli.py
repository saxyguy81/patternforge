"""Command line interface for the patternforge pattern tool."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import io
from .engine.candidates import generate_candidates
from .engine.explain import explain_dict, explain_text, summarize_text
from .engine.models import (
    InvertStrategy,
    OptimizeBudgets,
    OptimizeWeights,
    QualityMode,
    SolveOptions,
)
from .engine.rectangles import plan_rectangles as engine_plan_rectangles
from .engine.solver import evaluate_expr, propose_solution


def _quality_defaults(mode: QualityMode) -> dict[str, int]:
    if mode is QualityMode.EXACT:
        return {"depth": 2, "max_atoms": 8, "max_ops": 12}
    return {"depth": 1, "max_atoms": 4, "max_ops": 6}


def _parse_invert(value: str) -> InvertStrategy:
    mapping = {
        "never": InvertStrategy.NEVER,
        "auto": InvertStrategy.AUTO,
        "always": InvertStrategy.ALWAYS,
    }
    key = value.lower()
    if key not in mapping:
        raise argparse.ArgumentTypeError(f"invalid invert strategy: {value}")
    return mapping[key]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="patternforge", description="Pattern discovery CLI")
    parser.add_argument("-V", "--version", action="version", version="patternforge 0.1")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_options(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument("--mode", choices=[m.value for m in QualityMode], default="EXACT")
        cmd.add_argument("--invert", choices=["never", "auto", "always"], default="auto")
        cmd.add_argument("--splitmethod", choices=["classchange", "char"], default="classchange")
        cmd.add_argument("--schema")
        cmd.add_argument("--delimiter")
        cmd.add_argument("--fields")
        cmd.add_argument("--min-token-len", type=int, default=3)
        cmd.add_argument("--per-word-substrings", type=int, default=16)
        cmd.add_argument("--per-word-multi", type=int, default=4)
        cmd.add_argument("--per-word-cuts", type=int, default=32)
        cmd.add_argument("--max-candidates", type=int, default=4000)
        cmd.add_argument("--depth", type=int)
        cmd.add_argument("--max-atoms", type=int)
        cmd.add_argument("--max-ops", type=int)
        cmd.add_argument("--max-multi-segments", type=int, default=3)
        cmd.add_argument("--max-fp", type=int)
        cmd.add_argument("--max-fn", type=int)
        cmd.add_argument("--w-fp", type=float)
        cmd.add_argument("--w-fn", type=float)
        cmd.add_argument("--w-atom", type=float)
        cmd.add_argument("--w-op", type=float)
        cmd.add_argument("--w-wc", type=float)
        cmd.add_argument("--w-len", type=float)
        cmd.add_argument("--weights")
        cmd.add_argument(
            "--allow-not-on-atoms",
            dest="allow_not_on_atoms",
            action="store_true",
            default=True,
        )
        cmd.add_argument("--no-allow-not-on-atoms", dest="allow_not_on_atoms", action="store_false")
        cmd.add_argument(
            "--allow-complex-terms",
            dest="allow_complex_terms",
            action="store_true",
            default=False,
        )
        cmd.add_argument(
            "--no-allow-complex-terms",
            dest="allow_complex_terms",
            action="store_false",
        )
        cmd.add_argument("--seed", type=int, default=0)
        cmd.add_argument("--threads", type=int, default=1)
        cmd.add_argument("--include", required=True)
        cmd.add_argument("--exclude")
        cmd.add_argument("--out", default="-")
        cmd.add_argument("--format", choices=["text", "json"], default="text")
        cmd.add_argument("--emit-witnesses", action="store_true", default=False)
        cmd.add_argument("--max-examples", type=int, default=8)
        cmd.add_argument("--save-solution")

    propose = sub.add_parser("propose", help="propose a new expression")
    add_common_options(propose)
    propose.add_argument("--structured-terms", dest="structured_terms", action="store_true", default=False,
                        help="Emit structured terms (fields + metrics) instead of full solution when --format json")

    evaluate = sub.add_parser("evaluate", help="evaluate an expression")
    evaluate.add_argument("--include", required=True)
    evaluate.add_argument("--exclude")
    evaluate.add_argument("--expr", required=True)
    evaluate.add_argument("--atoms", required=True)
    evaluate.add_argument("--format", choices=["text", "json"], default="text")

    explain = sub.add_parser("explain", help="explain a saved solution")
    explain.add_argument("--solution", required=True)
    explain.add_argument("--format", choices=["text", "json"], default="text")

    summarize = sub.add_parser("summarize", help="summarize a solution")
    summarize.add_argument("--solution", required=True)

    rectangles = sub.add_parser("plan-rectangles", help="plan rectangle groups")
    rectangles.add_argument("--include", required=True)
    rectangles.add_argument("--rect-budget", type=int, required=True)
    rectangles.add_argument("--rect-penalty", type=float, default=1.0)
    rectangles.add_argument("--exception-weight", type=float, default=1.0)
    rectangles.add_argument("--format", choices=["text", "json"], default="json")

    dumpc = sub.add_parser("dump-candidates", help="debug candidate list")
    dumpc.add_argument("--include", required=True)
    dumpc.add_argument("--splitmethod", choices=["classchange", "char"], default="classchange")
    dumpc.add_argument("--min-token-len", type=int, default=3)
    dumpc.add_argument("--per-word-substrings", type=int, default=16)
    dumpc.add_argument("--per-word-multi", type=int, default=4)
    dumpc.add_argument("--max-multi-segments", type=int, default=3)
    dumpc.add_argument("--top", type=int, default=50)
    dumpc.add_argument("--format", choices=["text", "json"], default="json")
    return parser


def _resolve_weights(args: argparse.Namespace) -> OptimizeWeights:
    if args.weights:
        with open(args.weights, encoding="utf-8") as handle:
            payload = json.load(handle)
        return OptimizeWeights(
            w_fp=payload.get("w_fp", 1.0),
            w_fn=payload.get("w_fn", 1.0),
            w_atom=payload.get("w_atom", 0.05),
            w_op=payload.get("w_op", 0.02),
            w_wc=payload.get("w_wc", 0.01),
            w_len=payload.get("w_len", 0.001),
        )
    return OptimizeWeights(
        w_fp=args.w_fp if args.w_fp is not None else 1.0,
        w_fn=args.w_fn if args.w_fn is not None else 1.0,
        w_atom=args.w_atom if args.w_atom is not None else 0.05,
        w_op=args.w_op if args.w_op is not None else 0.02,
        w_wc=args.w_wc if args.w_wc is not None else 0.01,
        w_len=args.w_len if args.w_len is not None else 0.001,
    )


def _resolve_budgets(args: argparse.Namespace, mode: QualityMode) -> OptimizeBudgets:
    defaults = _quality_defaults(mode)
    return OptimizeBudgets(
        max_candidates=args.max_candidates,
        max_atoms=args.max_atoms if args.max_atoms is not None else defaults["max_atoms"],
        max_ops=args.max_ops if args.max_ops is not None else defaults["max_ops"],
        depth=args.depth if args.depth is not None else defaults["depth"],
        max_multi_segments=args.max_multi_segments,
        max_fp=args.max_fp,
        max_fn=args.max_fn,
    )


def _build_options(args: argparse.Namespace) -> SolveOptions:
    mode = QualityMode(args.mode)
    weights = _resolve_weights(args)
    budgets = _resolve_budgets(args, mode)
    invert = _parse_invert(args.invert)
    return SolveOptions(
        mode=mode,
        invert=invert,
        weights=weights,
        budgets=budgets,
        allow_not_on_atoms=args.allow_not_on_atoms,
        allow_complex_terms=args.allow_complex_terms,
        min_token_len=args.min_token_len,
        per_word_substrings=args.per_word_substrings,
        per_word_multi=args.per_word_multi,
        per_word_cuts=args.per_word_cuts,
        max_multi_segments=args.max_multi_segments,
        splitmethod=args.splitmethod,
        seed=args.seed,
    )


def _load_solution_arg(path: str) -> dict[str, object]:
    if path == "-":
        return json.load(sys.stdin)
    return io.load_solution(path)


def _emit_output(data: dict[str, object] | str, fmt: str, out_path: str) -> None:
    if fmt == "json":
        if isinstance(data, str):
            payload = {"text": data}
        else:
            payload = data
        io.write_json(payload, out_path)
    else:
        text = data if isinstance(data, str) else json.dumps(data, indent=2, sort_keys=True)
        io.write_text(text + ("\n" if not text.endswith("\n") else ""), out_path)


def _command_propose(args: argparse.Namespace) -> None:
    items = io.ensure_items(args.include, args.exclude)
    options = _build_options(args)
    solution = propose_solution(items.include, items.exclude, options)
    if args.structured_terms and args.format == "json":
        terms = solution.get("terms", [])
        payload = [
            {
                "fields": t.get("fields", {}),
                "tp": t.get("tp", 0),
                "fp": t.get("fp", 0),
                "fn": t.get("fn", 0),
                "residual_tp": t.get("residual_tp", 0),
                "residual_fp": t.get("residual_fp", 0),
                "length": t.get("length", 0),
            }
            for t in terms
        ]
        io.write_json({"terms": payload}, args.out)
        return
    if args.emit_witnesses:
        witnesses = solution.setdefault("witnesses", {})
        witnesses.setdefault("tp_examples", [])
        witnesses.setdefault("fp_examples", [])
        witnesses.setdefault("fn_examples", [])
    solution.setdefault("include", list(items.include))
    if items.exclude:
        solution.setdefault("exclude", list(items.exclude))
    if args.format == "json":
        io.write_json(solution, args.out)
    else:
        text = explain_text(solution, items.include, items.exclude)
        io.write_text(text + "\n", args.out)
    if args.save_solution:
        io.save_solution(solution, args.save_solution)


def _command_evaluate(args: argparse.Namespace) -> None:
    include = io.read_items(args.include)
    exclude = io.read_items(args.exclude) if args.exclude else []
    with open(args.atoms, encoding="utf-8") as handle:
        atom_payload = json.load(handle)
    if isinstance(atom_payload, dict) and "atoms" in atom_payload:
        atom_list = atom_payload["atoms"]
    elif isinstance(atom_payload, list):
        atom_list = atom_payload
    else:
        raise ValueError("atoms file must contain a list or an object with an 'atoms' key")
    # If expr references raw patterns instead of Pi atoms, map each top-level OR term to Pi
    expr = args.expr
    if "P" not in expr:
        # naive split on '|'; safe because our solver emits ' | ' between term conjunctions
        parts = [p.strip() for p in expr.split("|") if p.strip()]
        atoms = {f"P{i+1}": part for i, part in enumerate(parts)}
        expr = " | ".join(atoms.keys()) if atoms else "FALSE"
    else:
        atoms = {atom["id"]: atom["text"] for atom in atom_list}
    metrics = evaluate_expr(expr, atoms, include, exclude)
    if args.format == "json":
        io.write_json(metrics, "-")
    else:
        text = (
            f"EXPR: {args.expr}\n"
            f"COVERED {metrics['covered']} of {metrics['total_positive']} "
            f"(FN={metrics['fn']}) FP={metrics['fp']}"
        )
        io.write_text(text + "\n", "-")


def _command_explain(args: argparse.Namespace) -> None:
    solution = _load_solution_arg(args.solution)
    include = solution.get("include", [])
    exclude = solution.get("exclude", [])
    if args.format == "json":
        payload = explain_dict(solution, include, exclude)
        io.write_json(payload, "-")
    else:
        text = explain_text(solution, include, exclude)
        io.write_text(text + "\n", "-")


def _command_summarize(args: argparse.Namespace) -> None:
    solution = _load_solution_arg(args.solution)
    text = summarize_text(solution)
    io.write_text(text + "\n", "-")


def _command_rectangles(args: argparse.Namespace) -> None:
    include = io.read_items(args.include)
    plan = engine_plan_rectangles(
        include, args.rect_budget, args.rect_penalty, args.exception_weight
    )
    if args.format == "json":
        io.write_json(plan, "-")
    else:
        lines = [f"{rect['prefix']}: {rect['count']}" for rect in plan["rectangles"]]
        io.write_text("\n".join(lines) + "\n", "-")


def _command_dump_candidates(args: argparse.Namespace) -> None:
    include = io.read_items(args.include)
    generated = generate_candidates(
        include,
        splitmethod=args.splitmethod,
        min_token_len=args.min_token_len,
        per_word_substrings=args.per_word_substrings,
        per_word_multi=args.per_word_multi,
        max_multi_segments=args.max_multi_segments,
    )
    top = generated[: args.top]
    if args.format == "json":
        payload = []
        for entry in top:
            if len(entry) == 3:
                pattern, kind, score = entry
                field = None
            else:
                pattern, kind, score, field = entry
            obj = {"pattern": pattern, "kind": kind, "score": score}
            if field is not None:
                obj["field"] = field
            payload.append(obj)
        io.write_json(payload, "-")
    else:
        lines = []
        for entry in top:
            if len(entry) == 3:
                pattern, kind, score = entry
                lines.append(f"{pattern}\t{kind}\t{score:.2f}")
            else:
                pattern, kind, score, field = entry
                lines.append(f"{pattern}\t{kind}\t{score:.2f}\t{field}")
        io.write_text("\n".join(lines) + "\n", "-")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command
    if command == "propose":
        _command_propose(args)
    elif command == "evaluate":
        _command_evaluate(args)
    elif command == "explain":
        _command_explain(args)
    elif command == "summarize":
        _command_summarize(args)
    elif command == "plan-rectangles":
        _command_rectangles(args)
    elif command == "dump-candidates":
        _command_dump_candidates(args)
    else:
        parser.error(f"unknown command {command}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
