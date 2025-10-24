# patternforge

Fast, deterministic glob-pattern discovery & human-readable explanations for hierarchical names.

## Practical use cases

> The examples below assume either `pip install -e .` has been run or `PYTHONPATH=src` is set when invoking `python`.

### Diagram-ready rectangles
When you want a single rectangle in a block diagram to represent many child blocks, you can feed the
instance names into the rectangle planner and tune the trade-off between budget and precision.

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

PYTHONPATH=src python -m patternforge.cli plan-rectangles   --include rectangles.txt   --rect-budget 3   --rect-penalty 1.2   --exception-weight 0.75   --format json
```

```json
{
  "rectangles": [
    {"count": 12, "prefix": "video", "score": 8.100000000000001},
    {"count": 10, "prefix": "compute", "score": 6.6000000000000005},
    {"count": 4, "prefix": "control", "score": 2.0999999999999996}
  ],
  "total": 26
}
```
【916189†L1-L22】

Python callers can reuse the same engine:

```python
from patternforge.engine.rectangles import plan_rectangles

with open("rectangles.txt", encoding="utf-8") as fh:
    items = [line.strip() for line in fh if line.strip()]

plan = plan_rectangles(items, rect_budget=3, rect_penalty=1.2, exception_weight=0.75)
print(plan["total"], [(r["prefix"], r["count"]) for r in plan["rectangles"]])
```

This prints `26 [('video', 12), ('compute', 10), ('control', 4)]`, matching the CLI result.【368892†L1-L11】

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
confirms 12/12 coverage with no false positives.【1032a2†L1-L21】【dcb00b†L1-L6】

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

This prints `P1 {'covered': 12, 'total_positive': 12, 'fp': 0, 'fn': 0}` so your dashboard pipeline can
render the summary directly.【177f37†L1-L13】

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

jq '.expr, .metrics, .atoms' fabric_cache_solution.json
```

The grouped CSV records collapse to the concise expression `*bank*`, capturing all cache-bank pins
while excluding debug and router traffic.【45afaf†L1-L21】

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
print(solution["expr"], solution["atoms"][0]["text"])
```

Running this prints `P1 *bank*`, confirming the CLI and API stay in sync.【ddb98d†L1-L14】
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
process CPU time (see `python - <<'PY' ...` in the repository history for the exact script).【4c0d3c†L1-L6】
