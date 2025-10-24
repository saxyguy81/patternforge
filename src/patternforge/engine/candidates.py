"""Candidate generation for pattern expressions."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from .tokens import iter_tokens


class CandidatePool:
    def __init__(self) -> None:
        self._scores: dict[str, float] = {}
        self._kinds: dict[str, str] = {}

    def push(self, pattern: str, kind: str, score: float) -> None:
        current = self._scores.get(pattern)
        if current is None or score > current:
            self._scores[pattern] = score
            self._kinds[pattern] = kind

    def items(self) -> Iterable[tuple[str, str, float]]:
        for pattern, score in self._scores.items():
            yield pattern, self._kinds[pattern], score


def generate_candidates(
    include: Sequence[str],
    splitmethod: str,
    min_token_len: int,
    per_word_substrings: int,
    per_word_multi: int,
    max_multi_segments: int,
) -> list[tuple[str, str, float]]:
    pool = CandidatePool()
    token_lists: dict[int, list[str]] = defaultdict(list)
    for idx, token in iter_tokens(include, splitmethod=splitmethod, min_token_len=min_token_len):
        token_lists[idx].append(token.value)
    for tokens in token_lists.values():
        for token in tokens[:per_word_substrings]:
            pattern = f"*{token}*"
            score = len(token)
            pool.push(pattern, "substring", float(score))
        joined = "/".join(tokens)
        if joined:
            pool.push(joined, "exact", float(len(joined)))
        for token in tokens:
            pool.push(token, "exact", float(len(token)))
        if len(tokens) >= 2:
            for start in range(len(tokens)):
                for end in range(start + 1, min(len(tokens), start + max_multi_segments) + 1):
                    segment = tokens[start:end]
                    pattern = "*" + "*".join(segment) + "*"
                    score = sum(len(t) for t in segment) - (end - start - 1)
                    pool.push(pattern, "multi", float(score))
    return sorted(pool.items(), key=lambda item: (-item[2], item[0]))
