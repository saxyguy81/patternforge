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
    """Weights for cost function optimization.

    All weights can be scalar (global) or dict (per-field).
    For per-field dicts, unspecified fields use implicit default of 1.0.

    w_field: Field preference multiplier (multi-field only, always dict)
        - Applied during candidate generation: pattern_score *= w_field.get(field, 1.0)
        - Higher values = prefer patterns on that field
        - Lower values = discourage patterns on that field
        - Example: {"module": 2.0, "pin": 2.0, "instance": 0.5}

    w_fp, w_fn: Solution quality weights
        - Applied during greedy selection in cost function
        - Can be scalar (global) or dict (per-field)
        - Example: w_fp={"module": 10.0, "pin": 1.0} means FPs on module hurt 10x more

    w_pattern, w_op, w_wc, w_len: Pattern complexity/specificity weights
        - Applied during greedy selection
        - w_pattern, w_op, w_wc are penalties (positive = worse)
        - w_len is a reward (negative = better, rewards longer/more specific patterns)
        - Can be scalar (global) or dict (per-field)
    """
    w_field: dict[str, float] | None = None
    w_fp: float | dict[str, float] = 1.0
    w_fn: float | dict[str, float] = 1.0
    w_pattern: float | dict[str, float] = 0.35
    w_op: float | dict[str, float] = 0.05
    w_wc: float | dict[str, float] = 0.005
    w_len: float | dict[str, float] = -0.01


@dataclass(frozen=True)
class OptimizeBudgets:
    """Hard constraints on solution search.

    For max_fp, max_fn, max_patterns:
    - int >= 1: absolute count (e.g., max_fp=5 means "at most 5 false positives")
    - 0 < float < 1: percentage of include rows (e.g., max_fp=0.01 means "at most 1% FP rate")
    - 0: zero (no FPs/FNs allowed)
    - None: no limit

    max_candidates: absolute count only (total candidates unknown beforehand)
    """
    max_candidates: int = 4000
    max_patterns: int | float | None = None
    max_fp: int | float | None = None
    max_fn: int | float | None = None


@dataclass(frozen=True)
class SolveOptions:
    """Unified options for both single-field and multi-field solvers.

    Per-field parameters (splitmethod, min_token_len):
    - Scalar value applies to all fields
    - Dict with per-field values: unspecified fields use hardcoded default

    allowed_patterns: Restrict generated pattern types
    - None (default): all pattern types allowed ("exact", "substring", "prefix", "suffix", "multi")
    - list/set of str: global filter (e.g., ["prefix", "suffix"] allows only anchored patterns)
    - dict[str, list/set]: per-field filter (e.g., {"module": ["prefix"], "pin": ["substring", "exact"]})
    """
    # Core settings
    mode: QualityMode = QualityMode.EXACT
    effort: str = "medium"  # "low" | "medium" | "high" | "exhaustive"

    # Tokenization (per-field capable)
    splitmethod: str | dict[str, str] = "classchange"
    min_token_len: int | dict[str, int] = 3

    # Candidate generation
    per_word_substrings: int = 16
    max_multi_segments: int = 3
    allowed_patterns: list[str] | set[str] | dict[str, list[str] | set[str]] | None = None

    # Optimization
    weights: OptimizeWeights = field(default_factory=OptimizeWeights)
    budgets: OptimizeBudgets = field(default_factory=OptimizeBudgets)

    # Single-field specific
    invert: InvertStrategy = InvertStrategy.AUTO
    allow_complex_expressions: bool = False

    def for_inversion(self) -> SolveOptions:
        return SolveOptions(
            mode=self.mode,
            effort=self.effort,
            splitmethod=self.splitmethod,
            min_token_len=self.min_token_len,
            per_word_substrings=self.per_word_substrings,
            max_multi_segments=self.max_multi_segments,
            allowed_patterns=self.allowed_patterns,
            invert=self.invert,
            weights=self.weights,
            budgets=self.budgets,
            allow_complex_expressions=self.allow_complex_expressions,
        )


@dataclass(frozen=True)
class Pattern:
    id: str
    text: str
    kind: str
    wildcards: int
    length: int
    field: str | None = None
    negated: bool = False
    matches: int | None = None  # Number of items this pattern matches
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
    patterns: list[Pattern]
    metrics: dict[str, int]
    witnesses: dict[str, list[str]]
    expressions: list[dict[str, object]]

    def to_json(self) -> dict[str, object]:
        return {
            "expr": self.expr,
            "raw_expr": self.raw_expr,
            "global_inverted": self.global_inverted,
            "term_method": self.term_method,
            "mode": self.mode,
            "options": self.options,
            "patterns": [pattern.__dict__ for pattern in self.patterns],
            "metrics": self.metrics,
            "witnesses": self.witnesses,
            "expressions": self.expressions,
        }
