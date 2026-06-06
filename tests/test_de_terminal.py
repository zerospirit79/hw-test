"""Tests for headless virtual-terminal resume."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from hw_test.de_terminal import run_continue_on_vt_as_root, spawn_continue_on_vt


class SpawnContinueOnVtTests(unittest.TestCase):
    @patch("hw_test.de_terminal.subprocess.run")
    @patch("hw_test.de_terminal.shutil.which", side_effect=lambda name: name in ("openvt", "runuser"))
    @patch("hw_test.de_terminal.pwd.getpwnam")
    @patch("hw_test.de_terminal.os.geteuid", return_value=0)
    def test_run_continue_on_vt_as_root(
        self, _euid: object, getpwnam: MagicMock, _which: object, run: MagicMock
    ) -> None:
        getpwnam.return_value = MagicMock(pw_uid=1000)
        run.return_value = MagicMock(returncode=0)
        self.assertTrue(run_continue_on_vt_as_root("test"))
        self.assertEqual(run.call_args[0][0][0], "openvt")

    @patch("hw_test.de_terminal.subprocess.run")
    @patch("hw_test.de_terminal.pwd.getpwnam")
    @patch("hw_test.de_terminal.os.geteuid", return_value=1000)
    def test_spawn_continue_on_vt_uses_sudo(
        self, _euid: object, getpwnam: MagicMock, run: MagicMock
    ) -> None:
        getpwnam.return_value = MagicMock(pw_uid=1000)
        run.return_value = MagicMock(returncode=0)
        self.assertTrue(spawn_continue_on_vt("test"))
        self.assertEqual(run.call_args[0][0][:2], ["sudo", "-n"])


if __name__ == "__main__":
    unittest.main()
