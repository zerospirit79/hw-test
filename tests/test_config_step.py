"""Tests for config step (headless dialog TUI vs GUI handoff)."""

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
    def test_pre_allows_dialog_without_tty_for_openvt(self, _gs: object, _tty: object) -> None:
        step = self._step()
        step.ctx.has_binary = MagicMock(side_effect=lambda name: name == "dialog")

        self.assertEqual(step.pre(), TEST_ALLOWED)

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=False)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    def test_pre_skips_batch_without_tty(self, _gs: object, _tty: object) -> None:
        step = self._step(batchmode="1")
        step.ctx.has_binary = MagicMock(side_effect=lambda name: name == "dialog")
        from hw_test.constants import TEST_SKIPPED

        self.assertEqual(step.pre(), TEST_SKIPPED)

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=True)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    def test_pre_allows_batch_with_tty(self, _gs: object, _tty: object) -> None:
        step = self._step(batchmode="1")
        step.ctx.has_binary = MagicMock(side_effect=lambda name: name == "dialog")
        self.assertEqual(step.pre(), TEST_ALLOWED)

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=True)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    @patch("hw_test.steps.config.config_forms.run_tui")
    @patch("hw_test.steps.config.os.geteuid", return_value=0)
    def test_testcase_runs_dialog_as_root_on_headless_tty(
        self, _euid: object, run_tui: MagicMock, _gs: object, _tty: object
    ) -> None:
        step = self._step()
        step.ctx.has_binary = MagicMock(side_effect=lambda name: name == "dialog")
        step.ctx.print_settings_ini = MagicMock()
        self.assertEqual(step.testcase(), TEST_ALLOWED)
        run_tui.assert_called_once()

    @patch("hw_test.steps.config.graphical_session", return_value=False)
    @patch("hw_test.steps.config.os.geteuid", return_value=0)
    def test_testcase_blocked_without_dialog(self, _euid: object, _gs: object) -> None:
        step = self._step()
        step.ctx.has_binary = MagicMock(return_value=False)
        self.assertEqual(step.testcase(), TEST_BLOCKED)


if __name__ == "__main__":
    unittest.main()
