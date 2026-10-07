"""Peripheral checks with the tester's verdict (methodology 10.4, 10.10.x).

Each step runs what can be automated (playback, recording, service and
device listings), saves the output and then asks the tester for the
result in the same form as the manual express test.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.context import graphical_session
from hw_test.manual import ask_result, overall_status, record_subresult
from hw_test.steps.base import StepBase, register_step


def _run_to(report: list[str], cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        report += [f"# {' '.join(cmd)}", str(e)]
        return subprocess.CompletedProcess(cmd, 1, "", str(e))
    report += [
        f"# {' '.join(cmd)}  (exit {proc.returncode})",
        (proc.stdout or proc.stderr).rstrip(),
    ]
    return proc


def _tee(cmd: list[str]) -> tuple[int, str]:
    """Run an interactive command showing its output; return exit code and output."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except OSError as e:
        return 127, str(e)
    lines = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line)
    return proc.wait(), "".join(lines)


class _GuiStep(StepBase):
    """Steps that the methodology runs only in a graphical session."""

    flag = ""

    def pre(self) -> int:
        if not getattr(self.ctx, f"{self.flag}_test", ""):
            return TEST_SKIPPED
        if not graphical_session():
            return TEST_SKIPPED
        return TEST_ALLOWED

    def _say(self, ru: str, en: str) -> None:
        self.ctx.spawn(": " + (ru if self.ctx.langid == "ru" else en))


@register_step
class SoundStep(_GuiStep):
    STEP_ID = "sound"
    number = "10.4"
    en_name = "Checking the sound subsystem"
    ru_name = "Проверка звуковой подсистемы"
    flag = "sound"

    def testcase(self) -> int:
        ctx = self.ctx
        statuses = []
        self._say("Воспроизведение тестового звука", "Playing a test sound")
        ctx.spawn("speaker-test", "-c2", "-twav", "-l1")
        rc = ask_result(
            ctx, "10.4.1", "Проверка встроенного аудио", "_проверка_встроенного_аудио_при_наличии"
        )
        record_subresult(self.STEP_ID, "10.4.1", rc)
        statuses.append(rc)

        self._say("Говорите в микрофон 5 секунд", "Speak into the microphone for 5 seconds")
        if ctx.spawn("arecord", "-d", "5", "-f", "cd", "mic-test.wav") == 0:
            ctx.spawn("aplay", "mic-test.wav")
        Path("mic-test.wav").unlink(missing_ok=True)
        rc = ask_result(
            ctx,
            "10.4.2",
            "Проверка встроенного микрофона",
            "_проверка_встроенного_микрофона_при_наличии",
        )
        record_subresult(self.STEP_ID, "10.4.2", rc)
        statuses.append(rc)

        rc = ask_result(
            ctx, "10.4.3", "Проверка аудио портов", "_проверка_аудио_портов_при_наличии"
        )
        record_subresult(self.STEP_ID, "10.4.3", rc)
        statuses.append(rc)
        return overall_status(statuses)


@register_step
class WebcamStep(_GuiStep):
    STEP_ID = "webcam"
    number = "10.10.3"
    en_name = "Checking the built-in camera"
    ru_name = "Проверка встроенной камеры"
    flag = "webcam"

    def testcase(self) -> int:
        ctx = self.ctx
        app = next((a for a in ("kamoso", "cheese", "vlc") if ctx.has_binary(a)), "")
        proc = None
        if app:
            ctx.cmd_title(app)
            proc = subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rc = ask_result(
            ctx, self.number, self.ru_name, "_проверка_встроенной_камеры_при_наличии"
        )
        if proc and proc.poll() is None:
            proc.terminate()
        record_subresult(self.STEP_ID, "10.4.2.2", rc)
        return rc


@register_step
class BluetoothStep(_GuiStep):
    STEP_ID = "bluez"
    number = "10.10.10"
    en_name = "Checking Bluetooth"
    ru_name = "Проверка Bluetooth"
    flag = "bluez"

    def testcase(self) -> int:
        ctx = self.ctx
        report: list[str] = []
        active = _run_to(report, ["systemctl", "is-active", "bluetooth"])
        show = _run_to(report, ["bluetoothctl", "show"], timeout=15)
        Path("bluetooth.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        if (active.stdout or "").strip() != "active" or "Controller " not in (show.stdout or ""):
            ctx.spawn(": Bluetooth service or controller is not available")
            return TEST_FAILED
        return ask_result(ctx, self.number, self.ru_name, "_проверка_bluetooth_при_наличии")


@register_step
class FingerprintStep(StepBase):
    STEP_ID = "fprnt"
    number = "10.10.7"
    en_name = "Checking the fingerprint scanner"
    ru_name = "Проверка работы сканера отпечатка пальца"

    def pre(self) -> int:
        ctx = self.ctx
        if not ctx.fprnt_test or ctx.batchmode:
            return TEST_SKIPPED
        if not ctx.has_binary("fprintd-enroll"):
            return TEST_BLOCKED
        if not (sys.stdin.isatty() or graphical_session()):
            return TEST_BLOCKED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        user = ctx.username or os.environ.get("USER", "")
        ctx.spawn(": " + (
            "Прикладывайте палец к сканеру по запросу"
            if ctx.langid == "ru"
            else "Touch the scanner when asked"
        ))
        rc_e, enroll = _tee(["fprintd-enroll", user])
        rc_v, verify = _tee(["fprintd-verify", user])
        subprocess.run(["fprintd-delete", user], capture_output=True, check=False)
        Path("fprintd.txt").write_text(enroll + "\n" + verify, encoding="utf-8")
        ok = rc_e == 0 and "enroll-completed" in enroll and "verify-match" in verify
        return TEST_PASSED if ok and rc_v == 0 else TEST_FAILED


@register_step
class SmartcardStep(StepBase):
    STEP_ID = "scard"
    number = "10.10.12"
    en_name = "Checking the smart card slot"
    ru_name = "Проверка разъёма для смарт-карт"

    def pre(self) -> int:
        ctx = self.ctx
        if not ctx.scard_test or ctx.batchmode:
            return TEST_SKIPPED
        if not ctx.has_binary("pcsc_scan"):
            return TEST_BLOCKED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        if os.geteuid() == 0:
            ctx.spawn("systemctl", "start", "pcscd.socket", "pcscd.service")
        report: list[str] = []
        _run_to(report, ["lsusb"])
        readers = _run_to(report, ["pcsc_scan", "-r"], timeout=30)
        _run_to(report, ["opensc-tool", "--list-readers"], timeout=30)
        Path("smartcard.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        if readers.returncode != 0:
            return TEST_FAILED
        return ask_result(
            ctx, self.number, self.ru_name, "_проверка_разъёма_для_смарт_карт_при_наличии"
        )
