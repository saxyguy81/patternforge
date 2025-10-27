"""Data models shared across the patternforge engine."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class QualityMode(str, enum.Enum):
    EXACT = "EXACT"
    APPROX = "APPROX"


class InvertStrategy(str, enum.Enum):
    NEVER = "never"
    AUTO = "auto"
    ALWAYS = "always"


@dataclass(frozen=True)
class OptimizeWeights:
    w_fp: float = 1.0
    w_fn: float = 1.0
    w_atom: float = 0.05
    w_op: float = 0.02
    w_wc: float = 0.01
    w_len: float = 0.001


@dataclass(frozen=True)
class OptimizeBudgets:
    max_candidates: int = 4000
    max_atoms: int | None = None
    max_ops: int | None = None
    depth: int = 1
    max_multi_segments: int = 3
    max_fp: int | None = None
    max_fn: int | None = None


@dataclass(frozen=True)
class SolveOptions:
    mode: QualityMode = QualityMode.EXACT
    invert: InvertStrategy = InvertStrategy.AUTO
    weights: OptimizeWeights = field(default_factory=OptimizeWeights)
    budgets: OptimizeBudgets = field(default_factory=OptimizeBudgets)
    allow_not_on_atoms: bool = True
    allow_complex_terms: bool = False
    min_token_len: int = 3
    per_word_substrings: int = 16
    per_word_multi: int = 4
    per_word_cuts: int = 32
    max_multi_segments: int = 3
    splitmethod: str = "classchange"
    seed: int = 0

    def for_inversion(self) -> SolveOptions:
        return SolveOptions(
            mode=self.mode,
            invert=self.invert,
            weights=self.weights,
            budgets=self.budgets,
            allow_not_on_atoms=self.allow_not_on_atoms,
            min_token_len=self.min_token_len,
            per_word_substrings=self.per_word_substrings,
            per_word_multi=self.per_word_multi,
            per_word_cuts=self.per_word_cuts,
            max_multi_segments=self.max_multi_segments,
            splitmethod=self.splitmethod,
            seed=self.seed,
        )


@dataclass(frozen=True)
class Atom:
    id: str
    text: str
    kind: str
    wildcards: int
    length: int
    field: str | None = None
    negated: bool = False
    tp: int | None = None
    fp: int | None = None


@dataclass
class Candidate:
    text: str
    kind: str
    score: float
    include_bits: int
    exclude_bits: int
    wildcards: int
    length: int
    field: str | None = None


@dataclass
class Solution:
    expr: str
    raw_expr: str | None
    global_inverted: bool
    term_method: str
    mode: str
    options: dict[str, object]
    atoms: list[Atom]
    metrics: dict[str, int]
    witnesses: dict[str, list[str]]
    terms: list[dict[str, object]]

    def to_json(self) -> dict[str, object]:
        return {
            "expr": self.expr,
            "raw_expr": self.raw_expr,
            "global_inverted": self.global_inverted,
            "term_method": self.term_method,
            "mode": self.mode,
            "options": self.options,
            "atoms": [atom.__dict__ for atom in self.atoms],
            "metrics": self.metrics,
            "witnesses": self.witnesses,
            "terms": self.terms,
        }
