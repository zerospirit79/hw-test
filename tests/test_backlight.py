"""Tests for backlight helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hw_test.backlight import (
    _set_sysfs_level,
    cycle_brightness_levels,
    set_brightness_level,
)


class BacklightTests(unittest.TestCase):
    def test_set_sysfs_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device = Path(tmp)
            (device / "max_brightness").write_text("100\n", encoding="utf-8")
            (device / "brightness").write_text("50\n", encoding="utf-8")
            self.assertTrue(_set_sysfs_level(device, 0.5))
            self.assertEqual((device / "brightness").read_text(encoding="utf-8").strip(), "50")
            self.assertTrue(_set_sysfs_level(device, 0.25))
            self.assertEqual((device / "brightness").read_text(encoding="utf-8").strip(), "25")

    @patch("hw_test.backlight._set_brightnessctl", return_value=True)
    def test_set_brightness_prefers_brightnessctl(self, _mock: object) -> None:
        self.assertEqual(set_brightness_level(0.5), "brightnessctl")

    @patch("hw_test.backlight._set_brightnessctl", return_value=False)
    @patch("hw_test.backlight._backlight_devices", return_value=[])
    @patch("hw_test.backlight._set_gnome_brightness", return_value=False)
    @patch("hw_test.backlight._set_kde_brightness", return_value=False)
    def test_set_brightness_falls_back_to_xrandr(
        self,
        _kde: object,
        _gnome: object,
        _devices: object,
        _ctl: object,
    ) -> None:
        calls: list[tuple[str, ...]] = []

        def spawn(*args: str) -> int:
            calls.append(args)
            return 0

        method = set_brightness_level(0.5, xrandr_output="eDP-1", spawn=spawn)
        self.assertEqual(method, "xrandr")
        self.assertEqual(calls[0], ("xrandr", "--output", "eDP-1", "--brightness", "0.5"))

    @patch("hw_test.backlight.set_brightness_level", return_value="sysfs")
    @patch("hw_test.backlight.time.sleep")
    def test_cycle_brightness_levels(self, _sleep: object, _set: object) -> None:
        played = {"count": 0}

        def play() -> None:
            played["count"] += 1

        self.assertTrue(
            cycle_brightness_levels((0.5, 0.75), play_sound=play, sleep_seconds=0)
        )
        self.assertEqual(played["count"], 2)


if __name__ == "__main__":
    unittest.main()
