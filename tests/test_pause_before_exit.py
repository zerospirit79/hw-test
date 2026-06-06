"""Tests for pause_before_exit()."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from hw_test.main import pause_before_exit


class PauseBeforeExitTests(unittest.TestCase):
    def _ctx(self, **kwargs: object) -> MagicMock:
        ctx = MagicMock()
        ctx.batchmode = ""
        ctx.desktop_icon_start = ""
        ctx.username = "test"
        ctx.L.return_value = "Press any key"
        for key, value in kwargs.items():
            setattr(ctx, key, value)
        return ctx

    @patch("hw_test.main.close_desktop_terminal_if_needed")
    @patch("hw_test.main.read_key")
    @patch("hw_test.main.graphical_session", return_value=True)
    def test_shows_only_for_desktop_icon(
        self, _graphical: object, read_key: MagicMock, close: MagicMock
    ) -> None:
        pause_before_exit(self._ctx(desktop_icon_start="1"))
        read_key.assert_called_once()
        close.assert_called_once()

    @patch("hw_test.main.close_desktop_terminal_if_needed")
    @patch("hw_test.main.read_key")
    @patch("hw_test.main.graphical_session", return_value=True)
    def test_skips_without_desktop_icon(
        self, _graphical: object, read_key: MagicMock, close: MagicMock
    ) -> None:
        pause_before_exit(self._ctx())
        read_key.assert_not_called()
        close.assert_not_called()

    @patch("hw_test.main.close_desktop_terminal_if_needed")
    @patch("hw_test.main.read_key")
    @patch("hw_test.main.graphical_session", return_value=False)
    @patch("hw_test.main.os.geteuid", return_value=0)
    def test_closes_without_graphical_session_when_root(
        self,
        _euid: object,
        _graphical: object,
        read_key: MagicMock,
        close: MagicMock,
    ) -> None:
        pause_before_exit(self._ctx(desktop_icon_start="1"))
        read_key.assert_not_called()
        close.assert_called_once()

    @patch("hw_test.main.time.sleep")
    @patch("hw_test.main.read_key")
    def test_batchmode_sleeps(self, read_key: MagicMock, sleep: MagicMock) -> None:
        pause_before_exit(self._ctx(batchmode="1", desktop_icon_start="1"))
        read_key.assert_not_called()
        sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
