# v0.1.0

First release of a local preflight gate for Google Benchmark JSON comparisons.
Detects inventory changes, missing raw repetitions, duplicate/incomplete indices,
skipped or errored measurements, thread/unit drift and required context mismatch.
Produces bounded findings in text or versioned JSON. Does not calculate speedups
or statistical significance and never executes a benchmark binary.

Local validation: 38 tests passed on Windows Python 3.13, including CLI and
negative controls. Ruff passed. Release validation installs the built wheel in
a fresh environment, runs all tests and both README fixture commands, then
uninstalls it. Remote release gating requires successful Linux/Windows CI; the
Linux Python 3.13 job additionally builds and runs the original C++ example
against the system Google Benchmark library and tests a removed-case control.

Known limits: documented common JSON subset only; aggregates are not numerical
evidence; arbitrary counters/complexity fits are not compared; matching declared
context cannot guarantee equivalent physical measurement conditions.

MIT licensed, no runtime dependencies. Bundled JSON files are synthetic examples.
