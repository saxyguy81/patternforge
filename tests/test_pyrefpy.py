"""Tests for the custom :mod:`pyrefpy` checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pyrefpy import __main__ as pyrefpy_main
from pyrefpy import check_file, check_paths


def test_check_paths_codex_is_clean() -> None:
    issues = check_paths(["codex"])
    assert not issues


def test_cli_invocation() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pyrefpy", "codex", "--quiet"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_main_entrypoint() -> None:
    assert pyrefpy_main.main(["codex", "--quiet"]) == 0


def test_check_file_reports_missing(tmp_path: Path) -> None:
    faulty = tmp_path / "bad.py"
    faulty.write_text("def bad(x):\n    return x\n")
    issues = check_file(faulty)
    assert any("missing return annotation" in issue.message for issue in issues)
