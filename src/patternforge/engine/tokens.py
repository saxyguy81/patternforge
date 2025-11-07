"""Tokenization helpers."""
from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from typing import Callable

_SPLIT_RE = re.compile(r"([/_\.-])")


class Token:
    __slots__ = ("value", "index")

    def __init__(self, value: str, index: int) -> None:
        self.value = value
        self.index = index

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"Token({self.value!r}, {self.index})"


def _split_classchange(text: str) -> list[str]:
    chunks: list[str] = []
    buf = []
    prev = None
    for ch in text:
        category = "alpha" if ch.isalpha() else "digit" if ch.isdigit() else "other"
        if prev is None or category == prev:
            buf.append(ch)
        else:
            chunks.append("".join(buf))
            buf = [ch]
        prev = category
    if buf:
        chunks.append("".join(buf))
    return chunks


def _split_delimiters(text: str, min_token_len: int = 3) -> list[str]:
    """Split on delimiters and merge tokens that are too short."""
    raw_tokens = [t for t in _SPLIT_RE.split(text) if t and not _SPLIT_RE.match(t)]
    # Merge tokens that are too short with the next token
    merged_tokens = []
    i = 0
    while i < len(raw_tokens):
        token = raw_tokens[i]
        # If token is too short and there's a next token, merge them
        while len(token) < min_token_len and i + 1 < len(raw_tokens):
            i += 1
            token = token + "_" + raw_tokens[i]  # Use underscore as joiner
        merged_tokens.append(token)
        i += 1
    return merged_tokens


def tokenize(text: str, splitmethod: str = "classchange", min_token_len: int = 3) -> list[Token]:
    if splitmethod == "char":
        # Split into individual characters
        raw_tokens = list(text)
        effective_min_len = 1  # Characters are always length 1
    elif splitmethod == "delimiter":
        # Split on delimiters with merging for short tokens
        raw_tokens = _split_delimiters(text, min_token_len)
        effective_min_len = min_token_len
    else:  # classchange
        raw_tokens = _split_classchange(text)
        effective_min_len = min_token_len
    tokens: list[Token] = []
    for index, token in enumerate(raw_tokens):
        if len(token) >= effective_min_len:
            tokens.append(Token(token.lower(), index))
    return tokens


def iter_tokens(
    items: Sequence[str], splitmethod: str, min_token_len: int
) -> Iterator[tuple[int, Token]]:
    for idx, item in enumerate(items):
        for token in tokenize(item, splitmethod=splitmethod, min_token_len=min_token_len):
            yield idx, token


# Advanced/custom tokenization support
Tokenizer = Callable[[str], list[Token]]


def make_split_tokenizer(splitmethod: str = "classchange", min_token_len: int = 3) -> Tokenizer:
    def _fn(text: str) -> list[Token]:
        return tokenize(text, splitmethod=splitmethod, min_token_len=min_token_len)

    return _fn


def iter_custom_tokens(items: Sequence[str], tokenizer: Tokenizer) -> Iterator[tuple[int, Token]]:
    for idx, item in enumerate(items):
        for token in tokenizer(item):
            yield idx, token


def iter_structured_tokens(
    items: Sequence[dict[str, str]] | Sequence[Sequence[str]],
    field_tokenizers: dict[str, Tokenizer] | Sequence[Tokenizer],
    field_order: Sequence[str] | None = None,
) -> Iterator[tuple[int, Token]]:
    """
    Yield (row_index, Token) for structured rows, allowing per-field tokenizers.

    - items: list of dict rows or tuple/list rows.
    - field_tokenizers: either a mapping of field name -> tokenizer (for dict rows), or
      a sequence of tokenizers in positional order (for tuple/list rows).
    - field_order: for dict rows, optional explicit field order; otherwise keys() order is used.
    """
    for idx, row in enumerate(items):
        if isinstance(row, dict):
            names = list(field_order) if field_order else list(row.keys())
            offset = 0
            for name in names:
                tok = field_tokenizers.get(name) if isinstance(field_tokenizers, dict) else None
                if tok is None:
                    continue
                text = str(row.get(name, ""))
                toks = tok(text)
                for t in toks:
                    # adjust index by field offset to provide stable ordering
                    yield idx, Token(t.value, t.index + offset)
                offset += len(text)
        else:
            # positional sequence
            assert isinstance(field_tokenizers, Sequence)
            offset = 0
            for pos, tok in enumerate(field_tokenizers):
                if tok is None:
                    continue
                part = row[pos] if pos < len(row) else ""
                toks = tok(str(part))
                for t in toks:
                    yield idx, Token(t.value, t.index + offset)
                offset += len(str(part))


def iter_structured_tokens_with_fields(
    items: Sequence[dict[str, str]] | Sequence[Sequence[str]],
    field_tokenizers: dict[str, Tokenizer] | Sequence[Tokenizer],
    field_order: Sequence[str] | None = None,
) -> Iterator[tuple[int, Token, str]]:
    """
    Like iter_structured_tokens, but yields (row_index, Token, field_name) triples.
    For positional rows, field_name is f"f{index}".
    """
    for idx, row in enumerate(items):
        if isinstance(row, dict):
            names = list(field_order) if field_order else list(row.keys())
            for name in names:
                tok = field_tokenizers.get(name) if isinstance(field_tokenizers, dict) else None
                if tok is None:
                    continue
                text = str(row.get(name, ""))
                for t in tok(text):
                    yield idx, t, name
        else:
            # positional sequence
            assert isinstance(field_tokenizers, Sequence)
            for pos, tok in enumerate(field_tokenizers):
                if tok is None:
                    continue
                part = row[pos] if pos < len(row) else ""
                for t in tok(str(part)):
                    yield idx, t, f"f{pos}"
