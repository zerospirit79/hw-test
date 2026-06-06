"""Tests for kgx terminal detection and close."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from hw_test.de_terminal import _binary_is_kgx, _real_xvt_path
from hw_test.terminal import close_kgx_window, running_in_kgx


class KgxTerminalTests(unittest.TestCase):
    def test_binary_is_kgx_detects_alternative_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kgx = root / "kgx"
            xvt = root / "xvt"
            kgx.write_text("#!/bin/sh\n", encoding="utf-8")
            xvt.symlink_to(kgx)
            kgx.chmod(0o755)
            with patch("hw_test.de_terminal.shutil.which", side_effect=lambda name: str(xvt if name == "xvt" else kgx)):
                self.assertTrue(_binary_is_kgx(str(xvt)))
                self.assertIsNone(_real_xvt_path())

    @patch.dict("os.environ", {"HW_TEST_KGX": "1"}, clear=False)
    def test_running_in_kgx_env_marker(self) -> None:
        with patch("hw_test.terminal._find_kgx_ancestor_pid", return_value=None):
            self.assertTrue(running_in_kgx())

    @patch.dict("os.environ", {"TERM_PROGRAM": "kgx"}, clear=False)
    def test_running_in_kgx_term_program(self) -> None:
        with patch("hw_test.terminal._find_kgx_ancestor_pid", return_value=None):
            self.assertTrue(running_in_kgx())

    @patch("hw_test.terminal._find_kgx_ancestor_pid", return_value=4242)
    def test_running_in_kgx(self, _mock: object) -> None:
        self.assertTrue(running_in_kgx())

    @patch("hw_test.terminal.time.sleep")
    @patch("hw_test.terminal.os.kill")
    @patch("hw_test.terminal._find_kgx_ancestor_pid", return_value=4242)
    @patch("hw_test.terminal.Path.exists", return_value=True)
    def test_close_kgx_window_sends_sigkill_if_needed(
        self, _exists: object, _find: object, kill: object, _sleep: object
    ) -> None:
        import signal

        close_kgx_window(uid=1000)
        kill.assert_any_call(4242, signal.SIGTERM)
        kill.assert_any_call(4242, signal.SIGKILL)

    @patch("hw_test.terminal._signal_kgx_pid")
    @patch("hw_test.terminal._find_kgx_ancestor_pid", return_value=None)
    @patch("hw_test.terminal.subprocess.run")
    def test_close_kgx_window_pgrep_uses_test_uid(
        self, run: object, _find: object, signal_kgx: object
    ) -> None:
        run.return_value = MagicMock(stdout="2261 kgx -T PC Test -e hw-test\n", returncode=0)
        close_kgx_window(uid=1000)
        run.assert_called_once()
        self.assertIn("-u", run.call_args[0][0])
        self.assertIn("1000", run.call_args[0][0])
        signal_kgx.assert_called_once_with(2261)


if __name__ == "__main__":
    unittest.main()
