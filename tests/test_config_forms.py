"""Tests for config form TUI and headless Server behaviour."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from hw_test.context import FatalError, RuntimeContext
from hw_test.gui import config_forms


class ParseSelectionTests(unittest.TestCase):
    def test_parse_numbers(self) -> None:
        self.assertEqual(config_forms._parse_number_selection("8 13", 14), {8, 13})
        self.assertEqual(config_forms._parse_number_selection("1,2,3", 14), {1, 2, 3})
        self.assertEqual(config_forms._parse_number_selection("", 14), set())
        self.assertIsNone(config_forms._parse_number_selection("0 1", 14))
        self.assertIsNone(config_forms._parse_number_selection("abc", 14))


class ConfigFormsTuiTests(unittest.TestCase):
    @patch("hw_test.gui.config_forms._select_tests_tty", return_value={"fio"})
    @patch("hw_test.gui.config_forms.l10n.load_config_menu")
    def test_run_tui_uses_tty_checklist(self, load_menu: MagicMock, select: MagicMock) -> None:
        load_menu.return_value = ("", [("fio", "Disk perf")], 64)
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "en"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
        ctx.drives = "sda"
        config_forms.run_tui(ctx)
        self.assertEqual(ctx.fio_test, "1")
        select.assert_called_once()

    @patch("hw_test.gui.config_forms._select_tests_tty", return_value={"xprss", "power"})
    @patch("hw_test.gui.config_forms.l10n.load_config_menu")
    def test_run_tui_clears_express_on_headless_server(
        self, load_menu: MagicMock, _select: MagicMock
    ) -> None:
        load_menu.return_value = ("", [("xprss", "Express"), ("power", "Power")], 64)
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "ru"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
        ctx.have_xorg = ""
        config_forms.run_tui(ctx)
        self.assertEqual(ctx.xprss_test, "")
        self.assertEqual(ctx.power_test, "1")

    @patch("hw_test.gui.config_forms.clear_resume_autorun")
    @patch("hw_test.gui.config_forms._select_tests_tty", side_effect=KeyboardInterrupt)
    @patch("hw_test.gui.config_forms.l10n.load_config_menu")
    def test_run_tui_ctrl_c_cancels(
        self,
        load_menu: MagicMock,
        _select: MagicMock,
        clear_resume: MagicMock,
    ) -> None:
        load_menu.return_value = ("", [("power", "Power")], 64)
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "en"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
        with self.assertRaises(FatalError):
            config_forms.run_tui(ctx)
        clear_resume.assert_called_once_with(ctx)

    @patch("hw_test.gui.config_forms.Path")
    @patch("hw_test.gui.config_forms.sys.stdin.isatty", return_value=False)
    def test_run_tui_fatal_without_tty(self, _tty: object, path_cls: MagicMock) -> None:
        path_cls.return_value.exists.return_value = False
        ctx = RuntimeContext()
        ctx.progname = "hw-test"
        ctx.langid = "en"
        ctx.libdir = "/usr/libexec/hw-test"
        ctx.workdir = "/tmp/w"
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
