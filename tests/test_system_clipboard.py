"""Unit tests for pc_control.system.clipboard.

Runs real clipboard operations — tests are skipped on non-Windows and also
when pywin32 is not importable. The tests save and restore the prior
clipboard contents when possible so they don't clobber the developer's
work.
"""

from __future__ import annotations

import json
import sys

import pytest

from pc_control.system import clipboard

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or not getattr(clipboard, "HAS_WIN32", False),
    reason="clipboard module requires Windows + pywin32",
)


def _json_output(capsys: pytest.CaptureFixture) -> dict:
    out = capsys.readouterr().out.strip()
    assert out, "no stdout captured"
    return json.loads(out)


@pytest.fixture
def preserve_clipboard(capsys: pytest.CaptureFixture):
    """Snapshot the clipboard before a test and restore it after."""
    clipboard.get_clipboard()
    snapshot = _json_output(capsys).get("text")
    yield
    if snapshot is None:
        clipboard.clear_clipboard()
    else:
        clipboard.set_clipboard(snapshot)
    # Drain the trailing output so the next test starts clean.
    capsys.readouterr()


class TestRoundTrip:
    def test_set_then_get_returns_same_ascii_text(
        self, capsys: pytest.CaptureFixture, preserve_clipboard
    ) -> None:
        clipboard.set_clipboard("hello world")
        assert _json_output(capsys)["status"] == "ok"

        clipboard.get_clipboard()
        data = _json_output(capsys)
        assert data["status"] == "ok"
        assert data["text"] == "hello world"

    def test_set_then_get_preserves_unicode(
        self, capsys: pytest.CaptureFixture, preserve_clipboard
    ) -> None:
        payload = "árbol 日本語 🎈"
        clipboard.set_clipboard(payload)
        capsys.readouterr()  # drop the set_clipboard ack

        clipboard.get_clipboard()
        data = _json_output(capsys)
        assert data["text"] == payload

    def test_clear_empties_clipboard(
        self, capsys: pytest.CaptureFixture, preserve_clipboard
    ) -> None:
        clipboard.set_clipboard("something")
        capsys.readouterr()

        clipboard.clear_clipboard()
        assert _json_output(capsys)["status"] == "ok"

        clipboard.get_clipboard()
        data = _json_output(capsys)
        # CF_UNICODETEXT not available after EmptyClipboard → text is None
        assert data["text"] is None


class TestResponseShape:
    def test_set_reports_length(self, capsys: pytest.CaptureFixture, preserve_clipboard) -> None:
        clipboard.set_clipboard("12345")
        data = _json_output(capsys)
        assert data["action"] == "clipboard_set"
        assert data["length"] == 5

    def test_get_emits_expected_keys(
        self, capsys: pytest.CaptureFixture, preserve_clipboard
    ) -> None:
        clipboard.get_clipboard()
        data = _json_output(capsys)
        assert data["action"] == "clipboard_get"
        assert "text" in data
