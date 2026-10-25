import copy
import json
import subprocess
import sys

import pytest

from bench_preflight import core
from bench_preflight.cli import main
from bench_preflight.core import InputError, compare, load


def sample(name="BM_sum/8", index=0, count=3, **changes):
    row = dict(
        name=name,
        run_name=name,
        run_type="iteration",
        repetition_index=index,
        repetitions=count,
        iterations=50,
        threads=1,
        real_time=10.0,
        cpu_time=9.9,
        time_unit="ns",
    )
    row.update(changes)
    return row


def capture(names=("BM_sum/8", "BM_sum/64"), count=3):
    return {
        "context": {"num_cpus": 4, "library_build_type": "release", "compiler": "clang"},
        "benchmarks": [sample(n, i, count) for n in names for i in range(count)],
    }


def test_comparable_despite_timing_calibration_and_context_noise():
    a, b = capture(), capture()
    b["context"].update(date="later", host_name="another", mhz_per_cpu=1234)
    for row in b["benchmarks"]:
        row["real_time"] *= 3
        row["iterations"] = 999
    assert compare(a, b)["ok"]  # A preflight intentionally makes no regression claim.


def test_inventory_detects_added_and_removed_instead_of_silent_intersection():
    result = compare(capture(), capture(("BM_sum/8", "other")))
    assert result["counts"] == {"case-added": 1, "case-removed": 1}


@pytest.mark.parametrize("field,value", [("threads", 2), ("time_unit", "us")])
def test_changed_semantics(field, value):
    a, b = capture(), capture()
    for row in b["benchmarks"]:
        row[field] = value
    assert compare(a, b)["counts"] == {"semantics-mismatch": 2}


def test_context_required_and_no_value_leak():
    b = capture()
    b["context"]["compiler"] = "private-toolchain"
    result = compare(capture(), b, context_keys=("compiler", "missing"))
    assert result["counts"] == {"context-mismatch": 1, "context-missing": 1}
    assert "private-toolchain" not in json.dumps(result)


def test_aggregate_rows_do_not_count_as_samples_or_strip_suffix():
    a = capture(("BM_name_mean",))
    a["benchmarks"].append(
        {
            "name": "BM_name_mean_mean",
            "run_name": "BM_name_mean",
            "run_type": "aggregate",
            "aggregate_name": "mean",
        }
    )
    assert compare(a, a)["ok"]
    assert compare(a, a)["ignored_aggregate_rows"] == {"baseline": 1, "candidate": 1}
    b = copy.deepcopy(a)
    b["benchmarks"] = b["benchmarks"][-1:]
    result = compare(a, b)
    assert result["counts"] == {"no-raw-repetitions": 1}
    assert result["raw_repetitions"]["candidate"] == {}


@pytest.mark.parametrize("flag", ["error_occurred", "skipped"])
def test_unsuccessful_rows_are_findings_without_failure_body(flag):
    b = capture()
    b["benchmarks"][0] = sample(**{flag: True, "error_message": "SECRET", "real_time": None})
    result = compare(capture(), b)
    assert result["counts"]["unsuccessful-row"] == 1
    assert "SECRET" not in json.dumps(result)


def test_duplicate_or_missing_repetition_indices():
    b = capture()
    b["benchmarks"][1]["repetition_index"] = 0
    assert compare(capture(), b)["counts"] == {"repetition-index-mismatch": 1}
    b["benchmarks"][1].pop("repetition_index")
    assert compare(capture(), b)["counts"] == {"repetition-index-mismatch": 1}


def test_truncated_raw_rows_and_giant_declaration():
    b = capture()
    b["benchmarks"].pop()
    result = compare(capture(), b)
    assert result["counts"]["repetition-count-mismatch"] == 1
    assert result["counts"]["too-few-repetitions"] == 1
    a = capture()
    for row in a["benchmarks"]:
        row["repetitions"] = 2**62
    assert compare(a, a)["counts"]["repetition-count-mismatch"] == 4


def test_different_repetition_counts_allowed_if_complete_and_sufficient():
    assert compare(capture(count=3), capture(count=4))["ok"]


def test_legacy_single_row_needs_explicit_minimum():
    a = capture(("BM_one",), 1)
    for key in ("run_name", "run_type", "repetitions", "repetition_index", "threads"):
        a["benchmarks"][0].pop(key)
    assert compare(a, a, min_repetitions=1)["ok"]
    assert not compare(a, a)["ok"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("real_time", -1),
        ("cpu_time", True),
        ("cpu_time", float("inf")),
        ("real_time", 10**400),
        ("iterations", 0),
        ("iterations", 1.5),
        ("threads", True),
        ("time_unit", "minutes"),
        ("repetition_index", -1),
        ("repetitions", 0),
        ("run_type", "unknown"),
        ("run_name", "other"),
        ("skipped", "false"),
        ("name", ""),
    ],
)
def test_bad_iteration_fields(field, value):
    a = capture()
    a["benchmarks"][0][field] = value
    with pytest.raises(InputError):
        compare(a, capture())


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', "[", "[" * 2000])
def test_bad_json(tmp_path, raw):
    path = tmp_path / "bad.json"
    path.write_text(raw)
    with pytest.raises(InputError):
        load(path)


def test_empty_and_output_truncation():
    a = capture(tuple(str(i) for i in range(10)))
    b = {"context": capture()["context"], "benchmarks": []}
    report = compare(a, b, max_findings=2)
    assert not report["ok"] and report["finding_count"] == 11
    assert report["findings_truncated"] and len(report["findings"]) == 2


def test_limits_and_bom(tmp_path, monkeypatch):
    path = tmp_path / "a.json"
    path.write_text(json.dumps(capture()), encoding="utf-8-sig")
    assert compare(load(path), load(path))["ok"]
    monkeypatch.setattr(core, "MAX_BYTES", 20)
    with pytest.raises(InputError):
        load(path)
    monkeypatch.setattr(core, "MAX_ROWS", 2)
    with pytest.raises(InputError):
        compare(capture(), capture())


@pytest.mark.parametrize("document", [None, [], {}, {"context": {}, "benchmarks": 1}])
def test_invalid_document(document):
    with pytest.raises(InputError):
        compare(document, capture())


def test_cli_exit_codes_and_json(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(capture()))
    b.write_text(json.dumps(capture(("BM_sum/8",))))
    command = [sys.executable, "-m", "bench_preflight", str(a), str(b), "--json"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert json.loads(result.stdout)["counts"] == {"case-removed": 1}
    assert main([str(a), str(a), "--json"]) == 0
    assert main([str(a), str(b), "--min-repetitions", "0"]) == 2
    assert main([str(a), "missing", "--json"]) == 2
