"""Tests for desktop autostart file helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hw_test.desktop import chown_autostart_tree, remove_desktop_file


class DesktopAutostartTests(unittest.TestCase):
    def test_remove_desktop_file_ignores_permission_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            autostart = Path(tmp) / ".config" / "autostart"
            autostart.mkdir(parents=True)
            desktop = autostart / "hw-test.desktop"
            desktop.write_text("[Desktop Entry]\n", encoding="utf-8")
            os.chmod(autostart, 0o555)
            try:
                remove_desktop_file("hw-test", tmp)
            finally:
                os.chmod(autostart, 0o755)

    @patch("hw_test.desktop.subprocess.run")
    @patch("hw_test.desktop.pwd.getpwnam")
    @patch("hw_test.desktop.os.geteuid", return_value=0)
    def test_chown_autostart_tree_as_root(
        self, _euid: object, getpwnam: object, run: object
    ) -> None:
        getpwnam.return_value = object()
        with tempfile.TemporaryDirectory() as tmp:
            autostart = Path(tmp) / ".config" / "autostart"
            autostart.mkdir(parents=True)
            chown_autostart_tree(tmp, "test")
            self.assertTrue(run.called)


if __name__ == "__main__":
    unittest.main()
