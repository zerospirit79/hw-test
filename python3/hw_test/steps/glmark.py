"""Graphics performance step."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.context import graphical_session
from hw_test.log_analysis import analyze_collected_logs, dmesg_delta, read_dmesg
from hw_test.steps.base import StepBase, register_step

SOFTWARE_RENDERERS = ("llvmpipe", "softpipe", "swrast", "software rasterizer")
SCORE_RE = re.compile(r"glmark2 Score:\s*(\d+)")


def has_3d_acceleration(glxinfo: str) -> bool:
    """Methodology 8.3.5 / 11.2: direct rendering on a hardware renderer."""
    if not re.search(r"^direct rendering:\s*Yes", glxinfo, re.M):
        return False
    m = re.search(r"^OpenGL renderer string:\s*(.*)$", glxinfo, re.M)
    renderer = (m.group(1) if m else "").lower()
    return not any(sw in renderer for sw in SOFTWARE_RENDERERS)


def parse_glmark_score(log: str) -> int | None:
    m = SCORE_RE.search(log)
    return int(m.group(1)) if m else None


@register_step
class GlmarkStep(StepBase):
    STEP_ID = "glmark"
    number = "11.2"
    en_name = "Checking 2D/3D-Video performance"
    ru_name = "Определение производительности видеоподсистемы"

    def pre(self) -> int:
        if not self.ctx.v3d_test:
            return TEST_SKIPPED
        if not graphical_session():
            return TEST_SKIPPED
        glxinfo = Path("glxinfo.txt")
        text = glxinfo.read_text(errors="replace") if glxinfo.is_file() else ""
        # Пустой glxinfo.txt (нет доступа к дисплею из-под root) — не повод блокировать
        if "direct rendering:" in text and not has_3d_acceleration(text):
            self.ctx.spawn(": No hardware 3D acceleration (see glxinfo.txt)")
            return TEST_BLOCKED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        dmesg_before = read_dmesg()
        ctx.cmd_title("glmark2")
        proc = subprocess.run(
            ["glmark2"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
        )
        log = proc.stdout or ""
        Path("glmark2.log").write_text(log, encoding="utf-8")

        score = parse_glmark_score(log)
        ctx.spawn(f": glmark2 exit code: {proc.returncode}, score: {score}")
        if proc.returncode != 0 or score is None:
            return TEST_FAILED

        report = analyze_collected_logs(dmesg=dmesg_delta(dmesg_before, read_dmesg()))
        if any(f.severity == "critical" for f in report.findings):
            ctx.spawn(": Critical kernel messages during glmark2")
            return TEST_FAILED
        return TEST_PASSED
