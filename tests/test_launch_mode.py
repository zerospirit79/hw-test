"""Tests for resolve_launch_mode --auto behaviour."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hw_test.context import RuntimeContext
from hw_test.main import resolve_launch_mode


class AutoLaunchModeTests(unittest.TestCase):
    def test_auto_continues_from_hw_test_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            workdir = home / ".local/share" / "hw-test" / "2026-06-06"
            state = workdir / "STATE"
            state.mkdir(parents=True)
            (workdir / "hw-test.log").write_text("log\n", encoding="utf-8")
            (state / "start.txt").write_text("root\tprepare\n", encoding="utf-8")
            (state / "STEP").write_text("detect\n", encoding="utf-8")
            (home / "HW-TEST").symlink_to(workdir)

            ctx = RuntimeContext()
            ctx.progname = "hw-test"
            ctx.username = "test"
            ctx.homedir = str(home)
            ctx.launchmode = "auto"
            ctx.repodate = ""

            resolve_launch_mode(ctx)

            self.assertEqual(ctx.launchmode, "continue")
            self.assertEqual(ctx.workdir, str(workdir))


if __name__ == "__main__":
    unittest.main()
