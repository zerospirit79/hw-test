"""Tests for yad form helpers."""

from __future__ import annotations

import unittest

from hw_test.gui.forms import _yad_button, _yad_window_args


class YadFormHelpersTests(unittest.TestCase):
    def test_button_comma_format(self) -> None:
        btn = _yad_button("Пройден", "gtk-ok", "Подсказка, с запятой")
        self.assertEqual(btn, "--button=Пройден,gtk-ok,Подсказка, с запятой")

    def test_window_args_wrap_and_size(self) -> None:
        args = _yad_window_args(width=620, height=420)
        self.assertIn("--wrap", args)
        self.assertIn("--width=620", args)
        self.assertIn("--height=420", args)


if __name__ == "__main__":
    unittest.main()
