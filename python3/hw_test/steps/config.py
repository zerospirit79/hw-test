"""Test plan configuration step."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED, TEST_SKIPPED
from hw_test.context import graphical_session
from hw_test.de_terminal import apply_graphical_session_env
from hw_test.gui import config_forms
from hw_test.steps.base import StepBase, register_step


@register_step
class ConfigStep(StepBase):
    STEP_ID = "config"
    number = "5.4"
    en_name = "Defining a Test Plan"
    ru_name = "Определение плана тестирования"

    def pre(self) -> int:
        ctx = self.ctx
        if ctx.batchmode and not sys.stdin.isatty() and not graphical_session():
            return TEST_SKIPPED
        if not graphical_session() and not sys.stdin.isatty():
            return TEST_ALLOWED
        if os.geteuid() != 0:
            apply_graphical_session_env()
        if graphical_session() and ctx.has_binary("yad"):
            return TEST_ALLOWED
        if sys.stdin.isatty():
            return TEST_ALLOWED
        return TEST_BLOCKED

    def testcase(self) -> int:
        ctx = self.ctx
        if not graphical_session() and not sys.stdin.isatty():
            from hw_test.de_terminal import spawn_continue_on_vt

            user = ctx.username or os.environ.get("LOGNAME") or os.environ.get("USER", "")
            if user and spawn_continue_on_vt(user, ctx.progname):
                ini = Path(ctx.workdir) / "STATE" / "settings.ini"
                if ini.is_file():
                    ctx.print_settings_ini("config.ini")
                raise SystemExit(0)
            return TEST_BLOCKED
        if os.geteuid() != 0:
            apply_graphical_session_env()
        wconf = False
        if graphical_session() and ctx.has_binary("yad"):
            config_forms.run_gui(ctx)
            wconf = True
        elif sys.stdin.isatty():
            can_install_mate = bool(
                ctx.have_altsp
                and not ctx.have_xorg
                and ctx.distro == "SRV"
                and ctx.repo in ("c10f1", "c10f2")
            )
            config_forms.run_tui(ctx, can_install_mate=can_install_mate)
            wconf = True
        if wconf:
            ctx.print_settings_ini("config.ini")
            return TEST_ALLOWED
        return TEST_BLOCKED
