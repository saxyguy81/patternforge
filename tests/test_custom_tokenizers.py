"""Tests for custom tokenization and per-field tokenizers."""
from __future__ import annotations

import re

from patternforge.engine.candidates import generate_candidates
from patternforge.engine.solver import propose_solution
from patternforge.engine.tokens import (
    Token,
    iter_custom_tokens,
    iter_structured_tokens,
    make_split_tokenizer,
)


def test_make_split_tokenizer_and_iter_custom_tokens() -> None:
    items = ["alpha-beta_gamma/123"]
    tk = make_split_tokenizer("classchange", min_token_len=3)
    toks = list(iter_custom_tokens(items, tk))
    assert toks
    idx, t0 = toks[0]
    assert idx == 0
    values = {t.value for _, t in toks}
    # classchange splits by character class; keep alpha groups length>=3
    assert "alpha" in values
    assert "beta" in values or "beta_gamma" in values or "gamma" in values


def test_iter_structured_tokens_dict() -> None:
    rows = [
        {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
        {"module": "fabric_cache", "instance": "cache1/bank1", "pin": "data_out"},
    ]
    tk_module = make_split_tokenizer("classchange", min_token_len=3)
    tk_instance = make_split_tokenizer("classchange", min_token_len=3)
    tk_pin = make_split_tokenizer("classchange", min_token_len=3)
    field_tokenizers = {"module": tk_module, "instance": tk_instance, "pin": tk_pin}
    toks = list(iter_structured_tokens(rows, field_tokenizers, field_order=["module", "instance", "pin"]))
    values_by_row: dict[int, set[str]] = {0: set(), 1: set()}
    for idx, tok in toks:
        values_by_row[idx].add(tok.value)
    assert "fabric" in values_by_row[0]
    assert "cache" in values_by_row[0]
    assert "bank" in values_by_row[0]
    assert "data" in values_by_row[0]


def test_generate_candidates_with_custom_iter() -> None:
    include = ["ignored"]
    # Use only custom tokens; default path would have no influence
    custom_iter = [(0, Token("alpha", 0)), (0, Token("beta", 1))]
    result = generate_candidates(
        include,
        splitmethod="classchange",
        min_token_len=100,  # would eliminate default tokens if used
        per_word_substrings=8,
        max_multi_segments=3,
        token_iter=custom_iter,
    )
    patterns = {entry[0] for entry in result}
    # Expect candidates derived from custom tokens
    assert "*alpha*" in patterns
    assert "*beta*" in patterns
    assert "alpha" in patterns
    assert "beta" in patterns
    # Custom tokenizers concatenate without separator
    assert "alphabeta" in patterns


def test_propose_solution_with_structured_tokenizer_finds_bank() -> None:
    include_rows = [
        {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
        {"module": "fabric_cache", "instance": "cache1/bank1", "pin": "data_out"},
    ]
    exclude_rows = [
        {"module": "fabric_router", "instance": "rt0/debug", "pin": "trace"},
    ]

    def canon(row: dict[str, str]) -> str:
        return "/".join(filter(None, (row.get("module"), row.get("instance"), row.get("pin"))))

    include = [canon(r) for r in include_rows]
    exclude = [canon(r) for r in exclude_rows]

    tk_module = make_split_tokenizer("classchange", min_token_len=3)
    tk_instance = make_split_tokenizer("classchange", min_token_len=3)
    tk_pin = make_split_tokenizer("classchange", min_token_len=3)
    field_tokenizers = {"module": tk_module, "instance": tk_instance, "pin": tk_pin}
    token_iter = list(
        iter_structured_tokens(include_rows, field_tokenizers, field_order=["module", "instance", "pin"])  # noqa: E501
    )

    solution = propose_solution(include, exclude, token_iter, mode="APPROX")
    assert solution.patterns
    metrics = solution.metrics
    assert metrics["covered"] == len(include)
    assert metrics["fp"] == 0


def test_propose_solution_custom_iter_overrides_min_token_len() -> None:
    include = ["abc-xyz"]
    exclude: list[str] = []

    # With min_token_len very high, default tokenization would produce no tokens; supply our own
    def my_tok(s: str) -> list[Token]:
        parts = [p for p in re.split(r"[-_/]", s.lower()) if p]
        return [Token(p, i) for i, p in enumerate(parts)]

    token_iter = list(iter_custom_tokens(include, my_tok))
    solution = propose_solution(include, exclude, token_iter, mode="APPROX", min_token_len=100)
    assert solution.patterns
    texts = [a.text for a in solution.patterns]
    assert any("abc" in t or "xyz" in t for t in texts)
