# Validation scope and independent review

Tests cover identity, inventory removal/addition, complete and incomplete
repetitions, duplicate indices, aggregate-only results, skipped/error rows,
thread/unit mismatches, context privacy, legacy rows, malformed/oversize JSON,
non-finite or huge numbers, truncated findings and CLI return codes.

The key false-pass control deletes a case that would otherwise disappear from
an intersection comparison. Another control doubles all timings and still
passes, demonstrating that no performance-regression result is fabricated.

The native integration script runs two real Google Benchmark captures, validates
them, then removes a case and requires a failure finding. The C++ example is
original project code. The upstream library is an external build dependency,
not bundled or copied into this repository; its distribution retains its own
license. Normal users need only the Python standard library.

Review decisions: bound comparisons by observed rows rather than allocating a
range from untrusted repetition counts; never strip aggregate-name suffixes to
guess identity; suppress arbitrary producer error/skip messages; preserve exit
failure even when findings are truncated. Optional unknown fields remain outside
the comparability contract rather than receiving unsupported interpretations.

Release notes record observed validation. CI tests installed wheels on Ubuntu
Python 3.10/3.13 and Windows Python 3.13. Workflows never commit code.
