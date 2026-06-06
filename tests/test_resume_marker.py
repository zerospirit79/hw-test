"""Tests for headless resume marker (login, not boot)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hw_test.resume_autorun import (
    RESUME_ON_LOGIN,
    disable_headless_resume,
    enable_headless_resume,
)


class HeadlessResumeMarkerTests(unittest.TestCase):
    @patch("hw_test.resume_autorun._write_system_dropin")
    @patch("hw_test.resume_autorun.system_template_unit")
    @patch("hw_test.resume_autorun.subprocess.run")
    @patch("hw_test.resume_autorun.os.geteuid", return_value=1000)
    @patch("hw_test.resume_autorun.pwd.getpwnam")
    def test_enable_writes_marker_not_systemctl_enable(
        self,
        getpwnam: object,
        _euid: object,
        run: object,
        template: object,
        _dropin: object,
    ) -> None:
        template.return_value.is_file.return_value = True
        getpwnam.return_value = type("PW", (), {"pw_dir": "/home/test", "pw_uid": 1000})()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home" / "test"
            home.mkdir(parents=True)
            (home / "HW-TEST").mkdir()
            self.assertTrue(enable_headless_resume("hw-test", "test", str(home)))
            marker = home / "HW-TEST" / "STATE" / RESUME_ON_LOGIN
            self.assertTrue(marker.is_file())
            disable_calls = [
                c for c in run.call_args_list if c[0][0][:2] == ["systemctl", "disable"]
            ]
            enable_calls = [
                c for c in run.call_args_list if c[0][0][:2] == ["systemctl", "enable"]
            ]
            self.assertTrue(disable_calls)
            self.assertFalse(enable_calls)

    @patch("hw_test.resume_autorun.subprocess.run")
    @patch("hw_test.resume_autorun.pwd.getpwnam")
    def test_disable_removes_marker(self, getpwnam: object, _run: object) -> None:
        getpwnam.return_value = type("PW", (), {"pw_dir": "/home/test"})()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home" / "test"
            state = home / "HW-TEST" / "STATE"
            state.mkdir(parents=True)
            (state / RESUME_ON_LOGIN).write_text("", encoding="utf-8")
            disable_headless_resume("hw-test", "test", str(home))
            self.assertFalse((state / RESUME_ON_LOGIN).exists())


if __name__ == "__main__":
    unittest.main()
