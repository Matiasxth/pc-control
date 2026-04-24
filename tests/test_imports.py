"""Import smoke tests.

Each module is tagged with any optional deps it hard-requires at import time.
If a dep is missing we skip — this keeps the test suite green on a minimal
install (base only) as well as on `.[all]`.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest

# (module_name, optional_deps_needed_at_import_time)
#
# Windows-only deps (pywin32, pywinauto, winsdk) are treated as optional:
# they live under `sys_platform == 'win32'` in pyproject and will simply be
# absent on other platforms.
MODULE_REQUIREMENTS: list[tuple[str, tuple[str, ...]]] = [
    ("pc_control", ()),
    ("pc_control.cli", ()),
    ("pc_control.config", ()),
    ("pc_control.screen.capture", ()),
    ("pc_control.screen.context", ()),
    ("pc_control.input.controller", ()),
    ("pc_control.windows.manager", ()),
    ("pc_control.windows.layouts", ()),
    ("pc_control.system.monitor", ()),
    ("pc_control.system.clipboard", ("win32clipboard",)),
    ("pc_control.browser.commands", ("playwright",)),
    ("pc_control.browser.navigate", ("playwright",)),
    ("pc_control.desktop.commands", ()),
    ("pc_control.desktop.inspector", ("pywinauto",)),
    ("pc_control.ocr.windows_ocr", ("winsdk",)),
    ("pc_control.vision.commands", ()),
    ("pc_control.vision.diff", ("numpy",)),
    ("pc_control.api.commands", ()),
    ("pc_control.api.telegram", ()),
    ("pc_control.api.email_client", ()),
    ("pc_control.api.webhooks", ()),
    ("pc_control.chat.commands", ()),
    ("pc_control.audio.controller", ()),
    ("pc_control.app.launcher", ()),
    ("pc_control.workflow.engine", ()),
]


def _missing(deps: tuple[str, ...]) -> list[str]:
    return [d for d in deps if importlib.util.find_spec(d) is None]


@pytest.mark.parametrize(
    "module_name,required",
    MODULE_REQUIREMENTS,
    ids=[m for m, _ in MODULE_REQUIREMENTS],
)
def test_module_imports(module_name: str, required: tuple[str, ...]):
    missing = _missing(required)
    if missing:
        pytest.skip(f"missing optional deps: {', '.join(missing)}")
    importlib.import_module(module_name)


def test_package_has_version():
    import pc_control

    assert hasattr(pc_control, "__version__")
    assert isinstance(pc_control.__version__, str)
    assert pc_control.__version__.count(".") >= 1


def test_platform_guard():
    """Sanity check: non-Windows runs will skip Windows-only modules."""
    win_only_deps = {"win32clipboard", "pywinauto", "winsdk"}
    found_any_skippable = any(
        set(reqs) & win_only_deps for _, reqs in MODULE_REQUIREMENTS
    )
    assert found_any_skippable, "expected at least one module tagged with Windows-only deps"
    if sys.platform != "win32":
        for dep in win_only_deps:
            assert importlib.util.find_spec(dep) is None, (
                f"{dep} unexpectedly importable on non-Windows"
            )
