"""Tests for headless resume autostart logic."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from hw_test.context import RuntimeContext
from hw_test.resume_autorun import want_headless_resume


class WantHeadlessResumeTests(unittest.TestCase):
    def _ctx(self, **kwargs: object) -> RuntimeContext:
        ctx = RuntimeContext()
        ctx.have_systemd = "1"
        ctx.disable_autorun = ""
        ctx.headless_autorun = ""
        for key, value in kwargs.items():
            setattr(ctx, key, value)
        return ctx

    @patch("hw_test.resume_autorun.graphical_session", return_value=False)
    def test_auto_on_headless_with_systemd(self, _gs: object) -> None:
        self.assertTrue(want_headless_resume(self._ctx()))

    @patch("hw_test.resume_autorun.graphical_session", return_value=True)
    def test_auto_off_with_graphical_session(self, _gs: object) -> None:
        self.assertFalse(want_headless_resume(self._ctx()))

    @patch("hw_test.resume_autorun.graphical_session", return_value=False)
    def test_explicit_enable(self, _gs: object) -> None:
        self.assertTrue(want_headless_resume(self._ctx(headless_autorun="1")))

    @patch("hw_test.resume_autorun.graphical_session", return_value=False)
    def test_explicit_disable(self, _gs: object) -> None:
        self.assertFalse(want_headless_resume(self._ctx(headless_autorun="0")))

    @patch("hw_test.resume_autorun.graphical_session", return_value=False)
    def test_disable_autorun_blocks(self, _gs: object) -> None:
        self.assertFalse(want_headless_resume(self._ctx(disable_autorun="1")))


if __name__ == "__main__":
    unittest.main()
