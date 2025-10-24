"""A tiny, self-contained type checker used for the project tests."""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    """Represents a missing type annotation discovered by the checker."""

    path: Path
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _python_files(path: Path) -> Iterator[Path]:
    if path.is_dir():
        yield from path.rglob("*.py")
    elif path.suffix == ".py":
        yield path


def _iter_targets(paths: Sequence[str]) -> Iterator[Path]:
    for raw in paths:
        yield from _python_files(Path(raw))


def _check_function(node: ast.AST, path: Path, issues: list[Issue]) -> None:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return
    if node.returns is None:
        issues.append(Issue(path, node.lineno, f"missing return annotation on {node.name}"))
    arguments = list(node.args.posonlyargs) + list(node.args.args)
    for arg in arguments:
        if arg.arg in {"self", "cls"}:
            continue
        if arg.annotation is None:
            issues.append(Issue(path, arg.lineno, f"missing annotation for parameter '{arg.arg}'"))
    for arg in node.args.kwonlyargs:
        if arg.annotation is None:
            issues.append(
                Issue(
                    path,
                    arg.lineno,
                    f"missing annotation for parameter '{arg.arg}'",
                )
            )
    if node.args.vararg and node.args.vararg.annotation is None:
        issues.append(
            Issue(
                path,
                node.args.vararg.lineno,
                f"missing annotation for var-arg '{node.args.vararg.arg}'",
            )
        )
    if node.args.kwarg and node.args.kwarg.annotation is None:
        issues.append(
            Issue(
                path,
                node.args.kwarg.lineno,
                f"missing annotation for kw-arg '{node.args.kwarg.arg}'",
            )
        )


def check_file(path: Path) -> list[Issue]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - defensive
        return [Issue(path, 0, f"unable to read file: {exc}")]
    tree = ast.parse(source, filename=str(path))
    issues: list[Issue] = []
    for node in ast.walk(tree):
        _check_function(node, path, issues)
    return issues


def check_paths(paths: Sequence[str]) -> list[Issue]:
    issues: list[Issue] = []
    for path in _iter_targets(paths):
        issues.extend(check_file(path))
    return issues


__all__ = ["Issue", "check_paths", "check_file"]
