"""Console power management step (methodology 10.6.2).

Order: suspend (10.6.2.4) -> hibernate (10.6.2.3) -> reboot (10.6.2.2)
-> power off (10.6.2.1). The RTC alarm (rtcwake -m no) wakes the computer
automatically; without it the tester presses a key or the power button.
Reboot and power off end the process: the step resumes after boot from
``power.step`` and marker files, the same way the express test does.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.manual import overall_status, record_subresult
from hw_test.steps.base import StepBase, register_step
from hw_test.steps.express import swap_fits_ram

SUBSTEPS = (
    ("suspend", "10.6.2.4"),
    ("hibernate", "10.6.2.3"),
    ("reboot", "10.6.2.2"),
    ("poweroff", "10.6.2.1"),
)
WAKEALARM = Path("/sys/class/rtc/rtc0/wakealarm")
STEP_FILE = "power.step"
# Задержка будильника RTC для каждого режима, секунд
ALARM_DELAY = {"suspend": 30, "hibernate": 60, "poweroff": 120}
MANUAL_WAIT = 600
MIN_SLEEP_GAP = 5.0


def sleep_supported(target: str, power: Path = Path("/sys/power")) -> tuple[bool, str]:
    """Whether the kernel offers the mode; the reason is shown when it does not."""
    try:
        states = (power / "state").read_text().split()
    except OSError:
        return False, "/sys/power/state is unavailable"
    if target == "suspend":
        if "mem" in states or "freeze" in states:
            return True, ""
        return False, "suspend is not supported by the kernel"
    if "disk" not in states:
        try:
            if "[disabled]" in (power / "disk").read_text():
                return False, "hibernation is disabled (kernel lockdown / SecureBoot)"
        except OSError:
            pass
        return False, "hibernation is not supported by the kernel"
    if not swap_fits_ram():
        return False, "SWAP is smaller than RAM"
    return True, ""


def slept_seconds(boot0: float, mono0: float) -> float:
    """CLOCK_BOOTTIME keeps counting during sleep, CLOCK_MONOTONIC does not."""
    return (time.clock_gettime(time.CLOCK_BOOTTIME) - boot0) - (time.monotonic() - mono0)


@register_step
class PowerStep(StepBase):
    STEP_ID = "power"
    number = "10.6.2"
    en_name = "Checking console power management"
    ru_name = "Управление питанием из консоли"

    def pre(self) -> int:
        ctx = self.ctx
        if not ctx.power_test:
            return TEST_SKIPPED
        if not ctx.have_systemd:
            return TEST_BLOCKED
        return TEST_ALLOWED

    def reset_results(self) -> None:
        for p in [Path(STEP_FILE), Path(f"results-{self.STEP_ID}.txt"), *Path(".").glob("PWR-*")]:
            p.unlink(missing_ok=True)

    def testcase(self) -> int:
        sfile = Path(STEP_FILE)
        idx = int(sfile.read_text().split()[0]) if sfile.is_file() else 0
        while idx < len(SUBSTEPS):
            sfile.write_text(f"{idx}\n", encoding="utf-8")
            target, number = SUBSTEPS[idx]
            if target in ("suspend", "hibernate"):
                rc = self._sleep(target)
            else:
                rc = self._restart(target)
            record_subresult(self.STEP_ID, number, rc)
            idx += 1
        sfile.unlink(missing_ok=True)
        return overall_status(self._recorded())

    def _recorded(self) -> list[int]:
        names = {"PASSED": TEST_PASSED, "FAILED": TEST_FAILED, "SKIPPED": TEST_SKIPPED}
        path = Path(f"results-{self.STEP_ID}.txt")
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        lines = [ln for ln in text.splitlines() if "\t" in ln]
        return [names.get(ln.split("\t")[1], TEST_BLOCKED) for ln in lines]

    def _say(self, ru: str, en: str) -> None:
        self.ctx.spawn(": " + (ru if self.ctx.langid == "ru" else en))

    def _set_alarm(self, target: str) -> bool:
        if not WAKEALARM.exists() or not self.ctx.has_binary("rtcwake"):
            return False
        return self.ctx.spawn("rtcwake", "-m", "no", "-s", str(ALARM_DELAY[target])) == 0

    def _sleep(self, target: str) -> int:
        ctx = self.ctx
        marker = Path(f"PWR-{target.upper()}-STARTED")
        if marker.is_file():
            # Повторный вход после загрузки: система не вернулась из сна
            marker.unlink()
            self._say(f"{target}: система не вышла из режима", f"{target}: no resume")
            return TEST_FAILED
        ok, reason = sleep_supported(target)
        if not ok:
            ctx.spawn(f": {target}: {reason}")
            return TEST_SKIPPED
        alarm = self._set_alarm(target)
        if not alarm:
            self._say(
                "Будильник RTC недоступен: разбудите компьютер клавишей или кнопкой питания",
                "No RTC alarm: wake the computer with a key or the power button",
            )
        marker.write_text("started\n", encoding="utf-8")
        subprocess.run(["sync"], check=False)
        boot0, mono0 = time.clock_gettime(time.CLOCK_BOOTTIME), time.monotonic()
        if ctx.spawn("systemctl", target) != 0:
            marker.unlink(missing_ok=True)
            return TEST_FAILED
        deadline = time.monotonic() + (ALARM_DELAY[target] + 90 if alarm else MANUAL_WAIT)
        slept = 0.0
        while time.monotonic() < deadline:
            slept = slept_seconds(boot0, mono0)
            if slept > MIN_SLEEP_GAP:
                break
            time.sleep(1)
        marker.unlink(missing_ok=True)
        ctx.spawn(f": {target}: slept {slept:.0f} s")
        return TEST_PASSED if slept > MIN_SLEEP_GAP else TEST_FAILED

    def _restart(self, target: str) -> int:
        ctx = self.ctx
        marker = Path(f"PWR-{target.upper()}-STARTED")
        if marker.is_file():
            marker.unlink()
            return TEST_PASSED
        from hw_test.resume_autorun import setup_resume_autorun

        marker.write_text("started\n", encoding="utf-8")
        ctx.chown_workdir_for_user()
        setup_resume_autorun(ctx, force=True)
        if target == "poweroff":
            alarm = self._set_alarm("poweroff")
            self._say(
                "Компьютер будет выключен. "
                + ("Он включится сам через 2 минуты, иначе " if alarm else "")
                + "включите его кнопкой питания и войдите в систему.",
                "The computer will power off. "
                + ("It will start in 2 minutes by itself, otherwise " if alarm else "")
                + "press the power button and log in.",
            )
        time.sleep(10)
        subprocess.run(["sync"], check=False)
        if ctx.spawn("systemctl", target) != 0:
            marker.unlink(missing_ok=True)
            return TEST_FAILED
        sys.exit(0)
