"""Hardware firmware update step."""

from __future__ import annotations

import os

from hw_test.constants import (
    TEST_ALLOWED,
    TEST_BLOCKED,
    TEST_FAILED,
    TEST_PASSED,
    TEST_SKIPPED,
)
from hw_test.steps.base import StepBase, register_step

# fwupdmgr: EXIT_NOTHING_TO_DO (нет устройств / нет обновлений)
FWUPD_NOTHING_TO_DO = 2


@register_step
class FwupdStep(StepBase):
    STEP_ID = "fwupd"
    number = "6"
    en_name = "Checking the ability to hardware components firmware updating"
    ru_name = "Проверка возможности обновления прошивки компонентов оборудования"

    def pre(self) -> int:
        ctx = self.ctx
        if not ctx.fwupd_test:
            return TEST_SKIPPED
        if not ctx.has_binary("fwupdmgr"):
            return TEST_BLOCKED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        if ctx.username and ctx.langid != "en":
            os.environ["LANG"] = "C"
            os.environ["LC_ALL"] = "C"

        # Методика, раздел 6: отсутствие поддерживаемых устройств — ошибка,
        # отсутствие обновлений для них — норма.
        print("===[ Devices list:")
        rc = ctx.spawn("fwupdmgr", "get-devices")
        print("===]\n")
        if rc == FWUPD_NOTHING_TO_DO:
            ctx.spawn(": No devices supporting firmware update")
            return TEST_FAILED
        if rc != 0:
            return TEST_BLOCKED

        print("===[ Updates list:")
        rc = ctx.spawn("fwupdmgr", "get-updates", "-y")
        print("===]\n")
        if rc == FWUPD_NOTHING_TO_DO:
            ctx.spawn(": No firmware updates available")
            return TEST_PASSED
        if rc != 0:
            return TEST_BLOCKED

        print("===[ Update process:")
        rc = TEST_PASSED if ctx.spawn("fwupdmgr", "update", "-y") == 0 else TEST_FAILED
        print("===]\n")
        if ctx.have_systemd:
            ctx.stop_journald()
        ctx.system_restart(rc)
        return rc
