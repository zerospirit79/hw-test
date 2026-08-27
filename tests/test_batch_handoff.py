"""Tests for batch-mode handoff before user/both steps."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from hw_test.constants import TEST_SKIPPED
from hw_test.context import RuntimeContext
from hw_test.user_handoff import step_needs_user_handoff


class BatchHandoffTests(unittest.TestCase):
    def _ctx_with_plan(self, tmp: str, stepname: str) -> RuntimeContext:
        workdir = Path(tmp) / "HW-TEST"
        state = workdir / "STATE"
        state.mkdir(parents=True)
        (state / "start.txt").write_text(f"both\t{stepname}\n", encoding="utf-8")
        ctx = RuntimeContext()
        ctx.workdir = str(workdir)
        ctx.testplan = "start.txt"
        ctx.batchmode = "1"
        return ctx

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=False)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    def test_config_not_handoff_in_batch_without_tty(self, _gs: object, _tty: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx_with_plan(tmp, "config")
            self.assertFalse(step_needs_user_handoff(ctx, "config"))

    @patch("hw_test.steps.config.sys.stdin.isatty", return_value=True)
    @patch("hw_test.steps.config.graphical_session", return_value=False)
    @patch("hw_test.user_handoff.graphical_session", return_value=False)
    def test_config_no_handoff_headless_with_tty(
        self, _gs_h: object, _gs: object, _tty: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx_with_plan(tmp, "config")
            ctx.batchmode = ""
            self.assertFalse(step_needs_user_handoff(ctx, "config"))

    @patch("hw_test.user_handoff.create_step")
    def test_express_handoff_when_enabled(self, create_step: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx_with_plan(tmp, "express")
            ctx.batchmode = ""
            step = MagicMock()
            step.pre.return_value = 0
            create_step.return_value = step
            self.assertTrue(step_needs_user_handoff(ctx, "express"))

    @patch("hw_test.user_handoff.create_step")
    def test_express_skip_when_pre_skipped(self, create_step: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx_with_plan(tmp, "express")
            step = MagicMock()
            step.pre.return_value = TEST_SKIPPED
            create_step.return_value = step
            self.assertFalse(step_needs_user_handoff(ctx, "express"))


if __name__ == "__main__":
    unittest.main()
