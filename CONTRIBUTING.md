# Contributing to pc-control

Thanks for taking the time. This project is small and opinionated — a CLI that speaks JSON — and the contribution guidelines reflect that.

## Ground rules

1. **JSON out, always.** Every CLI command must emit exactly one JSON object on stdout with at least a `status` field (`"ok"` or `"error"`). No banners, no progress spinners, no ANSI colors. If you need to log something human-readable, send it to stderr.
2. **Windows is the reference platform.** Modules that genuinely only work on Windows must use the `try: import …; HAS_X = True / except ImportError: HAS_X = False` pattern and return `{"status": "error", "error": "<dep> not available"}` when called on other platforms. The import itself must not crash.
3. **Persistent daemons** are the right answer for any backend that takes >200 ms to start (browser, WhatsApp, pywinauto). Make the first call cheap and every subsequent call fast.
4. **Don't add mandatory deps** for features that can be optional. Use an extras group in `pyproject.toml`.

## Development setup

```bash
git clone https://github.com/Matiasxth/pc-control.git
cd pc-control
pip install -e ".[all,dev]"
python -m playwright install chromium   # only if you touch browser/
```

## Before opening a PR

Run locally what CI will run:

```bash
ruff check pc_control examples tests
python -m compileall -q pc_control
pytest tests/ -v
```

If `ruff check` flags something, try `ruff check --fix` first. If you want to apply formatting, use `ruff format pc_control examples tests` — but note that CI does **not** currently enforce formatting (planned follow-up).

## Adding a new module

New top-level modules go in `pc_control/<name>/` with:

- `commands.py` — pure dispatch: reads `args`, calls plain functions, prints JSON.
- Everything else — actual implementation, with type hints and docstrings that match the conventions in `pc_control/screen/capture.py` and `pc_control/system/monitor.py`.
- Hook the subparser into `pc_control/cli.py:build_parser()`.
- Add an import test entry in `tests/test_imports.py`. If the module hard-requires an optional dep, tag it so CI skips cleanly on minimal installs.
- Add a one-line row to the feature table in `README.md`.

## Commit messages

Use conventional-ish prefixes that match what's already in the git log:

- `feat:` new user-visible feature
- `fix:` bug fix
- `docs:` README, CONTRIBUTING, docstrings
- `test:` test-only change
- `ci:` workflow or tooling
- `chore:` packaging, deps, housekeeping
- `refactor:` no behavior change

Keep the subject ≤72 chars, imperative mood. Use the body to explain *why*, not *what* (the diff already shows what).

## Reporting bugs

Open an issue and please include:

- OS + Python version
- Exact command you ran
- Full stdout + stderr
- What you expected vs. what happened

If the bug is in an optional-dep feature (browser, OCR, desktop, vision), run `pip show <package>` for that dep and include the version.

## License

By contributing, you agree that your contributions will be licensed under the MIT License, same as the rest of the project.
