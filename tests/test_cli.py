"""Smoke tests for the CLI parser.

These tests do not invoke any command — they only verify that the argparse
tree builds and that every top-level module exposes `--help` without crashing.
Nothing here requires platform-specific dependencies (pywin32, pywinauto,
winsdk), which are only imported when a command actually runs.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from pc_control.cli import build_parser

TOP_LEVEL_MODULES = [
    "screen",
    "input",
    "windows",
    "browser",
    "system",
    "clipboard",
    "ocr",
    "desktop",
    "vision",
    "chat",
    "api",
    "audio",
    "app",
    "workflow",
]


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None
    assert parser.prog == "pc_control"


def test_root_help_lists_all_modules():
    parser = build_parser()
    help_text = parser.format_help()
    for mod in TOP_LEVEL_MODULES:
        assert mod in help_text, f"module '{mod}' missing from --help"


def test_root_help_cli_exits_zero():
    """`python -m pc_control --help` must exit 0 and write to stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "pc_control", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "usage:" in result.stdout.lower()


@pytest.mark.parametrize("module", TOP_LEVEL_MODULES)
def test_module_help_cli_exits_zero(module: str):
    """Each top-level module must respond to --help without crashing."""
    result = subprocess.run(
        [sys.executable, "-m", "pc_control", module, "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"`pc_control {module} --help` failed with code {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    assert "usage:" in result.stdout.lower()
