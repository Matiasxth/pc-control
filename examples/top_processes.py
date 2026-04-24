"""Print the top N processes by CPU usage.

Demonstrates the typical subprocess + JSON pattern:
  1. Call `pc-control` as a child process.
  2. Parse stdout as JSON.
  3. Surface errors via the `status` field.

Usage:
    python examples/top_processes.py --limit 5
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run_pc_control(*args: str) -> dict:
    """Invoke `pc-control` with the given args and return its JSON output."""
    cmd = [sys.executable, "-m", "pc_control", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"pc-control exited {result.returncode}\nstderr: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=10, help="How many to show")
    parser.add_argument(
        "--sort", choices=["cpu", "memory"], default="cpu", help="Sort key"
    )
    args = parser.parse_args()

    data = run_pc_control(
        "system", "processes", "--sort", args.sort, "--limit", str(args.limit)
    )
    if data.get("status") != "ok":
        print(f"error: {data.get('error')}", file=sys.stderr)
        return 1

    width = max(len(p["name"]) for p in data["processes"]) if data["processes"] else 20
    print(f"{'PID':>7}  {'NAME':<{width}}  {'CPU%':>6}  {'MEM (MB)':>9}")
    for p in data["processes"]:
        print(
            f"{p['pid']:>7}  {p['name']:<{width}}  "
            f"{p['cpu_percent']:>6.1f}  {p['memory_mb']:>9.1f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
