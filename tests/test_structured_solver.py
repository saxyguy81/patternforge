"""Tests for structured per-field solver."""
from __future__ import annotations

from patternforge.engine.models import QualityMode, SolveOptions
from patternforge.engine.solver import propose_solution_structured
from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields
from patternforge.engine.candidates import generate_candidates


def test_propose_solution_structured_per_field_atoms() -> None:
    include_rows = [
        {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
        {"module": "fabric_cache", "instance": "cache1/bank1", "pin": "data_out"},
    ]
    exclude_rows = [
        {"module": "fabric_router", "instance": "rt0/debug", "pin": "trace"},
    ]
    tk = make_split_tokenizer("classchange", min_token_len=3)
    field_tokenizers = {"module": tk, "instance": tk, "pin": tk}
    token_iter = list(iter_structured_tokens_with_fields(include_rows, field_tokenizers, field_order=["module", "instance", "pin"]))  # noqa: E501
    # Ensure candidate generation preserves field
    gen = generate_candidates(
        ["/".join(r.values()) for r in include_rows],
        splitmethod="classchange",
        min_token_len=3,
        per_word_substrings=8,
        per_word_multi=4,
        max_multi_segments=3,
        token_iter=token_iter,
    )
    assert any(entry[3] is not None for entry in gen)
    sol = propose_solution_structured(
        include_rows,
        exclude_rows,
        SolveOptions(mode=QualityMode.APPROX),
        token_iter=token_iter,
    )
    assert sol["atoms"]
    # Ensure atoms carry field information
    assert any("field" in a and a["field"] for a in sol["atoms"])
    # Should cover all include rows
    assert sol["metrics"]["covered"] == len(include_rows)
