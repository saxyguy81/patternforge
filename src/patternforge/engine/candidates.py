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
    max_multi_segments: int,
    token_iter: Iterable[tuple] | None = None,
    w_field: dict[str, float] | None = None,
    allowed_patterns: list[str] | set[str] | dict[str, list[str] | set[str]] | None = None,
) -> list[tuple[str, str, float, str | None]]:
    pool = CandidatePool()
    token_lists: dict[int, list[str]] = defaultdict(list)
    # Store mapping from (idx, field) to original string for position checking
    original_strings: dict[tuple[int, str | None], str] = {}

    # Detect if using custom tokenizer by checking if user provided token_iter
    using_custom_tokenizer = token_iter is not None

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
        # Store original string for position checking (only for non-custom tokenizers)
        # Custom tokenizers may provide semantic tokens not derived from the string
        if key not in original_strings and not using_custom_tokenizer:
            original_strings[key] = include[idx].lower()

    # Helper to check if a pattern kind is allowed for a given field
    def is_allowed(kind: str, field: str | None) -> bool:
        if allowed_patterns is None:
            return True
        if isinstance(allowed_patterns, dict):
            # Per-field filter
            if field and field in allowed_patterns:
                field_patterns = allowed_patterns[field]
                return kind in field_patterns
            # If field not in dict, allow all (default behavior for unspecified fields)
            return True
        # Global filter (list or set)
        return kind in allowed_patterns

    # Helper to apply field weight to score
    def apply_weight(score: float, field: str | None) -> float:
        if w_field and field:
            weight = w_field.get(field, 1.0)
            return score * weight
        return score

    # Generate global prefix patterns from longest common prefix across ALL include items
    # This generates patterns like "pd_sio/asio/asio_spis/*" instead of just "pd_sio*"
    if not using_custom_tokenizer and len(include) >= 2 and is_allowed("prefix", None):
        # Find longest common prefix
        include_lower = [s.lower() for s in include]
        common_prefix = include_lower[0]
        for s in include_lower[1:]:
            # Find common prefix between common_prefix and s
            i = 0
            while i < len(common_prefix) and i < len(s) and common_prefix[i] == s[i]:
                i += 1
            common_prefix = common_prefix[:i]

        # Extend to last delimiter boundary (non-alphanumeric character)
        if len(common_prefix) > 0:
            # Find the last delimiter position before divergence
            last_delim_pos = 0
            for i, ch in enumerate(common_prefix):
                if not ch.isalnum():
                    last_delim_pos = i + 1  # Include the delimiter

            if last_delim_pos > 0:
                # Create prefix pattern up to last delimiter
                prefix_pattern = common_prefix[:last_delim_pos] + "*"
                # High score to prefer this over per-item prefixes
                score = len(common_prefix[:last_delim_pos]) * 2.0
                pool.push(prefix_pattern, "prefix", apply_weight(float(score), None), None)

    for (idx_field, tokens) in token_lists.items():
        _, field = idx_field
        original_str = original_strings.get(idx_field, "")

        for token in tokens[:per_word_substrings]:
            if is_allowed("substring", field):
                pattern = f"*{token}*"
                score = len(token)
                pool.push(pattern, "substring", apply_weight(float(score), field), field)

        # Generate exact match from original string (for standard tokenizers)
        # or concatenated tokens (for custom tokenizers)
        if is_allowed("exact", field):
            if original_str:
                # Use actual original string to preserve separators
                pool.push(original_str, "exact", apply_weight(float(len(original_str)), field), field)
            else:
                # For custom tokenizers, concatenate tokens without separator
                joined = "".join(tokens)
                if joined:
                    pool.push(joined, "exact", apply_weight(float(len(joined)), field), field)

        for token in tokens:
            # For individual tokens, generate exact matches
            # This is needed for custom tokenizers where tokens are semantic units
            if is_allowed("exact", field):
                pool.push(token, "exact", apply_weight(float(len(token)), field), field)

        # Generate prefix patterns: token* (anchored start)
        # Only if token actually appears at the start of the original string
        if len(tokens) >= 1 and tokens[0] and is_allowed("prefix", field):
            first_token = tokens[0]
            if original_str.startswith(first_token):
                pattern = f"{first_token}*"
                # Score higher than substring to prefer anchored patterns
                # Fewer wildcards (1) vs substring (2) should be preferred
                score = len(first_token) * 1.5
                pool.push(pattern, "prefix", apply_weight(float(score), field), field)

        # Generate suffix patterns: *token (anchored end)
        # Only if token actually appears at the end of the original string
        if len(tokens) >= 1 and tokens[-1] and is_allowed("suffix", field):
            last_token = tokens[-1]
            if original_str.endswith(last_token):
                pattern = f"*{last_token}"
                # Score higher than substring to prefer anchored patterns
                score = len(last_token) * 1.5
                pool.push(pattern, "suffix", apply_weight(float(score), field), field)

        if len(tokens) >= 2 and is_allowed("multi", field):
            for start in range(len(tokens)):
                for end in range(start + 1, min(len(tokens), start + max_multi_segments) + 1):
                    segment = tokens[start:end]
                    pattern = "*" + "*".join(segment) + "*"
                    score = sum(len(t) for t in segment) - (end - start - 1)
                    pool.push(pattern, "multi", apply_weight(float(score), field), field)
    return sorted(pool.items(), key=lambda item: (-item[2], item[0]))
