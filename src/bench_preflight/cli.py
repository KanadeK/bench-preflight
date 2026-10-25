"""Offline command-line preflight."""

import argparse
import json
import sys

from . import __version__
from .core import DEFAULT_CONTEXT, InputError, compare, load


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preflight two Google Benchmark JSON captures.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--min-repetitions", type=int, default=3)
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="KEY",
        help="additional exact scalar context field (repeatable)",
    )
    parser.add_argument("--max-findings", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = compare(
            load(args.baseline),
            load(args.candidate),
            min_repetitions=args.min_repetitions,
            context_keys=(*DEFAULT_CONTEXT, *args.context),
            max_findings=args.max_findings,
        )
    except InputError as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "ok": False, "error": str(exc)}))
        else:
            print(f"Input error: {str(exc)!r}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
    else:
        print(
            f"{'PASS' if report['ok'] else 'FAIL'}: "
            f"{report['baseline_cases']} baseline / {report['candidate_cases']} candidate cases; "
            f"{report['finding_count']} findings"
        )
        for finding in report["findings"]:
            print(json.dumps(finding, ensure_ascii=True))
        if report["findings_truncated"]:
            print("Findings truncated; failure status and counts remain complete.")
    return 0 if report["ok"] else 1
