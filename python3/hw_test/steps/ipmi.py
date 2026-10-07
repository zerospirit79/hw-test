"""IPMI step (methodology 10.9), in-band and non-destructive only.

Power off/on/reset, one-time boot to BIOS and password change from
section 10.9.1 stay manual: they need a remote host and change the BMC state.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.steps.base import StepBase, register_step

IPMI_MODULES = ("ipmi_msghandler", "ipmi_devintf", "ipmi_si")
# (команда, обязательна ли для PASSED)
IPMI_COMMANDS = (
    (["mc", "info"], True),
    (["chassis", "status"], True),
    (["sensor"], True),
    (["user", "list", "1"], False),
)


def has_ipmi_device(dev: Path = Path("/dev")) -> bool:
    return any(dev.glob("ipmi[0-9]*")) or (dev / "ipmi" / "0").exists()


@register_step
class IpmiStep(StepBase):
    STEP_ID = "ipmi"
    number = "10.9"
    en_name = "Checking IPMI"
    ru_name = "Проверка IPMI"

    def pre(self) -> int:
        ctx = self.ctx
        if not ctx.ipmi_test:
            return TEST_SKIPPED
        if not ctx.has_binary("ipmitool"):
            return TEST_BLOCKED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        if ctx.username and ctx.langid != "en":
            os.environ["LANG"] = "C"
            os.environ["LC_ALL"] = "C"
        ctx.spawn("modprobe", "-a", *IPMI_MODULES)
        if not has_ipmi_device():
            ctx.spawn(": No /dev/ipmi* device: BMC is not available from the OS")
            return TEST_BLOCKED
        report = []
        rc = TEST_PASSED
        for args, required in IPMI_COMMANDS:
            cmd = ["ipmitool", *args]
            ctx.cmd_title(" ".join(cmd))
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                report.append(f"# {' '.join(cmd)}  (timeout)")
                if required:
                    rc = TEST_FAILED
                continue
            report += [
                f"# {' '.join(cmd)}  (exit {proc.returncode})",
                (proc.stdout or proc.stderr).rstrip(),
            ]
            if required and proc.returncode != 0:
                rc = TEST_FAILED
        report.append(
            "# 10.9.1: power off/on/reset, bootdev bios and password change "
            "are not run automatically (remote, state-changing)"
        )
        Path("ipmi.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return rc
