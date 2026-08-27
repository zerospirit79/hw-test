"""Tests for config step (headless TUI vs GUI handoff)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED
from hw_test.context import RuntimeContext
from hw_test.steps.config import ConfigStep


class ConfigStepTests(unittest.TestCase):
    def _step(self, **ctx_attrs: object) -> ConfigStep:
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "en"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/hw-test-workdir"
        for key, value in ctx_attrs.items():
            setattr(ctx, key, value)
        step = ConfigStep()
        step.ctx = ctx
        return step

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=False)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    def test_pre_allows_without_tty_for_openvt(self, _gs: object, _tty: object) -> None:
        step = self._step()
        self.assertEqual(step.pre(), TEST_ALLOWED)

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=False)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    def test_pre_skips_batch_without_tty(self, _gs: object, _tty: object) -> None:
        step = self._step(batchmode="1")
        from hw_test.constants import TEST_SKIPPED

        self.assertEqual(step.pre(), TEST_SKIPPED)

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=True)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    def test_pre_allows_batch_with_tty(self, _gs: object, _tty: object) -> None:
        step = self._step(batchmode="1")
        self.assertEqual(step.pre(), TEST_ALLOWED)

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=True)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    @patch("hw_test.steps.config.config_forms.run_tui")
    @patch("hw_test.steps.config.os.geteuid", return_value=0)
    def test_testcase_runs_tui_as_root_on_headless_tty(
        self, _euid: object, run_tui: MagicMock, _gs: object, _tty: object
    ) -> None:
        step = self._step()
        step.ctx.print_settings_ini = MagicMock()
        self.assertEqual(step.testcase(), TEST_ALLOWED)
        run_tui.assert_called_once()

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=False)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    @patch("hw_test.steps.config.os.geteuid", return_value=0)
    def test_testcase_blocked_without_tty_when_openvt_fails(
        self, _euid: object, _gs: object, _tty: object
    ) -> None:
        step = self._step()
        step.ctx.username = ""
        self.assertEqual(step.testcase(), TEST_BLOCKED)


if __name__ == "__main__":
    unittest.main()
