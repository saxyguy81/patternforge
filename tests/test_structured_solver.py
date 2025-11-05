"""Tests for structured per-field solver."""
from __future__ import annotations

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
        max_multi_segments=3,
        token_iter=token_iter,
    )
    assert any(entry[3] is not None for entry in gen)
    sol = propose_solution_structured(
        include_rows,
        exclude_rows,
        token_iter=token_iter,
        mode="APPROX",
    )
    assert sol.patterns
    # Ensure patterns carry field information
    assert any(hasattr(a, 'field') and a.field for a in sol.patterns)
    # Should cover all include rows
    assert sol.metrics["covered"] == len(include_rows)


def test_structured_minus_term_fields() -> None:
    include_rows = [
        {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
        {"module": "fabric_cache", "instance": "cache0/bank1", "pin": "data_out"},
    ]
    exclude_rows = [
        {"module": "fabric_dbg", "instance": "trace", "pin": "tag"},
    ]

    def canon(r: dict[str, str]) -> str:
        return "/".join(filter(None, (r.get("module"), r.get("instance"), r.get("pin"))))

    include = [canon(r) for r in include_rows]
    exclude = [canon(r) for r in exclude_rows]

    from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields
    from patternforge.engine.solver import propose_solution_structured

    tk = make_split_tokenizer("classchange", min_token_len=3)
    fts = {"module": tk, "instance": tk, "pin": tk}
    tok_iter = list(iter_structured_tokens_with_fields(include_rows, fts, field_order=["module", "instance", "pin"]))
    sol = propose_solution_structured(include_rows, exclude_rows,
        token_iter=tok_iter,
        mode="EXACT",
        allow_complex_expressions=True
    )
    # Either a minus expression exists or the positive expression(s) suffice; when minus exists, it should reduce FP and carry not_fields
    minus_expressions = [t for t in sol.expressions if "-" in t.get("expr", "") or "-" in t.get("raw_expr", "")]
    for t in minus_expressions:
        assert t.get("fp", 0) == 0
        # not_fields may be present for structured pattern pairing
        nf = t.get("not_fields", {})
        if nf:
            assert isinstance(nf, dict)
