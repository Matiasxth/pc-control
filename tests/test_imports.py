"""Import smoke tests for platform-independent modules.

Modules that require Windows-only deps (pywin32, pywinauto, winsdk) are skipped
on non-Windows platforms rather than failing the suite.
"""
from __future__ import annotations

import importlib
import sys

import pytest

WINDOWS_ONLY = {
    "pc_control.system.clipboard",   # pywin32
    "pc_control.desktop.inspector",  # pywinauto
    "pc_control.desktop.daemon",     # pywinauto
    "pc_control.desktop.controller", # pywinauto
    "pc_control.ocr.windows_ocr",    # winsdk
    "pc_control.vision.detect",      # winsdk
}

CORE_MODULES = [
    "pc_control",
    "pc_control.cli",
    "pc_control.config",
    "pc_control.screen.capture",
    "pc_control.screen.context",
    "pc_control.input.controller",
    "pc_control.windows.manager",
    "pc_control.windows.layouts",
    "pc_control.system.monitor",
    "pc_control.system.clipboard",
    "pc_control.browser.commands",
    "pc_control.browser.navigate",
    "pc_control.desktop.commands",
    "pc_control.desktop.inspector",
    "pc_control.ocr.windows_ocr",
    "pc_control.vision.commands",
    "pc_control.vision.diff",
    "pc_control.api.commands",
    "pc_control.api.telegram",
    "pc_control.api.email_client",
    "pc_control.api.webhooks",
    "pc_control.chat.commands",
    "pc_control.audio.controller",
    "pc_control.app.launcher",
    "pc_control.workflow.engine",
]


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_module_imports(module_name: str):
    if module_name in WINDOWS_ONLY and sys.platform != "win32":
        pytest.skip(f"{module_name} requires Windows-only dependencies")
    importlib.import_module(module_name)


def test_package_has_version():
    import pc_control

    assert hasattr(pc_control, "__version__")
    assert isinstance(pc_control.__version__, str)
    assert pc_control.__version__.count(".") >= 1
