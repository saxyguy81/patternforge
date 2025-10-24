"""Command line entry point for :mod:`pyrefpy`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import check_paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pyrefpy", description="Simple annotation checker")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["codex"],
        help="files or directories to inspect",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress success output")
    args = parser.parse_args(argv)
    issues = check_paths(args.paths)
    if issues:
        for issue in issues:
            sys.stderr.write(issue.format() + "\n")
        return 1
    if not args.quiet:
        sys.stdout.write("pyrefpy: success\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
