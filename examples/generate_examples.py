"""Generate labelled synthetic fixtures; these are NOT performance measurements."""

import copy
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    baseline = {
        "context": {
            "num_cpus": 4,
            "library_build_type": "release",
            "compiler": "demo-toolchain",
            "fixture": "synthetic",
        },
        "benchmarks": [],
    }
    for name in ("BM_Sum/8", "BM_Sum/64"):
        for i in range(3):
            baseline["benchmarks"].append(
                {
                    "name": name,
                    "run_name": name,
                    "run_type": "iteration",
                    "repetitions": 3,
                    "repetition_index": i,
                    "threads": 1,
                    "iterations": 100,
                    "real_time": 10 + i,
                    "cpu_time": 9 + i,
                    "time_unit": "ns",
                }
            )
    candidate = copy.deepcopy(baseline)
    for row in candidate["benchmarks"]:
        row["real_time"] *= 2
        row["cpu_time"] *= 2
    missing = copy.deepcopy(candidate)
    missing["benchmarks"] = missing["benchmarks"][:3]
    for name, value in [("baseline", baseline), ("candidate", candidate), ("missing", missing)]:
        (root / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
