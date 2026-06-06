"""Backlight control for express test (Wayland and X11)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Iterable

_BACKLIGHT_DEVICES = (
    "intel_backlight",
    "amdgpu_bl0",
    "amdgpu_bl1",
    "thinkpad_panel",
    "dmi_acpi",
)


def _backlight_devices() -> list[Path]:
    base = Path("/sys/class/backlight")
    if not base.is_dir():
        return []
    by_name = {p.name: p for p in base.iterdir() if p.is_dir()}
    ordered = [by_name[name] for name in _BACKLIGHT_DEVICES if name in by_name]
    ordered.extend(path for path in sorted(by_name.values()) if path not in ordered)
    return ordered


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _set_sysfs_level(device: Path, fraction: float) -> bool:
    max_brightness = _read_int(device / "max_brightness")
    if max_brightness is None or max_brightness <= 0:
        return False
    value = max(1, min(max_brightness, round(max_brightness * fraction)))
    try:
        (device / "brightness").write_text(f"{value}\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _set_brightnessctl(fraction: float) -> bool:
    if not shutil.which("brightnessctl"):
        return False
    percent = max(1, min(100, round(fraction * 100)))
    proc = subprocess.run(
        ["brightnessctl", "-q", "set", f"{percent}%"],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def _gdbus_set_brightness(dest: str, path: str, iface: str, prop: str, percent: int) -> bool:
    if not shutil.which("gdbus") or not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        return False
    proc = subprocess.run(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            dest,
            "--object-path",
            path,
            "--method",
            "org.freedesktop.DBus.Properties.Set",
            iface,
            prop,
            f"<int32 {percent}>",
        ],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def _set_gnome_brightness(fraction: float) -> bool:
    percent = max(0, min(100, round(fraction * 100)))
    return _gdbus_set_brightness(
        "org.gnome.SettingsDaemon.Power",
        "/org/gnome/SettingsDaemon/Power",
        "org.gnome.SettingsDaemon.Power",
        "Brightness",
        percent,
    )


def _set_kde_brightness(fraction: float) -> bool:
    percent = max(0, min(100, round(fraction * 100)))
    for qdbus in ("qdbus6", "qdbus"):
        if not shutil.which(qdbus):
            continue
        proc = subprocess.run(
            [
                qdbus,
                "org.kde.Solid.PowerManagement",
                "/org/kde/Solid/PowerManagement/Actions/BrightnessControl",
                "org.kde.Solid.PowerManagement.Actions.BrightnessControl.setBrightness",
                str(percent),
            ],
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return True
    return False


def set_brightness_level(
    fraction: float,
    *,
    xrandr_output: str = "",
    spawn: Callable[..., int] | None = None,
) -> str:
    """Set brightness level; return method name or empty string if all failed."""
    for name, fn in (
        ("brightnessctl", lambda: _set_brightnessctl(fraction)),
        (
            "sysfs",
            lambda: any(_set_sysfs_level(device, fraction) for device in _backlight_devices()),
        ),
        ("gnome", lambda: _set_gnome_brightness(fraction)),
        ("kde", lambda: _set_kde_brightness(fraction)),
    ):
        try:
            if fn():
                return name
        except OSError:
            continue
    if xrandr_output and spawn is not None:
        if spawn("xrandr", "--output", xrandr_output, "--brightness", str(fraction)) == 0:
            return "xrandr"
    return ""


def cycle_brightness_levels(
    levels: Iterable[float],
    *,
    xrandr_output: str = "",
    spawn: Callable[..., int] | None = None,
    log: Callable[[str], None] | None = None,
    sleep_seconds: float = 2.0,
    play_sound: Callable[[], None] | None = None,
) -> bool:
    """Cycle through brightness levels; return True if at least one change succeeded."""
    worked = False
    for fraction in levels:
        method = set_brightness_level(
            fraction,
            xrandr_output=xrandr_output,
            spawn=spawn,
        )
        if method:
            worked = True
            if log:
                log(f"*** brightness {fraction}: {method}\n")
            if play_sound:
                play_sound()
        elif log:
            log(f"*** brightness {fraction}: failed\n")
        time.sleep(sleep_seconds)
    return worked


def primary_xrandr_output() -> str:
    proc = subprocess.run(["xrandr"], capture_output=True, text=True, check=False)
    for line in (proc.stdout or "").splitlines():
        if " connected primary " in line:
            return line.split()[0]
    return ""
