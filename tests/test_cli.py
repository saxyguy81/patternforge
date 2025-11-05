"""End-to-end CLI tests executed directly via :func:`patternforge.cli.main`."""

import argparse
import json
from pathlib import Path

import pytest

from patternforge import cli


def _write(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def test_cli_propose_and_save(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    include = _write(tmp_path / "include.txt", "alpha/module1\nalpha/module2\n")
    exclude = _write(tmp_path / "exclude.txt", "beta/module1\n")
    solution_path = tmp_path / "solution.json"
    cli.main(
        [
            "propose",
            "--include",
            str(include),
            "--exclude",
            str(exclude),
            "--format",
            "json",
            "--out",
            "-",
            "--save-solution",
            str(solution_path),
        ]
    )
    captured = capfd.readouterr()
    payload = json.loads(captured.out)
    assert payload["expr"]
    assert solution_path.exists()


def test_cli_evaluate_explain_and_summarize(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    include = _write(tmp_path / "include.txt", "alpha/module1\nalpha/module2\n")
    exclude = _write(tmp_path / "exclude.txt", "beta/module1\n")
    solution_path = tmp_path / "solution.json"
    cli.main(
        [
            "propose",
            "--include",
            str(include),
            "--exclude",
            str(exclude),
            "--format",
            "json",
            "--out",
            str(solution_path),
        ]
    )
    solution = json.loads(solution_path.read_text())
    atoms_file = tmp_path / "patterns.json"
    atoms_file.write_text(json.dumps({"patterns": solution["patterns"]}))

    cli.main(
        [
            "evaluate",
            "--include",
            str(include),
            "--exclude",
            str(exclude),
            "--expr",
            solution["expr"],
            "--patterns",
            str(atoms_file),
            "--format",
            "json",
        ]
    )
    metrics_out = json.loads(capfd.readouterr().out)
    assert "covered" in metrics_out

    cli.main(["explain", "--solution", str(solution_path), "--format", "text"])
    text = capfd.readouterr().out
    assert "EXPR:" in text

    cli.main(["summarize", "--solution", str(solution_path)])
    summary = capfd.readouterr().out
    assert "covers" in summary


def test_patternforge_main_entrypoint(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    include = _write(tmp_path / "include.txt", "alpha/module1\n")
    from patternforge import main as patternforge_main

    patternforge_main([
        "propose",
        "--include",
        str(include),
        "--format",
        "json",
        "--out",
        "-",
    ])
    assert capfd.readouterr().out


def test_cli_dump_candidates(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    include = _write(tmp_path / "include.txt", "alpha/x\nalpha/y\nbeta/z\n")
    cli.main(
        [
            "dump-candidates",
            "--include",
            str(include),
            "--format",
            "json",
        ]
    )
    dump = json.loads(capfd.readouterr().out)
    assert dump


def test_cli_propose_text_with_schema(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    include = _write(tmp_path / "include.txt", "pd/mod/inst/mem/i0\n")
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "name": "path",
                "delimiter": "/",
                "fields": ["pd", "module", "inst", "leaf", "pin"],
            }
        )
    )
    cli.main(
        [
            "propose",
            "--include",
            str(include),
            "--schema",
            str(schema_path),
            "--format",
            "text",
            "--emit-witnesses",
            "--out",
            "-",
        ]
    )
    text = capfd.readouterr().out
    assert "EXPR:" in text


def test_parse_invert_errors() -> None:
    from patternforge.cli import _parse_invert

    with pytest.raises(argparse.ArgumentTypeError):
        # argparse.ArgumentTypeError derives from ValueError
        _parse_invert("invalid")
