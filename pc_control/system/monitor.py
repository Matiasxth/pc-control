"""System monitoring — CPU, RAM, disk, processes via psutil."""

from __future__ import annotations

import json
import shutil
import sys
from argparse import Namespace

import psutil


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def system_info() -> None:
    """Emit a summary of CPU load, memory usage, and C: disk usage.

    CPU load is sampled over 1 second (psutil.cpu_percent blocking call).
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk_total, disk_used, _ = shutil.disk_usage("C:/")
    _output(
        {
            "status": "ok",
            "action": "system_info",
            "cpu": {"percent": cpu_percent, "cores": psutil.cpu_count()},
            "memory": {
                "total_gb": round(mem.total / (1024**3), 1),
                "used_gb": round(mem.used / (1024**3), 1),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk_total / (1024**3), 1),
                "used_gb": round(disk_used / (1024**3), 1),
                "percent": round(disk_used / disk_total * 100, 1),
            },
        }
    )


def list_processes(
    sort_by: str = "cpu",
    filter_name: str | None = None,
    limit: int = 20,
) -> None:
    """Emit the top `limit` processes, sorted by CPU or memory.

    Args:
        sort_by: `"cpu"` or `"memory"`.
        filter_name: Case-insensitive substring match against process name.
        limit: Maximum number of processes to include.

    Processes that vanish mid-iteration or raise AccessDenied are silently
    skipped — this is best-effort monitoring, not an audit trail.
    """
    procs: list[dict] = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = p.info
            if filter_name and filter_name.lower() not in info["name"].lower():
                continue
            procs.append(
                {
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0,
                    "memory_mb": (
                        round(info["memory_info"].rss / (1024**2), 1) if info["memory_info"] else 0
                    ),
                    "status": info["status"],
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    key = "cpu_percent" if sort_by == "cpu" else "memory_mb"
    procs.sort(key=lambda x: x[key], reverse=True)
    procs = procs[:limit]

    _output({"status": "ok", "action": "processes", "count": len(procs), "processes": procs})


def kill_process(pid: int | None = None, name: str | None = None) -> None:
    """Kill a process by `pid` (exact) or `name` (case-insensitive, all matches)."""
    try:
        if pid:
            p = psutil.Process(pid)
            pname = p.name()
            p.kill()
            _output({"status": "ok", "action": "kill", "pid": pid, "name": pname})
        elif name:
            killed: list[int] = []
            for p in psutil.process_iter(["pid", "name"]):
                if p.info["name"].lower() == name.lower():
                    p.kill()
                    killed.append(p.info["pid"])
            _output({"status": "ok", "action": "kill", "name": name, "killed_pids": killed})
        else:
            _output({"status": "error", "error": "Provide --pid or --name"})
    except psutil.NoSuchProcess:
        _output({"status": "error", "error": f"Process not found: {pid or name}"})
    except psutil.AccessDenied:
        _output({"status": "error", "error": f"Access denied for process: {pid or name}"})


def handle_command(args: Namespace) -> None:
    """Dispatch `system <subcommand>` to the right handler."""
    if args.system_command == "info":
        system_info()
    elif args.system_command == "processes":
        list_processes(
            sort_by=getattr(args, "sort", "cpu"),
            filter_name=getattr(args, "filter", None),
            limit=getattr(args, "limit", 20),
        )
    elif args.system_command == "kill":
        kill_process(
            pid=getattr(args, "pid", None),
            name=getattr(args, "name", None),
        )
    else:
        print(f"Unknown system command: {args.system_command}", file=sys.stderr)
        sys.exit(1)
