# patternforge

Fast, deterministic glob-pattern discovery & human-readable explanations for hierarchical names.

## Practical use cases

### Diagram-ready rectangles
When you want a single rectangle in a block diagram to represent many child blocks, you can feed
just the instance names into the rectangle planner. The tool will group items by their top-level
segment so you can trade off between one broad rectangle or several focused ones.

```bash
cat <<'DATA' > rectangles.txt
video/display/pixel0
video/display/pixel1
video/shader/vec0
video/shader/vec1
video/memory/buffer0
video/memory/buffer1
video/io/ingress/decoder
video/io/egress/hdmi0
compute/dsp/unit0
compute/dsp/unit1
compute/dsp/unit2
compute/router/scheduler
compute/router/debug
compute/memory/cache0
compute/memory/cache1
DATA

python -m patternforge.cli plan-rectangles \
  --include rectangles.txt \
  --rect-budget 2 \
  --rect-penalty 1.5 \
  --exception-weight 1.0 \
  --format json
```

The planner reports that two rectangles – one for `video/*` and one for `compute/*` – cover all
15 blocks while letting you adjust the rectangle budget if you need smaller clusters.【0a8f4e†L1-L16】

### Regression triage
For nightly regression dashboards, you can treat failing runs as `--include` items and passing runs
as `--exclude`. Pattern discovery will surface the common fragments that explain the failures and the
`explain` command produces a concise JSON summary for dashboards.

```bash
cat <<'FAIL' > regress_failed.txt
regress/nightly/ipA/test_fifo/fail
regress/nightly/ipA/test_dma/fail
regress/nightly/ipB/test_cache/fail
regress/nightly/ipB/test_stream/fail
regress/nightly/ipC/test_uart/fail
FAIL

cat <<'PASS' > regress_passed.txt
regress/nightly/ipA/test_fifo/pass
regress/nightly/ipA/test_dma/pass
regress/nightly/ipB/test_cache/pass
regress/nightly/ipB/test_stream/pass
regress/nightly/ipC/test_uart/pass
regress/nightly/ipC/test_spi/pass
regress/nightly/ipC/test_i2c/pass
PASS

python -m patternforge.cli propose \
  --include regress_failed.txt \
  --exclude regress_passed.txt \
  --mode APPROX \
  --format text \
  --emit-witnesses \
  --out regress_solution.json

python -m patternforge.cli explain --solution regress_solution.json --format json
```

The solver finds a single atom `*fail*`, explains that it covers every failure, and lists true-positive
examples without false positives, which can be rendered directly in status e-mails or dashboards.【8cc236†L1-L6】【317a6a†L1-L27】

### Connection summaries with optional field schemas
When inspecting how sub-block pins connect to top-level signals, supply the hierarchical paths and
optionally a field schema so the CLI can tokenize by domain/block/instance/pin boundaries. This lets
you balance a compact expression against precision—adding more field-aware negative examples pushes the
solver toward multi-substring atoms when needed.

```bash
cat <<'INC' > fabric_cache_include.txt
fabric/mem_ctrl/cache0/inst0/data_in
fabric/mem_ctrl/cache0/inst0/tag
fabric/mem_ctrl/cache0/inst1/data_in
fabric/mem_ctrl/cache0/inst1/tag
fabric/mem_ctrl/cache1/inst0/data_in
fabric/mem_ctrl/cache1/inst0/tag
fabric/mem_ctrl/cache1/inst1/data_in
fabric/mem_ctrl/cache1/inst1/tag
INC

cat <<'EXC' > fabric_cache_exclude.txt
fabric/mem_ctrl/router/inst0/req
fabric/mem_ctrl/router/inst0/grant
fabric/mem_ctrl/router/inst1/req
fabric/mem_ctrl/router/inst1/grant
fabric/mem_ctrl/debug/trace/inst0/port
fabric/mem_ctrl/cache_debug/inst0/data_tap
fabric/mem_ctrl/cache_metrics/inst0/data_latency
fabric/mem_ctrl/cache_diag/inst2/tag
EXC

cat <<'SCHEMA' > fabric_schema.json
{"name": "fabric_path", "delimiter": "/", "fields": ["domain", "block", "subblock", "instance", "pin"]}
SCHEMA

python -m patternforge.cli propose \
  --include fabric_cache_include.txt \
  --exclude fabric_cache_exclude.txt \
  --schema fabric_schema.json \
  --mode APPROX \
  --format text \
  --emit-witnesses
```

Because every include path shares the `cache` sub-block prefix, the greedy solver chooses the concise
`*cache*` atom. The witness report highlights the remaining false positives (`cache_debug`,
`cache_metrics`, `cache_diag`), letting you decide whether to add more specific negative samples or
allow the trade-off in exchange for a simpler expression.【59e4df†L1-L10】

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
