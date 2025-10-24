"""patternforge pattern discovery toolkit."""

from collections.abc import Sequence

from .engine.solver import evaluate_expr, propose_solution


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point mirroring :func:`patternforge.cli.main`."""

    from .cli import main as cli_main

    return cli_main(argv)


__all__ = ["main", "propose_solution", "evaluate_expr"]
