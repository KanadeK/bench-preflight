# bench-preflight

Catch incomplete or structurally incomparable **Google Benchmark JSON captures**
before interpreting a performance comparison.

Google Benchmark's [compare.py documentation](https://github.com/google/benchmark/blob/main/docs/tools.md)
explains that benchmarks with differing names are omitted from the diff. A
filtered-out case can therefore disappear from a comparison. bench-preflight
adds a conservative input gate: exact case coverage, complete raw repetitions,
compatible thread/unit semantics and declared environment fields.

It complements compare.py, benchstat and performance dashboards. **A pass is
not a claim of equal performance or statistical significance.** No benchmark
binary is executed by the CLI.

## Install

Requires Python 3.10+. No runtime dependencies, credentials or network calls.
Version 0.1.0 is distributed on GitHub, not PyPI.

```sh
git clone https://github.com/KanadeK/bench-preflight.git
cd bench-preflight
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS or
`.venv\Scripts\Activate.ps1` in PowerShell. Alternatively, invoke the executables
inside `.venv/bin` or `.venv\Scripts` directly.

```sh
python -m pip install .
bench-preflight examples/baseline.json examples/candidate.json --context compiler
# PASS: 2 baseline / 2 candidate cases; 0 findings
bench-preflight examples/baseline.json examples/missing.json --json
# Exit 1, case-removed: BM_Sum/64
```

The bundled JSON examples are **synthetic format fixtures**, not measured
performance. The candidate has deliberately larger timings and still passes:
this tool checks comparability, not speed. `examples/generate_examples.py`
recreates the fixtures.

## Use with real captures

Collect baseline and candidate results with raw repetitions enabled:

```sh
./bench-old --benchmark_repetitions=5 --benchmark_out=old.json --benchmark_out_format=json
./bench-new --benchmark_repetitions=5 --benchmark_out=new.json --benchmark_out_format=json
bench-preflight old.json new.json --min-repetitions 5 --context compiler --context cpu_model --json
```

Add `compiler` and `cpu_model` as custom context in your producer when using the
above contract. Keys must exist on both sides. Repeat `--context KEY` for other
fields that must be identical. Do not require a commit ID field to match if the
purpose is to compare two different commits. Review unrecorded confounders
yourself (hardware, load, affinity, flags, temperature, timer configuration).

By default `num_cpus` and `library_build_type` must be present and identical.
These two fields do **not** establish machine or environment equivalence.
Dates, hostnames and CPU frequency are not automatically compared. Custom
context keys are literal top-level keys, not dotted paths; values must be
non-null scalars. Mismatched field names are reported without their values.

## Checks and exact semantics

| Check | Behavior |
| --- | --- |
| Case identity | Exact iteration `name`; `run_name`, when present, must agree |
| Inventory | Both added and removed cases fail; no intersection-only comparison |
| Raw samples | Default minimum 3 successful iteration rows per case |
| Repetition metadata | Declared count, when present, must equal observed successful count; indices must form 0..n-1 |
| Multiple rows without indices | Fail, because repetitions cannot be distinguished reliably |
| Errors/skips | Any `error_occurred: true` or `skipped: true` fails; message bodies are not printed |
| Thread/time units | Consistent within each case and identical across captures |
| Timing | `real_time`/`cpu_time` must be finite nonnegative numbers; zero is allowed |
| Iterations | Positive integer; calibration counts may differ across runs |
| Aggregate rows | Never counted as raw repetitions; require explicit `run_name`; their numeric statistics are not checked |
| Aggregate-only case | Fails with `no-raw-repetitions` |

Different complete repetition counts are allowed when both meet the minimum.
Legacy single-iteration rows may omit `run_type`, `run_name`, `threads` and
repetition metadata: iteration, name and one thread are assumed. Such captures
require `--min-repetitions 1`; this is a structural check, not statistical proof.
Units are `ns`, `us`, `ms`, `s`; changing to a convertible unit still fails the
contract rather than silently converting it.

Exit **0**: contract passes. Exit **1**: valid report with preflight findings.
Exit **2**: malformed/unsupported input or invalid usage. `--json` emits schema
version 1, counts and findings; input errors include an `error` string.
`--max-findings` defaults to 200 and only truncates details, never failure status
or counts. Case names are escaped in terminal output.

```python
from bench_preflight.core import load, compare

result = compare(
    load("old.json"),
    load("new.json"),
    min_repetitions=5,
    context_keys=("num_cpus", "library_build_type", "compiler"),
)
assert result["ok"], result["counts"]
```

## Limits and validation

This is a documented common-format subset, not a universal Google Benchmark
schema validator. Unknown JSON fields are accepted; unknown run types fail.
Aggregate statistics, complexity fits, memory measurements, arbitrary counters,
counter units and hidden measurement conditions are outside the contract.
Complexity-only aggregates without matching raw cases fail. A successful check
does not establish unbiased sampling, adequate statistical power or test quality.

Maximum 32 MiB per input, 100,000 rows per capture, 4,096 characters per case/key
and 64 required context keys. UTF-8 (optional BOM) only. Duplicate JSON keys,
non-finite values and failed JSON parsing are rejected. Inputs must be stable
regular files. Capture case names may themselves be sensitive; keep exports
private when appropriate. The program never sends them anywhere.

Tests include malformed captures, missing/duplicate repetitions, case deletion,
unit/thread drift, false-pass negative controls and CLI exits. CI also compiles
the original small `examples/native_benchmark.cpp` against Google Benchmark,
collects two real captures and confirms that removing a real case fails. This
optional producer check requires a C++ compiler and the Google Benchmark library;
normal use does not. See [validation notes](docs/VALIDATION.md).

Uninstall: `python -m pip uninstall bench-preflight`. Remove the virtual
environment, clone and any captures you created when no longer needed. No
service, background task or global configuration is installed. Installation may
download setuptools; the installed CLI is offline.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT license](LICENSE)

## 中文说明

在解读 Google Benchmark 性能差异之前，检查两份结果是否具备一致的用例覆盖、
完整原始重复测量、相同线程数与时间单位，以及显式要求的环境字段。
它能发现被过滤掉的用例、重复或缺失的重复编号、错误或跳过的测量。
默认至少三次原始测量，汇总统计不能代替原始测量。
通过检查不代表性能相同，也不代表统计显著或环境完全一致。
示例 JSON 是明确标注的合成格式样本；CI 另外验证原生 C++ 生产者的实际输出。
