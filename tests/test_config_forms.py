"""Tests for config form TUI (dialog)."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from hw_test.context import FatalError, RuntimeContext
from hw_test.gui import config_forms


class ConfigFormsTuiTests(unittest.TestCase):
    @patch("hw_test.gui.config_forms.subprocess.run")
    @patch("hw_test.gui.config_forms.sys.stdin.isatty", return_value=True)
    @patch("hw_test.gui.config_forms.l10n.load_config_menu")
    def test_run_tui_uses_terminal_for_dialog_ui(
        self, load_menu: MagicMock, _tty: object, run: MagicMock
    ) -> None:
        load_menu.return_value = ("", [("fio", "Disk perf")], 64)
        run.return_value = MagicMock(returncode=0, stderr="fio\n")
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "en"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
        ctx.drives = "sda"
        config_forms.run_tui(ctx)
        kwargs = run.call_args.kwargs
        self.assertIsNone(kwargs.get("stdout"))
        self.assertEqual(kwargs.get("stderr"), subprocess.PIPE)
        self.assertEqual(ctx.fio_test, "1")

    @patch("hw_test.gui.config_forms.sys.stdin.isatty", return_value=False)
    def test_run_tui_fatal_without_tty(self, _tty: object) -> None:
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "en"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
        ctx.has_binary = MagicMock(return_value=True)
        with self.assertRaises(FatalError):
            config_forms.run_tui(ctx)


if __name__ == "__main__":
    unittest.main()
