# Contributing

Use Python 3.10 or newer in a virtual environment. Install the package and tools:

```sh
python -m pip install -e . -r requirements-dev.txt
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m build
```

For packaging validation, install the built wheel into a fresh environment and
run the README examples outside the source directory. Keep examples synthetic
and label them. Include negative tests and a minimal reproduction for bug fixes.
Do not include secrets, private report contents or machine-specific paths.

Open an issue before broad format or behavior changes. Documentation and tests
must describe limits accurately. This repository has no automated code-writing
or dependency-update bot. Maintainer review is required for changes.
