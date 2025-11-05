"""Candidate generation for pattern expressions."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from .tokens import Token, iter_tokens


class CandidatePool:
    def __init__(self) -> None:
        self._scores: dict[tuple[str, str | None], float] = {}
        self._kinds: dict[tuple[str, str | None], str] = {}

    def push(self, pattern: str, kind: str, score: float, field: str | None) -> None:
        key = (pattern, field)
        current = self._scores.get(key)
        if current is None or score > current:
            self._scores[key] = score
            self._kinds[key] = kind

    def items(self) -> Iterable[tuple[str, str, float, str | None]]:
        for (pattern, field), score in self._scores.items():
            yield pattern, self._kinds[(pattern, field)], score, field


def generate_candidates(
    include: Sequence[str],
    splitmethod: str,
    min_token_len: int,
    per_word_substrings: int,
    per_word_multi: int,
    max_multi_segments: int,
    token_iter: Iterable[tuple] | None = None,
    field_weights: dict[str, float] | None = None,
) -> list[tuple[str, str, float, str | None]]:
    pool = CandidatePool()
    token_lists: dict[int, list[str]] = defaultdict(list)
    if token_iter is None:
        token_iter = iter_tokens(include, splitmethod=splitmethod, min_token_len=min_token_len)
    for entry in token_iter:
        if len(entry) == 2:
            idx, token = entry  # type: ignore[misc]
            field = None
        else:
            idx, token, field = entry  # type: ignore[misc]
        key = (idx, field)
        token_lists[key].append(token.value)

    # Helper to apply field weight to score
    def apply_weight(score: float, field: str | None) -> float:
        if field_weights and field:
            weight = field_weights.get(field, 1.0)
            return score * weight
        return score

    for (idx_field, tokens) in token_lists.items():
        _, field = idx_field
        for token in tokens[:per_word_substrings]:
            pattern = f"*{token}*"
            score = len(token)
            pool.push(pattern, "substring", apply_weight(float(score), field), field)
        joined = "/".join(tokens)
        if joined:
            pool.push(joined, "exact", apply_weight(float(len(joined)), field), field)
        for token in tokens:
            pool.push(token, "exact", apply_weight(float(len(token)), field), field)

        # Generate prefix patterns: token/* (anchored start)
        if len(tokens) >= 1 and tokens[0]:
            first_token = tokens[0]
            pattern = f"{first_token}/*"
            # Score higher than substring to prefer anchored patterns
            # Fewer wildcards (1) vs substring (2) should be preferred
            score = len(first_token) * 1.5
            pool.push(pattern, "prefix", apply_weight(float(score), field), field)

        # Generate suffix patterns: */token (anchored end)
        if len(tokens) >= 1 and tokens[-1]:
            last_token = tokens[-1]
            pattern = f"*/{last_token}"
            # Score higher than substring to prefer anchored patterns
            score = len(last_token) * 1.5
            pool.push(pattern, "suffix", apply_weight(float(score), field), field)

        if len(tokens) >= 2:
            for start in range(len(tokens)):
                for end in range(start + 1, min(len(tokens), start + max_multi_segments) + 1):
                    segment = tokens[start:end]
                    pattern = "*" + "*".join(segment) + "*"
                    score = sum(len(t) for t in segment) - (end - start - 1)
                    pool.push(pattern, "multi", apply_weight(float(score), field), field)
    return sorted(pool.items(), key=lambda item: (-item[2], item[0]))
