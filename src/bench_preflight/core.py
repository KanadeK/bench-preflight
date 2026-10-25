"""Structural and declared-context checks before comparing benchmark captures."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
DEFAULT_CONTEXT = ("num_cpus", "library_build_type")


class InputError(ValueError):
    """Unsupported or malformed benchmark input."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InputError("non-finite JSON number")
    return result


def _constant(value):
    raise InputError(f"invalid JSON constant: {value}")


def load(path: str | Path) -> dict:
    path = Path(path)
    try:
        if not path.is_file():
            raise InputError("input must be a regular file")
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise InputError("input exceeds 32 MiB")
        return json.loads(
            data.decode("utf-8-sig"),
            object_pairs_hook=_pairs,
            parse_float=_float,
            parse_constant=_constant,
        )
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise InputError(f"cannot read {str(path)!r}: {exc}") from exc


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise InputError(f"{field} must be a nonblank string of at most 4096 characters")
    return value


def _integer(value, field, minimum=1):
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise InputError(f"{field} must be an integer in [{minimum}, 2^63-1]")
    return value


def _timing(value, field):
    if type(value) not in (int, float) or value < 0:
        raise InputError(f"{field} must be a finite nonnegative number")
    try:
        if not math.isfinite(value):
            raise InputError(f"{field} must be finite")
    except OverflowError as exc:
        raise InputError(f"{field} is too large") from exc


def _capture(document, side, add, minimum):
    if not isinstance(document, dict) or not isinstance(document.get("context"), dict):
        raise InputError(f"{side}: context must be an object")
    if "num_cpus" in document["context"]:
        _integer(document["context"]["num_cpus"], "context.num_cpus")
    if "library_build_type" in document["context"]:
        _text(document["context"]["library_build_type"], "context.library_build_type")
    rows = document.get("benchmarks")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise InputError(f"{side}: benchmarks must be a list of at most 100000 rows")
    if not rows:
        add("empty-capture", side=side)
    groups = defaultdict(list)
    aggregate_cases = set()
    ignored = 0
    for row in rows:
        if not isinstance(row, dict):
            raise InputError(f"{side}: every benchmark row must be an object")
        name = _text(row.get("name"), "name")
        kind = row.get("run_type", "iteration")
        if kind not in ("iteration", "aggregate"):
            raise InputError(f"{side}: unknown run_type")
        for flag in ("error_occurred", "skipped"):
            if flag in row and type(row[flag]) is not bool:
                raise InputError(f"{flag} must be boolean")
        failed = row.get("error_occurred", False) or row.get("skipped", False)
        if kind == "aggregate":
            # Never infer raw names by removing '_mean' or other suffixes.
            case = _text(row.get("run_name"), "aggregate run_name")
            aggregate_cases.add(case)
            ignored += 1
            if failed:
                add("unsuccessful-row", side=side, case=case)
            continue
        case = row.get("run_name", name)
        _text(case, "run_name")
        if case != name:
            raise InputError("iteration name and run_name must match")
        groups[case].append(row)
        if failed:
            add("unsuccessful-row", side=side, case=case)
            continue
        _integer(row.get("iterations"), "iterations")
        _integer(row.get("threads", 1), "threads")
        if row.get("time_unit") not in ("ns", "us", "ms", "s"):
            raise InputError("iteration time_unit must be ns, us, ms or s")
        for field in ("real_time", "cpu_time"):
            _timing(row.get(field), field)
        if "repetitions" in row:
            _integer(row["repetitions"], "repetitions")
        if "repetition_index" in row:
            _integer(row["repetition_index"], "repetition_index", 0)
    for case in sorted(aggregate_cases - groups.keys()):
        add("no-raw-repetitions", side=side, case=case)
    semantics = {}
    sample_counts = {}
    for case, records in sorted(groups.items()):
        good = [r for r in records if not r.get("error_occurred") and not r.get("skipped")]
        sample_counts[case] = len(good)
        if len(good) < minimum:
            add("too-few-repetitions", side=side, case=case, observed=len(good), required=minimum)
        declarations = {r.get("repetitions") for r in good}
        indices = [r.get("repetition_index") for r in good]
        if len(declarations) > 1:
            add("inconsistent-repetitions", side=side, case=case)
        declared = next(iter(declarations)) if len(declarations) == 1 else None
        if declared is not None and declared != len(good):
            add(
                "repetition-count-mismatch",
                side=side,
                case=case,
                declared=declared,
                observed=len(good),
            )
        if len(good) > 1 or any(i is not None for i in indices):
            # Comparing to range(len), rather than range(declared), bounds memory
            # even when a malicious declaration is astronomically large.
            if None in indices or sorted(indices) != list(range(len(good))):
                add("repetition-index-mismatch", side=side, case=case)
        signatures = {(r.get("threads", 1), r["time_unit"]) for r in good}
        if len(signatures) > 1:
            add("inconsistent-semantics", side=side, case=case)
        if len(signatures) == 1:
            semantics[case] = next(iter(signatures))
    return set(groups) | aggregate_cases, semantics, sample_counts, ignored


def compare(
    baseline: dict,
    candidate: dict,
    *,
    min_repetitions=3,
    context_keys=DEFAULT_CONTEXT,
    max_findings=200,
) -> dict:
    """Apply a conservative contract; does not calculate performance regressions."""
    _integer(min_repetitions, "min_repetitions")
    if min_repetitions > MAX_ROWS:
        raise InputError("min_repetitions exceeds row limit")
    _integer(max_findings, "max_findings")
    if max_findings > 10000:
        raise InputError("max_findings must not exceed 10000")
    context_keys = tuple(dict.fromkeys(context_keys))
    if not context_keys or len(context_keys) > 64:
        raise InputError("require between 1 and 64 context keys")
    for key in context_keys:
        _text(key, "context key")
    findings = []
    counts = Counter()

    def add(code, **details):
        counts[code] += 1
        if len(findings) < max_findings:
            findings.append({"code": code, **details})

    old, old_semantics, old_counts, old_ignored = _capture(
        baseline, "baseline", add, min_repetitions
    )
    new, new_semantics, new_counts, new_ignored = _capture(
        candidate, "candidate", add, min_repetitions
    )
    for key in context_keys:
        a, b = baseline["context"], candidate["context"]
        if key not in a or key not in b or a.get(key) is None or b.get(key) is None:
            add("context-missing", field=key)
        elif type(a[key]) is not type(b[key]) or a[key] != b[key]:
            add("context-mismatch", field=key)
        elif isinstance(a[key], (dict, list)):
            raise InputError("required context values must be scalar")
        elif isinstance(a[key], str) and not a[key].strip():
            add("context-missing", field=key)
        elif isinstance(a[key], float) and not math.isfinite(a[key]):
            raise InputError("required context value must be finite")
    for case in sorted(old - new):
        add("case-removed", case=case)
    for case in sorted(new - old):
        add("case-added", case=case)
    for case in sorted(old_semantics.keys() & new_semantics.keys()):
        if old_semantics[case] != new_semantics[case]:
            add("semantics-mismatch", case=case)
    total = sum(counts.values())
    return {
        "schema_version": 1,
        "ok": total == 0,
        "baseline_cases": len(old),
        "candidate_cases": len(new),
        "required_context": list(context_keys),
        "min_repetitions": min_repetitions,
        "raw_repetitions": {"baseline": old_counts, "candidate": new_counts},
        "ignored_aggregate_rows": {"baseline": old_ignored, "candidate": new_ignored},
        "counts": dict(sorted(counts.items())),
        "finding_count": total,
        "findings": findings,
        "findings_truncated": total > len(findings),
    }
