"""Tokenization helpers."""
from __future__ import annotations

import re
from collections.abc import Iterator, Sequence

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


def tokenize(text: str, splitmethod: str = "classchange", min_token_len: int = 3) -> list[Token]:
    if splitmethod == "char":
        raw_tokens = [text]
    else:
        raw_tokens = _split_classchange(text)
    tokens: list[Token] = []
    for index, token in enumerate(raw_tokens):
        if len(token) >= min_token_len:
            tokens.append(Token(token.lower(), index))
    return tokens


def iter_tokens(
    items: Sequence[str], splitmethod: str, min_token_len: int
) -> Iterator[tuple[int, Token]]:
    for idx, item in enumerate(items):
        for token in tokenize(item, splitmethod=splitmethod, min_token_len=min_token_len):
            yield idx, token
