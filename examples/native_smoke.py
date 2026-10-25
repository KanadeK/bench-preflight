"""Exercise captures emitted by a real Google Benchmark binary (optional)."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from bench_preflight.core import compare, load


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as folder:
        paths = [Path(folder) / "first.json", Path(folder) / "second.json"]
        for path in paths:
            subprocess.run(
                [
                    executable,
                    f"--benchmark_out={path}",
                    "--benchmark_out_format=json",
                    "--benchmark_repetitions=3",
                    "--benchmark_min_time=0.001",
                ],
                check=True,
            )
        a, b = map(load, paths)
        result = compare(a, b)
        assert result["ok"], result
        assert result["baseline_cases"] == 2
        b["benchmarks"] = [
            r
            for r in b["benchmarks"]
            if r.get("run_name", r["name"])
            == a["benchmarks"][0].get("run_name", a["benchmarks"][0]["name"])
        ]
        assert compare(a, b)["counts"]["case-removed"] == 1
        print(
            json.dumps(
                {
                    "native_producer": "Google Benchmark",
                    "positive": result,
                    "negative_control": "one removed case detected",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
