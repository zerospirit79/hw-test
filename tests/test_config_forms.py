"""Tests for config form TUI (dialog) and headless Server behaviour."""

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
        env = kwargs.get("env") or {}
        self.assertGreaterEqual(int(env.get("ESCDELAY", "0")), 3000)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[cmd.index("--checklist") + 1], "")

    @patch("hw_test.gui.config_forms.subprocess.run")
    @patch("hw_test.gui.config_forms.sys.stdin.isatty", return_value=True)
    @patch("hw_test.gui.config_forms.l10n.load_config_menu")
    def test_run_tui_clears_express_on_headless_server(
        self, load_menu: MagicMock, _tty: object, run: MagicMock
    ) -> None:
        load_menu.return_value = ("", [("xprss", "Express"), ("power", "Power")], 64)
        run.return_value = MagicMock(returncode=0, stderr="xprss power\n")
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "ru"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
        ctx.have_xorg = ""
        config_forms.run_tui(ctx)
        self.assertEqual(ctx.xprss_test, "")
        self.assertEqual(ctx.power_test, "1")

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


class ClearGraphicsOnlyTests(unittest.TestCase):
    def test_keeps_express_when_desktop_present(self) -> None:
        ctx = RuntimeContext()
        ctx.have_xorg = "1"
        ctx.have_gnome = "1"
        ctx.xprss_test = "1"
        self.assertEqual(config_forms.clear_graphics_only_tests(ctx), [])
        self.assertEqual(ctx.xprss_test, "1")

    def test_clears_express_without_desktop(self) -> None:
        ctx = RuntimeContext()
        ctx.have_xorg = ""
        ctx.xprss_test = "1"
        ctx.v3d_test = "1"
        ctx.power_test = "1"
        cleared = config_forms.clear_graphics_only_tests(ctx)
        self.assertIn("xprss", cleared)
        self.assertIn("v3d", cleared)
        self.assertEqual(ctx.xprss_test, "")
        self.assertEqual(ctx.power_test, "1")


if __name__ == "__main__":
    unittest.main()
