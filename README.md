# patternforge

Fast, deterministic glob-pattern discovery & human-readable explanations for hierarchical names.

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user guide with examples and best practices
- **[STRUCTURED_SOLVER_GUIDE.md](STRUCTURED_SOLVER_GUIDE.md)** - Deep dive into multi-field pattern matching
- **[examples/](examples/)** - Runnable examples (quick start, patterns, performance tests)

## Quick Start

CLI in 60 seconds:

```bash
# 1) Create small include/exclude sets
cat > include.txt <<'IN'
alpha/module1/mem/i0
alpha/module2/io/i1
beta/cache/bank0
IN

cat > exclude.txt <<'EX'
gamma/module1/mem/i0
beta/router/debug
EX

# 2) Propose best patterns and save JSON
PYTHONPATH=src python -m patternforge.cli propose \
  --include include.txt --exclude exclude.txt \
  --format json --emit-witnesses --out quick_solution.json

# 3) Inspect the expression, raw patterns, and metrics
jq '.expr, .raw_expr, .metrics' quick_solution.json

# 4) Human-readable explanation
PYTHONPATH=src python -m patternforge.cli explain \
  --solution quick_solution.json --format text

# 5) (Optional) Evaluate expression against atoms to verify
jq '{atoms: .atoms}' quick_solution.json > atoms.json
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include include.txt --exclude exclude.txt \
  --expr "$(jq -r .expr quick_solution.json)" --atoms atoms.json --format text
```

Example outputs for the dataset above (YAML):

```yaml
expr: "P1 | P2"
raw_expr: "*alpha* | *cache*"
metrics: {covered: 3, total_positive: 3, fp: 0, fn: 0}
explain:
  atoms:
    - {id: P1, text: "*alpha*", kind: substring}
    - {id: P2, text: "*cache*", kind: substring}
  tp_examples: [alpha/module1/mem/i0, alpha/module2/io/i1, beta/cache/bank0]
evaluate: {covered: 3, total_positive: 3, fp: 0, fn: 0}
```

Python API quick start:

```python
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution
from patternforge.engine.explain import explain_text

include = [
    "alpha/module1/mem/i0",
    "alpha/module2/io/i1",
    "beta/cache/bank0",
]
exclude = [
    "gamma/module1/mem/i0",
    "beta/router/debug",
]

solution = propose_solution(include, exclude, SolveOptions())
print(solution["expr"], solution.get("raw_expr"))
print(explain_text(solution, include, exclude))
```

Example solution (YAML):

```yaml
expr: "P1 | P2"
raw_expr: "*alpha* | *cache*"
term_method: additive
metrics: {covered: 3, total_positive: 3, fp: 0, fn: 0}
atoms:
  - {id: P1, text: "*alpha*", kind: substring, wildcards: 2, length: 5, tp: 2, fp: 0}
  - {id: P2, text: "*cache*", kind: substring, wildcards: 2, length: 5, tp: 1, fp: 0}
witnesses:
  tp_examples: [alpha/module1/mem/i0, alpha/module2/io/i1, beta/cache/bank0]
  fp_examples: []
  fn_examples: []
terms:
  - {expr: P1, raw_expr: "*alpha*", tp: 2, fp: 0, fn: 1, incremental_tp: 2, incremental_fp: 0, length: 5}
  - {expr: P2, raw_expr: "*cache*", tp: 1, fp: 0, fn: 2, incremental_tp: 1, incremental_fp: 0, length: 5}
```

For structured inputs (rows with fields like module/instance/pin), see the “Structured per‑field matching example” below.

### Expression modes and switches

- Default mode (single-pattern terms with OR):
  - The solver selects a minimal set of single wildcard patterns and ORs them: `P1 | P2 | …`.
  - To force full coverage of all include items, add `--max-fn 0` (or set `options.budgets.max_fn=0`).
  - To cap the number of patterns (“terms”), set `--max-atoms N`.

```bash
PYTHONPATH=src python -m patternforge.cli propose \
  --include include.txt --exclude exclude.txt \
  --max-fn 0 --max-atoms 4 \
  --format json --out - | jq '.expr, .metrics'
```

- Inverted OR (everything minus patterns):
  - Use `--invert always` to return the global complement of the OR’d terms. This corresponds to: “Everything MINUS P1 MINUS P2 …”.

```bash
PYTHONPATH=src python -m patternforge.cli propose \
  --include include.txt --exclude exclude.txt \
  --invert always --format json --out - | jq '.global_inverted, .expr, .metrics'
```

- Complex intersections (AND/NOT):
  - The evaluator supports AND/OR/NOT and parentheses for expressions over atoms (`P1 & P2`, `!P3`, `(P1 & !P2) | P4`).
  - Today, `propose` selects an OR of atoms; use `evaluate` to verify complex expressions you design from the atom list.

```bash
# 1) Propose to get atoms
PYTHONPATH=src python -m patternforge.cli propose \
  --include include.txt --exclude exclude.txt --out sol.json --format json
jq '{atoms: .atoms}' sol.json > atoms.json

# 2) Try a complex expression against the atom set
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include include.txt --exclude exclude.txt \
  --expr '(P1 & P2) | (!P3 & P4)' --atoms atoms.json --format text
```

## Practical use cases

> The examples below assume either `pip install -e .` has been run or `PYTHONPATH=src` is set when invoking `python`.

### Regression triage
For nightly regression dashboards, treat failing runs as `--include` items and passing runs as
`--exclude`. Pattern discovery surfaces the fragments that explain the failures, and you can retain a
JSON solution for dashboards.

```bash
cat <<'FAIL' > regress_failed.txt
regress/nightly/ipA/test_fifo/rand_smoke/fail
regress/nightly/ipA/test_fifo/max_burst/fail
regress/nightly/ipA/test_dma/rand_smoke/fail
regress/nightly/ipB/test_cache/assoc16/fail
regress/nightly/ipB/test_cache/assoc32/fail
regress/nightly/ipB/test_stream/throughput/fail
regress/nightly/ipC/test_uart/loopback/fail
regress/nightly/ipC/test_uart/framing/fail
regress/nightly/ipD/test_pcie/gen4_link/fail
regress/nightly/ipD/test_pcie/gen5_link/fail
regress/nightly/ipD/test_pcie/replay/fail
regress/nightly/ipE/test_crypto/aes_sweep/fail
FAIL

cat <<'PASS' > regress_passed.txt
regress/nightly/ipA/test_fifo/rand_smoke/pass
regress/nightly/ipA/test_fifo/max_burst/pass
regress/nightly/ipA/test_dma/rand_smoke/pass
regress/nightly/ipA/test_dma/stress/pass
regress/nightly/ipB/test_cache/assoc16/pass
regress/nightly/ipB/test_cache/assoc32/pass
regress/nightly/ipB/test_stream/throughput/pass
regress/nightly/ipC/test_uart/loopback/pass
regress/nightly/ipC/test_uart/framing/pass
regress/nightly/ipC/test_uart/parity/pass
regress/nightly/ipC/test_spi/loopback/pass
regress/nightly/ipD/test_pcie/gen4_link/pass
regress/nightly/ipD/test_pcie/gen5_link/pass
regress/nightly/ipD/test_pcie/replay/pass
regress/nightly/ipD/test_pcie/error_inject/pass
regress/nightly/ipE/test_crypto/aes_sweep/pass
regress/nightly/ipE/test_crypto/hash_mix/pass
PASS

PYTHONPATH=src python -m patternforge.cli propose   --include regress_failed.txt   --exclude regress_passed.txt   --mode APPROX   --invert auto   --format json   --emit-witnesses   --out regress_solution.json

jq '.expr, .metrics, .atoms' regress_solution.json

PYTHONPATH=src python -m patternforge.cli explain   --solution regress_solution.json   --format text
```

The solver returns a single atom `*fail*` that cleanly separates failing jobs, and the explanation
confirms 12/12 coverage with no false positives.

Programmatic access follows the same pattern:

```python
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution
from patternforge.engine.explain import explain_dict

with open("regress_failed.txt", encoding="utf-8") as fh:
    include = [line.strip() for line in fh if line.strip()]
with open("regress_passed.txt", encoding="utf-8") as fh:
    exclude = [line.strip() for line in fh if line.strip()]

solution = propose_solution(include, exclude, SolveOptions())
summary = explain_dict(solution, include, exclude)
print(summary["expr"], summary["metrics"])
```

This example produces a one-atom solution and full coverage; see JSON/YAML above for the structure.

### Connection summaries from CSV data
When inspecting how sub-block pins connect to top-level signals, you can point the CLI at CSV files
with `module`, `instance`, and `pin` columns—even if the instance itself contains `/`—and the reader
will compose hierarchical paths automatically.

```bash
cat <<'CSV' > fabric_cache_include.csv
module,instance,pin
fabric_cache,cache0/bank0,data_in
fabric_cache,cache0/bank0,data_out
fabric_cache,cache0/bank1,data_in
fabric_cache,cache0/bank1,data_out
fabric_cache,cache1/bank0,data_in
fabric_cache,cache1/bank0,data_out
fabric_cache,cache1/bank1,data_in
fabric_cache,cache1/bank1,data_out
CSV

cat <<'CSV' > fabric_cache_exclude.csv
module,instance,pin
fabric_cache,cache_dbg/trace,data_tap
fabric_cache,cache_dbg/trace,tag
fabric_cache,cache_diag/inst0,metrics
fabric_cache,cache_diag/inst1,metrics
fabric_router,rt0/core0,req
fabric_router,rt0/core0,grant
fabric_router,rt0/core1,req
fabric_router,rt0/core1,grant
fabric_router,rt0/debug,trace
CSV

PYTHONPATH=src python -m patternforge.cli propose   --include fabric_cache_include.csv   --exclude fabric_cache_exclude.csv   --mode APPROX   --format json   --emit-witnesses   --out fabric_cache_solution.json
```

The grouped CSV records collapse to the concise expression `*bank*`, capturing all cache-bank pins
while excluding debug and router traffic.

Python scripts can perform the same join explicitly if you need to enrich the rows before solving:

```python
import csv
from patternforge.engine.models import QualityMode, SolveOptions
from patternforge.engine.solver import propose_solution

def load(path: str) -> list[str]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return ["/".join(filter(None, (row["module"], row["instance"], row["pin"]))) for row in reader]

options = SolveOptions(mode=QualityMode.APPROX)
solution = propose_solution(load("fabric_cache_include.csv"), load("fabric_cache_exclude.csv"), options)
print(solution["expr"], solution["atoms"][0]["text"])  # e.g., P1 *bank*
```

This confirms the CLI and API stay in sync.

## Performance characterization
The CLI remains responsive across common dataset sizes. Measuring synthetic workloads on this machine
shows near-linear scaling while keeping runtimes well under a second:

| include size | elapsed (s) | atoms | FP | FN |
|--------------|-------------|-------|----|----|
| 50           | 0.140       | 1     | 17 | 0  |
| 100          | 0.150       | 1     | 34 | 0  |
| 250          | 0.150       | 1     | 84 | 0  |
| 500          | 0.200       | 1     | 167 | 0 |
| 1000         | 0.200       | 1     | 334 | 0 |

These timings come from invoking `patternforge propose` with randomly generated hierarchical paths and recording
process CPU time (see `python - <<'PY' ...` in the repository history for the exact script).

## Pattern matching examples

This section demonstrates how `*` wildcards work and how to combine multiple patterns. A few rules of thumb:

- `*` matches any substring (including `/`); everything else is literal.
- If the pattern does not start with `*`, it is anchored at the beginning.
- If the pattern does not end with `*`, it is anchored at the end.
- Multiple `*` enforce token order but not adjacency (e.g., `a*b*c` means “a … b … c” in order).
- Use boolean `|` (OR), `&` (AND), `!` (NOT), and parentheses over named atoms `P1`, `P2`, …

We will use a small hierarchical dataset (26 total items):

```bash
cat <<'DATA' > rectangles.txt
video/display/pixel0
video/display/pixel1
video/display/scaler0
video/shader/vector0
video/shader/vector1
video/shader/vector_debug
video/memory/cache0
video/memory/cache1
video/memory/cache2
video/io/ingress/decoder0
video/io/egress/hdmi0
video/io/egress/hdmi1
compute/dsp/vector0
compute/dsp/vector1
compute/dsp/vector2
compute/dsp/vector3
compute/control/sequencer
compute/control/debug
compute/memory/cache0
compute/memory/cache1
compute/memory/cache2
compute/memory/cache3
control/clockmgr/main
control/clockmgr/backup
control/resetmgr/main
control/resetmgr/debug
DATA
```

Create a small atoms file with a variety of patterns:

```bash
cat > atoms_rect.json <<'JSON'
[
  {"id": "P1",  "text": "video*"},
  {"id": "P2",  "text": "*cache*"},
  {"id": "P3",  "text": "video/*/pixel*"},
  {"id": "P4",  "text": "*io/*/hdmi*"},
  {"id": "P5",  "text": "*dsp*"},
  {"id": "P6",  "text": "*vector*"},
  {"id": "P7",  "text": "*debug*"},
  {"id": "P8",  "text": "*vector"},
  {"id": "P9",  "text": "compute/*/cache*"},
  {"id": "P10", "text": "video/*/vector*"}
]
JSON
```

Now evaluate a few expressions and note the printed summaries:

```bash
# Prefix-only at start (anchored): matches the 12 video/* items
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P1' --format text

# Middle-substring match: any item with “cache” anywhere
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P2' --format text

# Multiple wildcards with ordering: “video/ … /pixel*”
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P3' --format text

# Multiple wildcards spanning separators: “*/io/*/hdmi*”
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P4' --format text

# Boolean AND intersection: video items that also contain “vector”
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P1 & P6' --format text

# Union of disjoint sources then intersect: (dsp OR video/*/vector*) AND *vector*
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr '(P5 | P10) & P6' --format text

# Filter out debug using NOT
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr '(P1 & P6) & !P7' --format text

# End-anchored only: “*vector” matches strings that end exactly with “vector”
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P8' --format text

# Constrain cache hits to compute subtree only
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P9' --format text

# Two-segment middle match within video
PYTHONPATH=src python -m patternforge.cli evaluate \
  --include rectangles.txt --atoms atoms_rect.json \
  --expr 'P10' --format text
```

Example outputs you should see (YAML):

```yaml
examples:
  - {expr: P1, metrics: {covered: 12, total_positive: 26, fp: 0, fn: 14}}
  - {expr: P2, metrics: {covered: 7, total_positive: 26, fp: 0, fn: 19}}
  - {expr: P3, metrics: {covered: 2, total_positive: 26, fp: 0, fn: 24}}
  - {expr: P4, metrics: {covered: 2, total_positive: 26, fp: 0, fn: 24}}
  - {expr: "P1 & P6", metrics: {covered: 3, total_positive: 26, fp: 0, fn: 23}}
  - {expr: "(P5 | P10) & P6", metrics: {covered: 7, total_positive: 26, fp: 0, fn: 19}}
  - {expr: "(P1 & P6) & !P7", metrics: {covered: 2, total_positive: 26, fp: 0, fn: 24}}
  - {expr: P8, metrics: {covered: 0, total_positive: 26, fp: 0, fn: 26}}
  - {expr: P9, metrics: {covered: 4, total_positive: 26, fp: 0, fn: 22}}
  - {expr: P10, metrics: {covered: 3, total_positive: 26, fp: 0, fn: 23}}
```

How it works (high level):
- Tokenize include items (by default using character‑class changes, or your custom tokenizer).
- Generate candidates from tokens: exact tokens, substrings `*tok*`, multi‑wildcards `*tok1*tok2*`, and joined segments.
- Rank candidates by score; build boolean expression greedily to minimize a weighted cost of FP/FN/complexity.
- Optionally invert the selection if global inversion yields a lower cost.
- Return the symbolic expression (P1 | P2 …), the raw patterns, per‑atom TP/FP counts, and witnesses.

Peek at candidates for a dataset:

```bash
PYTHONPATH=src python -m patternforge.cli dump-candidates \
  --include rectangles.txt --top 8 --format text
```

Example candidate dump (YAML):

```yaml
- {pattern: "*vector*", kind: substring, score: 6.0}
- {pattern: video, kind: exact, score: 5.0}
- {pattern: "*cache*", kind: substring, score: 5.0}
- {pattern: compute, kind: exact, score: 7.0}
- {pattern: "*io*hdmi*", kind: multi, score: 7.0}
```

### Boolean combos with excludes (FP/TP)

You can also pass `--exclude` to measure false positives. Reuse the regression data from above and try these atoms:

```bash
cat > atoms_regress.json <<'JSON'
[
  {"id": "Q1", "text": "*fail*"},
  {"id": "Q2", "text": "*cache*"},
  {"id": "Q3", "text": "*gen*"}
]
JSON

PYTHONPATH=src python -m patternforge.cli evaluate \
  --include regress_failed.txt --exclude regress_passed.txt \
  --atoms atoms_regress.json --expr 'Q1' --format text

PYTHONPATH=src python -m patternforge.cli evaluate \
  --include regress_failed.txt --exclude regress_passed.txt \
  --atoms atoms_regress.json --expr 'Q2' --format text

PYTHONPATH=src python -m patternforge.cli evaluate \
  --include regress_failed.txt --exclude regress_passed.txt \
  --atoms atoms_regress.json --expr 'Q2 & Q1' --format text

PYTHONPATH=src python -m patternforge.cli evaluate \
  --include regress_failed.txt --exclude regress_passed.txt \
  --atoms atoms_regress.json --expr 'Q3' --format text
```

Typical outputs for the dataset in this README (YAML):

```yaml
results:
  - {expr: Q1, metrics: {covered: 12, total_positive: 12, fp: 0, fn: 0}}
  - {expr: Q2, metrics: {covered: 2, total_positive: 12, fp: 2, fn: 10}}
  - {expr: "Q2 & Q1", metrics: {covered: 2, total_positive: 12, fp: 0, fn: 10}}
  - {expr: Q3, metrics: {covered: 2, total_positive: 12, fp: 2, fn: 10}}
```

## Rectangles (appendix)

The rectangle planner is a lightweight top-level grouping helper, not the main solver. It counts items by the first path segment and proposes up to `rect_budget` rectangles. If you need middle/multi-wildcards or boolean combinations, use the solver.

- Return shape
  - `rectangles`: list of entries with keys:
    - `prefix`: the top-level path segment used for grouping
    - `count`: number of items under that prefix
    - `score`: simple score = max(count - rect_penalty, 0) * exception_weight
    - `pattern`: convenience wildcard pattern for the rectangle (e.g., `video*`)
    - `kind`: always `prefix` for now
  - `total`: total items in the include set

Example:

```bash
cat <<'DATA' > rectangles.txt
video/display/pixel0
video/display/pixel1
video/shader/vector0
compute/dsp/vector0
compute/memory/cache0
control/clockmgr/main
DATA

PYTHONPATH=src python -m patternforge.cli plan-rectangles \
  --include rectangles.txt --rect-budget 2 --format json
```

Programmatic:

```python
from patternforge.engine.rectangles import plan_rectangles

items = [
    "video/display/pixel0",
    "video/shader/vector0",
    "compute/dsp/vector0",
    "control/clockmgr/main",
]
plan = plan_rectangles(items, rect_budget=2, rect_penalty=1.0, exception_weight=1.0)
print(plan["rectangles"][0]["prefix"], plan["rectangles"][0]["pattern"])  # e.g., video video*
```

Sample YAML output for the CLI example above:

```yaml
rectangles:
  - prefix: video
    count: 3
    score: 2.0
    pattern: "video*"
    kind: prefix
  - prefix: compute
    count: 2
    score: 1.0
    pattern: "compute*"
    kind: prefix
total: 6
```

## Python API

This library is importable and script-friendly. The core flow is:

- Prepare include and exclude lists of hierarchical strings.
- Call `propose_solution(include, exclude, SolveOptions(...))`.
- Inspect the returned dict (`expr`, `atoms`, `metrics`), or render via `explain_*` helpers.

Minimal example:

```python
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution
from patternforge.engine.explain import explain_dict, explain_text

include = [
    "regress/nightly/ipA/test_fifo/rand_smoke/fail",
    "regress/nightly/ipA/test_fifo/max_burst/fail",
    "regress/nightly/ipB/test_cache/assoc16/fail",
]
exclude = [
    "regress/nightly/ipA/test_fifo/rand_smoke/pass",
    "regress/nightly/ipB/test_cache/assoc16/pass",
]

options = SolveOptions()  # defaults work well; see knobs below
solution = propose_solution(include, exclude, options)

print(solution["expr"])              # e.g., "P1"
print(solution["atoms"])             # list of {id,text,kind,wildcards,...}
print(solution["metrics"])           # {covered,total_positive,fp,fn,...}

print(explain_text(solution, include, exclude))
summary = explain_dict(solution, include, exclude)
print(summary["expr"], summary["metrics"])  # recomputed vs original, with per-atom tp/fp
```

Human-readable output shows both the symbolic and raw expression:

```text
EXPR: P1 | P2
RAW:  *cache* | *bank*
```

Evaluate an expression against atoms (useful to test what-ifs):

```python
from patternforge.engine.solver import evaluate_expr

atoms = {atom["id"]: atom["text"] for atom in solution["atoms"]}
metrics = evaluate_expr(solution["expr"], atoms, include, exclude)
print(metrics)  # {"covered": ..., "fp": ..., "fn": ...}
```

Persist/load solutions (e.g., for dashboards):

```python
from patternforge import io

io.save_solution(solution, "solve.json")
loaded = io.load_solution("solve.json")
```

### Optimization knobs (SolveOptions)

**For comprehensive documentation, see [USER_GUIDE.md](USER_GUIDE.md)**

- Quality
  - `mode`: `EXACT` explores deeper combinations and favors precise atoms; `APPROX` is faster, with a shallower search.
  - `effort`: `"low"`, `"medium"` (default), `"high"`, or `"exhaustive"` - controls quality vs speed trade-off
  - `invert`: `auto` evaluates both non-inverted and inverted coverage and chooses lower cost; `never` forces non-inverted; `always` returns the inverted selection.

- Budgets (`options.budgets`) control the search frontier and expression size
  - `max_candidates`: upper bound on ranked candidate atoms considered (default 4000)
  - `max_atoms`: cap on atoms in the final expression (int or 0<float<1 for percentage)
  - `max_multi_segments`: max segments in multi-wildcard atoms like `*a*b*c*` (limits combinatorics)
  - `max_fp`, `max_fn`: optional hard stops (int or 0<float<1 for percentage) that prune worse-than-threshold solutions early

- Weights (`options.weights`) tune the cost function used by the greedy selector
  - `w_fp`, `w_fn`: penalty for false positives/negatives (dominant factors)
  - `w_atom`, `w_op`: penalize long expressions with many atoms/boolean ops
  - `w_wc`: penalize many wildcards (encourages more specific tokens)
  - `w_len`: penalize longer non-`*` characters (nudges toward concise patterns)
  - `w_field`: field preference for structured data (dict mapping field names to weights)
  - **NEW:** All weights can be scalar OR dict for per-field customization

- Tokenization / candidate generation
  - `splitmethod`: `classchange` chunks by character class; `char` uses specific separators
  - `min_token_len`: discard tokens shorter than this
  - `per_word_substrings`: top N per-token substrings to consider as `*tok*` atoms
  - `max_multi_segments`: limit segments in multi-wildcard atoms

**Example:**
```python
from patternforge.engine.models import SolveOptions, OptimizeWeights, OptimizeBudgets

options = SolveOptions(
    mode=QualityMode.EXACT,
    effort="high",
    weights=OptimizeWeights(
        w_fp=2.0,           # Penalize false positives heavily
        w_field={"pin": 3.0, "instance": 0.5}  # Prefer pin patterns (structured)
    ),
    budgets=OptimizeBudgets(
        max_atoms=8,        # At most 8 atoms
        max_fp=0.01,        # Allow 1% false positives
    )
)
```

### Advanced: custom tokenizers (per-field)

You can provide your own tokenization logic (globally or per-field for structured rows) without changing matching semantics. Tokenization only affects candidate generation; matching still uses wildcard patterns over your include/exclude strings.

1) Build your canonical strings for matching (e.g., `module/instance/pin`).
2) Build a token iterator using per-field tokenizers.
3) Pass `token_iter` into `propose_solution(...)`.

```python
from patternforge.engine.models import SolveOptions
from patternforge.engine.solver import propose_solution
from patternforge.engine.tokens import (
    make_split_tokenizer,
    iter_structured_tokens,
    iter_structured_tokens_with_fields,
)

# Structured rows (e.g., read from CSV)
include_rows = [
    {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
    {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_out"},
]
exclude_rows = [
    {"module": "fabric_router", "instance": "rt0/debug", "pin": "trace"},
]

# 1) Canonical strings for matching
def canon(row: dict[str, str]) -> str:
    return "/".join(filter(None, (row.get("module"), row.get("instance"), row.get("pin"))))

include = [canon(r) for r in include_rows]
exclude = [canon(r) for r in exclude_rows]

# 2) Per-field tokenizers
tk_module = make_split_tokenizer("classchange", min_token_len=3)
tk_instance = make_split_tokenizer("classchange", min_token_len=3)
tk_pin = make_split_tokenizer("classchange", min_token_len=3)

field_tokenizers = {"module": tk_module, "instance": tk_instance, "pin": tk_pin}
token_iter = list(iter_structured_tokens_with_fields(include_rows, field_tokenizers, field_order=["module", "instance", "pin"]))

# 3) Propose with custom tokens
options = SolveOptions(mode="APPROX")
solution = propose_solution(include, exclude, options, token_iter=token_iter)
print(solution["expr"], [a["text"] for a in solution["atoms"]])
```

Custom global tokenizer for plain strings:

```python
import re
from patternforge.engine.tokens import Token

def my_tokenizer(s: str):
    # split on '-', '_', '/' and keep 3+ length parts
    parts = [p for p in re.split(r"[-_/]", s.lower()) if len(p) >= 3]
    return [Token(p, i) for i, p in enumerate(parts)]

token_iter = [(i, t) for i, s in enumerate(include) for t in my_tokenizer(s)]
solution = propose_solution(include, exclude, SolveOptions(), token_iter=token_iter)
```

Notes
- Matching always runs over your `include`/`exclude` strings with wildcard rules described earlier.
- Custom tokenizers only influence how candidate patterns are generated and selected.
- If you already have separate per-field tokenizers, prefer `iter_structured_tokens` to keep indices stable.

### What solutions look like for multi-field inputs

- The solver matches against your canonical strings (e.g., `module/instance/pin`) by default.
- True per-field matching is available via `propose_solution_structured(...)` which creates atoms that carry a `field` attribute and are matched only against that field’s value when computing coverage.
- Use `iter_structured_tokens_with_fields(...)` to generate per-field tokens; pass them as `token_iter` into `propose_solution_structured`.
- For additional attribution or display, `explain_by_field(solution, rows, field_order=[...])` groups atoms by likely field influence.

### Structured per-field matching example

```python
from patternforge.engine.models import QualityMode, SolveOptions
from patternforge.engine.solver import propose_solution_structured
from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields

include_rows = [
    {"module": "fabric_cache", "instance": "cache0/bank0", "pin": "data_in"},
    {"module": "fabric_cache", "instance": "cache1/bank1", "pin": "data_out"},
]
exclude_rows = [
    {"module": "fabric_router", "instance": "rt0/debug", "pin": "trace"},
]

tk = make_split_tokenizer("classchange", min_token_len=3)
field_tokenizers = {"module": tk, "instance": tk, "pin": tk}
token_iter = list(iter_structured_tokens_with_fields(include_rows, field_tokenizers, field_order=["module", "instance", "pin"]))

sol = propose_solution_structured(include_rows, exclude_rows, SolveOptions(mode=QualityMode.APPROX), token_iter=token_iter)
print(sol["expr"])                 # e.g., "P1"
print(sol["atoms"])                # atoms include {"field": "instance"} or similar
print(sol["metrics"])              # coverage metrics over rows
```

Example structured output (YAML):

```yaml
expr: "P1"
raw_expr: "*data*"
term_method: additive
metrics: {covered: 2, total_positive: 2, fp: 0, fn: 0}
atoms:
  - {id: P1, text: "*data*", kind: substring, wildcards: 2, length: 4, field: pin, tp: 2, fp: 0}
terms:
  - {expr: P1, raw_expr: "*data*", field: pin, tp: 2, fp: 0, fn: 0, incremental_tp: 2, incremental_fp: 0, length: 4}
```

Notes
- Atoms in structured mode carry a `field` key; matching and coverage use only that field’s value.
- If an atom’s `field` is not explicitly set, the solver attributes it to the most likely field based on substring hits.

### Structured JSONL (module/instance/pin)

Use JSONL inputs to model rows with multiple fields. Values may contain any characters; discovered field patterns can include zero or more wildcards (for example, `*cache*bank*`). Omitted fields are treated as wildcard.

Create JSONL inputs:

```bash
cat > include_rows.jsonl <<'IN'
{"module":"fabric_cache","instance":"cache0/bank0","pin":"data_in"}
{"module":"fabric_cache","instance":"cache0/bank1","pin":"data_out"}
{"module":"fabric_cache","instance":"cache1/bank2","pin":"data_in"}
{"module":"fabric_cache","instance":"cache1/bank3","pin":"data_out"}
IN

cat > exclude_rows.jsonl <<'EX'
{"module":"fabric_router","instance":"rt0/core0","pin":"req"}
{"module":"fabric_router","instance":"rt0/core1","pin":"grant"}
{"module":"fabric_cache","instance":"cache_dbg/trace","pin":"tag"}
EX
```

Run a short Python snippet to produce structured terms (fields ANDed within each term, ORed across terms):

```bash
PYTHONPATH=src python - <<'PY'
import json
from patternforge.engine.models import SolveOptions, QualityMode
from patternforge.engine.solver import propose_solution_structured
from patternforge.engine.tokens import make_split_tokenizer, iter_structured_tokens_with_fields

def load_jsonl(path):
    rows = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

include_rows = load_jsonl('include_rows.jsonl')
exclude_rows = load_jsonl('exclude_rows.jsonl')

tk = make_split_tokenizer('classchange', min_token_len=3)
fts = {'module': tk, 'instance': tk, 'pin': tk}
tok_iter = list(iter_structured_tokens_with_fields(include_rows, fts, field_order=['module','instance','pin']))
opts = SolveOptions(mode=QualityMode.EXACT, allow_complex_terms=True)
sol = propose_solution_structured(include_rows, exclude_rows, opts, token_iter=tok_iter)

# Emit only structured terms (fields + metrics)
terms = [
  {
    'fields': t.get('fields', {}),
    'tp': t.get('tp', 0), 'fp': t.get('fp', 0), 'fn': t.get('fn', 0),
    'incremental_tp': t.get('incremental_tp', 0), 'incremental_fp': t.get('incremental_fp', 0),
    'length': t.get('length', 0)
  }
  for t in sol.get('terms', [])
]
print(json.dumps({'expr': sol['expr'], 'terms': terms}, indent=2))
PY
```

Example structured terms (YAML):

```yaml
expr: "(*fabric*) & (*data*) | (*cache*) & (*data*) | (*data*)"
terms:
  - {fields: {module: "*fabric*", pin: "*data*"}, tp: 4, fp: 0, fn: 0, incremental_tp: 0, incremental_fp: 0, length: 10}
  - {fields: {module: "*cache*", pin: "*data*"}, tp: 4, fp: 0, fn: 0, incremental_tp: 0, incremental_fp: 0, length: 9}
  - {fields: {pin: "*data*"}, tp: 4, fp: 0, fn: 0, incremental_tp: 4, incremental_fp: 0, length: 4}
```

CLI tip
- The `propose` command supports `--structured-terms` to emit only structured terms when outputting JSON, but it expects you to use the Python API for structured rows. Use the snippet above for end-to-end JSONL workflows.
