# Examples

Short, runnable scripts that call `pc-control` as a subprocess and parse its JSON output. They exist to show the intended integration pattern — **treat `pc-control` as a typed JSON pipe**, not as a library.

Each script:

- Runs on Python 3.10+ with `pc-control` installed (`pip install -e .`).
- Uses only the stdlib (`subprocess`, `json`, `argparse`) plus whatever extra the example happens to need.
- Exits non-zero when the underlying command fails, and prints a human-readable error.

| Script | What it does | Needs |
|---|---|---|
| [`top_processes.py`](./top_processes.py) | Prints the N most CPU-hungry processes | base install |
| [`screenshot_to_text.py`](./screenshot_to_text.py) | Screenshots a region, OCRs it, prints the text | `[ocr]` extra |
| [`focus_or_launch.py`](./focus_or_launch.py) | Focuses an existing window by title, or exits gracefully | base install |
| [`browser_extract.py`](./browser_extract.py) | Navigates a persistent Chromium to a URL and extracts `<h1>` text | `[browser]` extra + `playwright install chromium` |
| [`clipboard_timer.py`](./clipboard_timer.py) | Sets the clipboard to a timestamp every N seconds | base install (Windows only) |

Run any example directly:

```bash
python examples/top_processes.py --limit 5
```
