"""Tests that optional tests stay off until chosen in step 5.4."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hw_test.context import RuntimeContext
from hw_test.gui.config_forms import sync_detected_hardware


class OptionalTestDefaultsTests(unittest.TestCase):
    def test_sync_detected_hardware_keeps_fio_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp) / "HW-TEST"
            state = workdir / "STATE"
            state.mkdir(parents=True)
            (state / "settings.ini").write_text(
                "drives=sda\nfio_test=\n",
                encoding="utf-8",
            )
            (workdir / "detect.ini").write_text("drives=sda\nfio_test=1\n", encoding="utf-8")
            ctx = RuntimeContext()
            ctx.workdir = str(workdir)
            ctx.drives = "sda"
            sync_detected_hardware(ctx)
            self.assertEqual(ctx.fio_test, "")


if __name__ == "__main__":
    unittest.main()
