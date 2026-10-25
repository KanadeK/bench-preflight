# Security

Version 0.1.x is supported. Treat exported reports as potentially sensitive.
Only share redacted, minimal reproductions. Do not put credentials or private
test names in public issues. Report vulnerabilities through
[GitHub private reporting](https://github.com/KanadeK/bench-preflight/security/advisories/new).
If that channel is unavailable, open an issue asking for a private contact
without vulnerability details or sensitive data.

The CLI reads explicitly supplied local JSON files and emits a report. It does
not contact a network, execute input content or read ambient credentials.
Inputs have byte/record bounds; JSON duplicate keys and non-finite constants
are rejected. Resource limits are not an OS sandbox. Only process regular files;
do not use device files, named pipes or files being changed concurrently.
