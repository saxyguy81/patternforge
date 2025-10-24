"""Document-frequency utilities."""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

from .tokens import Token


def compute_idf(tokens: Iterable[Token], total_docs: int) -> dict[str, float]:
    counts = Counter(token.value for token in tokens)
    idf: dict[str, float] = {}
    for token, df in counts.items():
        idf[token] = math.log(1.0 + total_docs / (1 + df))
    return idf
