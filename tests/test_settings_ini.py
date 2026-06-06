"""Tests for settings.ini vs CLI launch flags."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hw_test.config_loader import SETTINGS_INI_SKIP_KEYS, load_config_files
from hw_test.context import RuntimeContext


class SettingsIniSkipTests(unittest.TestCase):
    def test_batchmode_not_loaded_from_settings_ini(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / "settings.ini"
            ini.write_text("batchmode=\nfio_test=1\n", encoding="utf-8")
            ctx = RuntimeContext()
            ctx.batchmode = "1"
            load_config_files(ctx, ini, skip_keys=SETTINGS_INI_SKIP_KEYS)
            self.assertEqual(ctx.batchmode, "1")
            self.assertEqual(ctx.fio_test, "1")


if __name__ == "__main__":
    unittest.main()
