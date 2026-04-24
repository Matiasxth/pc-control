"""Unit tests for pc_control.system.monitor.

These exercise real psutil calls — no mocks. Each test reads the JSON the
module prints to stdout and asserts on its shape and a few invariants.
"""

from __future__ import annotations

import json
import os

import pytest

from pc_control.system import monitor


def _json_output(capsys: pytest.CaptureFixture) -> dict:
    """Read captured stdout as a single JSON object."""
    out = capsys.readouterr().out.strip()
    assert out, "no stdout captured"
    return json.loads(out)


class TestSystemInfo:
    def test_emits_ok_status_with_expected_top_level_keys(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        monitor.system_info()
        data = _json_output(capsys)

        assert data["status"] == "ok"
        assert data["action"] == "system_info"
        assert set(data) >= {"status", "action", "cpu", "memory", "disk"}

    def test_cpu_percent_in_valid_range(self, capsys: pytest.CaptureFixture) -> None:
        monitor.system_info()
        data = _json_output(capsys)
        assert 0 <= data["cpu"]["percent"] <= 100
        assert data["cpu"]["cores"] >= 1

    def test_memory_fields_are_non_negative(self, capsys: pytest.CaptureFixture) -> None:
        monitor.system_info()
        data = _json_output(capsys)
        mem = data["memory"]
        assert mem["total_gb"] > 0
        assert mem["used_gb"] >= 0
        assert 0 <= mem["percent"] <= 100


class TestListProcesses:
    def test_default_returns_process_list(self, capsys: pytest.CaptureFixture) -> None:
        monitor.list_processes(limit=5)
        data = _json_output(capsys)

        assert data["status"] == "ok"
        assert data["action"] == "processes"
        assert isinstance(data["processes"], list)
        assert data["count"] == len(data["processes"])
        assert data["count"] <= 5

    def test_limit_caps_the_result_size(self, capsys: pytest.CaptureFixture) -> None:
        monitor.list_processes(limit=3)
        data = _json_output(capsys)
        assert len(data["processes"]) <= 3

    def test_sort_by_cpu_is_monotonically_non_increasing(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        monitor.list_processes(sort_by="cpu", limit=20)
        data = _json_output(capsys)
        cpus = [p["cpu_percent"] for p in data["processes"]]
        assert cpus == sorted(cpus, reverse=True)

    def test_sort_by_memory_is_monotonically_non_increasing(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        monitor.list_processes(sort_by="memory", limit=20)
        data = _json_output(capsys)
        mems = [p["memory_mb"] for p in data["processes"]]
        assert mems == sorted(mems, reverse=True)

    def test_filter_name_narrows_results(self, capsys: pytest.CaptureFixture) -> None:
        # Python itself is almost certainly running (it's running the test).
        monitor.list_processes(filter_name="python", limit=20)
        data = _json_output(capsys)
        assert data["status"] == "ok"
        for p in data["processes"]:
            assert "python" in p["name"].lower()

    def test_filter_name_with_no_matches_returns_empty(self, capsys: pytest.CaptureFixture) -> None:
        monitor.list_processes(filter_name="zzz_no_such_process_xyz", limit=20)
        data = _json_output(capsys)
        assert data["status"] == "ok"
        assert data["processes"] == []
        assert data["count"] == 0

    def test_process_records_have_expected_fields(self, capsys: pytest.CaptureFixture) -> None:
        monitor.list_processes(limit=5)
        data = _json_output(capsys)
        for p in data["processes"]:
            assert {"pid", "name", "cpu_percent", "memory_mb", "status"} <= set(p)


class TestKillProcess:
    def test_missing_args_returns_error(self, capsys: pytest.CaptureFixture) -> None:
        monitor.kill_process(pid=None, name=None)
        data = _json_output(capsys)
        assert data["status"] == "error"
        assert "--pid" in data["error"] or "--name" in data["error"]

    def test_unknown_pid_returns_error(self, capsys: pytest.CaptureFixture) -> None:
        # pid 999999 should not exist on any sane system; 2**31-1 is definitely free.
        fake_pid = 2**31 - 1
        assert not _pid_exists(fake_pid)

        monitor.kill_process(pid=fake_pid)
        data = _json_output(capsys)
        assert data["status"] == "error"


def _pid_exists(pid: int) -> bool:
    """Best-effort check that a given PID is not currently used."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    except Exception:
        return False
