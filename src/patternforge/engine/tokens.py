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
    """Split on character class changes (alpha/digit/other)."""
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


def _merge_short_tokens(raw_tokens: list[str], min_token_len: int, joiner: str = "") -> list[tuple[str, int]]:
    """Merge alpha/digit tokens that are too short, preserving delimiters between them.

    Args:
        raw_tokens: List of token strings (including delimiters)
        min_token_len: Minimum length threshold
        joiner: String to join tokens (empty string means include actual delimiters from raw_tokens)

    Returns:
        List of (merged_token, original_index) tuples preserving original indices
    """
    if not raw_tokens:
        return []

    def is_delimiter_only(token: str) -> bool:
        """Check if token contains only delimiters (non-alphanumeric chars)."""
        return not any(c.isalnum() for c in token)

    # Skip single-character alphanumeric tokens entirely as they don't carry semantic meaning
    # But keep track of delimiters to preserve them during merging
    merged_tokens = []
    i = 0
    while i < len(raw_tokens):
        token = raw_tokens[i]
        original_idx = i

        # Skip delimiter-only and single-char alphanumeric tokens
        if is_delimiter_only(token) or len(token) == 1:
            i += 1
            continue

        # Token is meaningful (>1 char, has alphanumeric)
        # Try to merge if it's still too short
        while len(token) < min_token_len and i + 1 < len(raw_tokens):
            i += 1
            next_item = raw_tokens[i]

            # Include delimiters in the merge to preserve actual string structure
            if is_delimiter_only(next_item):
                token += next_item
                # Continue to get the next meaningful token after delimiter
                if i + 1 < len(raw_tokens):
                    i += 1
                    next_item = raw_tokens[i]
                    # Skip single-char tokens
                    if len(next_item) == 1 and not is_delimiter_only(next_item):
                        continue
                    token += next_item
            elif len(next_item) > 1:  # Only merge multi-char tokens
                if joiner:
                    token = token + joiner + next_item
                else:
                    token = token + next_item
            # Skip single-char tokens without merging

        # Only add tokens that meet minimum length
        if len(token) >= min_token_len:
            merged_tokens.append((token, original_idx))
        i += 1
    return merged_tokens


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
        tokens_with_indices = [(t, i) for i, t in enumerate(raw_tokens)]
    elif splitmethod == "delimiter":
        # Split on delimiters with merging for short tokens
        raw_tokens = _split_delimiters(text, min_token_len)
        effective_min_len = min_token_len
        tokens_with_indices = [(t, i) for i, t in enumerate(raw_tokens)]
    else:  # classchange
        # Split on character class changes, then merge short tokens
        raw_chunks = _split_classchange(text)
        tokens_with_indices = _merge_short_tokens(raw_chunks, min_token_len, joiner="")
        effective_min_len = min_token_len

    tokens: list[Token] = []
    for token, index in tokens_with_indices:
        # After merging, all tokens should meet min_token_len
        # But we still check in case of edge cases (e.g., very short input text)
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
