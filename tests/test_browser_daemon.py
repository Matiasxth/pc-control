"""Tests for Chromium discovery in pc_control.browser.daemon."""

from pathlib import Path

import pytest

from pc_control.browser import daemon


def _make_chromium(base: Path, folder: str) -> Path:
    exe = base / folder / "chrome-win64" / "chrome.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    return exe


class TestFindChromiumExe:
    def test_returns_none_when_nothing_installed(self, tmp_path):
        assert daemon.find_chromium_exe(tmp_path) is None

    def test_finds_single_install(self, tmp_path):
        exe = _make_chromium(tmp_path, "chromium-1255")
        assert daemon.find_chromium_exe(tmp_path) == exe

    def test_picks_highest_revision_numerically(self, tmp_path):
        _make_chromium(tmp_path, "chromium-999")
        newest = _make_chromium(tmp_path, "chromium-1255")
        _make_chromium(tmp_path, "chromium-1208")
        assert daemon.find_chromium_exe(tmp_path) == newest

    def test_ignores_headless_shell_and_non_numeric_folders(self, tmp_path):
        _make_chromium(tmp_path, "chromium_headless_shell-2000")
        _make_chromium(tmp_path, "chromium-tip-of-tree")
        exe = _make_chromium(tmp_path, "chromium-1255")
        assert daemon.find_chromium_exe(tmp_path) == exe

    def test_ignores_revision_folder_without_exe(self, tmp_path):
        (tmp_path / "chromium-3000").mkdir()
        exe = _make_chromium(tmp_path, "chromium-1255")
        assert daemon.find_chromium_exe(tmp_path) == exe


class TestBrowsersDir:
    def test_honors_playwright_browsers_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
        assert daemon._playwright_browsers_dir() == tmp_path

    @pytest.mark.parametrize("value", [None, "0"])
    def test_defaults_to_localappdata(self, tmp_path, monkeypatch, value):
        if value is None:
            monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
        else:
            monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", value)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert daemon._playwright_browsers_dir() == tmp_path / "ms-playwright"
