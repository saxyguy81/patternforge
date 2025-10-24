"""Pattern matching primitives used by the solver."""
from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache


def _split_pattern(pattern: str) -> list[str]:
    parts: list[str] = pattern.split("*")
    return parts


def ordered_match(text: str, tokens: Sequence[str], start_anchor: bool, end_anchor: bool) -> bool:
    pos = 0
    if start_anchor and tokens:
        if not text.startswith(tokens[0]):
            return False
        pos = len(tokens[0])
        tokens = tokens[1:]
    for index, token in enumerate(tokens):
        if index == len(tokens) - 1 and end_anchor:
            if token:
                end_pos = text.rfind(token)
                if end_pos == -1:
                    return False
                return end_pos + len(token) == len(text)
            return True
        found = text.find(token, pos)
        if found == -1:
            return False
        pos = found + len(token)
    if end_anchor and tokens:
        return text.endswith(tokens[-1])
    return True


def match_pattern(text: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    if "*" not in pattern:
        return text == pattern
    start_anchor = not pattern.startswith("*")
    end_anchor = not pattern.endswith("*")
    tokens = [chunk for chunk in pattern.split("*") if chunk]
    if not tokens:
        return True
    if start_anchor:
        first = tokens[0]
        if not text.startswith(first):
            return False
        start_index = len(first)
        tokens = tokens[1:]
    else:
        start_index = 0
    position = start_index
    for idx, token in enumerate(tokens):
        if idx == len(tokens) - 1 and end_anchor:
            return text.endswith(token) and text.find(token, position) != -1
        found = text.find(token, position)
        if found == -1:
            return False
        position = found + len(token)
    if end_anchor and tokens:
        return text.endswith(tokens[-1])
    return True


def match_all(texts: Sequence[str], pattern: str) -> list[bool]:
    return [match_pattern(text, pattern) for text in texts]


@lru_cache(maxsize=4096)
def wildcard_count(pattern: str) -> int:
    leading = 1 if pattern.startswith("*") else 0
    trailing = 1 if pattern.endswith("*") else 0
    return max(pattern.count("*") - leading - trailing, 0)
