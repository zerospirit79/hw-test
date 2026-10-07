"""Checks aligned with the testing methodology (sections 6, 9, 10.1, 10.11, 11.2)."""

from __future__ import annotations

import gzip
import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from hw_test.constants import TEST_BLOCKED, TEST_FAILED, TEST_PASSED
from hw_test.log_analysis import analyze_collected_logs, dmesg_delta
from hw_test.steps import cpupower, express, glmark
from hw_test.steps.fwupd import FwupdStep


class FakeCtx(SimpleNamespace):
    def __init__(self, codes: dict[str, int]) -> None:
        super().__init__(username="", langid="en", have_systemd=False)
        self.codes = codes
        self.calls: list[tuple[str, ...]] = []
        self.restarted: int | None = None

    def spawn(self, *args: str) -> int:
        if len(args) == 1 and args[0].startswith(": "):
            return 0
        self.calls.append(args)
        return self.codes.get(args[1], 0)

    def system_restart(self, rc: int) -> None:
        self.restarted = rc


class FwupdStepTests(unittest.TestCase):
    def run_step(self, **codes: int) -> tuple[int, FakeCtx]:
        ctx = FakeCtx({k.replace("_", "-"): v for k, v in codes.items()})
        return FwupdStep(ctx=ctx).testcase(), ctx

    def test_no_supported_devices_is_failure(self) -> None:
        rc, ctx = self.run_step(get_devices=2)
        self.assertEqual(rc, TEST_FAILED)
        self.assertIsNone(ctx.restarted)

    def test_no_updates_is_normal(self) -> None:
        rc, ctx = self.run_step(get_updates=2)
        self.assertEqual(rc, TEST_PASSED)
        self.assertNotIn("update", [c[1] for c in ctx.calls])
        self.assertIsNone(ctx.restarted)

    def test_other_errors_block(self) -> None:
        self.assertEqual(self.run_step(get_devices=1)[0], TEST_BLOCKED)
        self.assertEqual(self.run_step(get_updates=1)[0], TEST_BLOCKED)

    def test_update_reboots(self) -> None:
        rc, ctx = self.run_step()
        self.assertEqual(rc, TEST_PASSED)
        self.assertEqual(ctx.restarted, TEST_PASSED)
        rc, ctx = self.run_step(update=1)
        self.assertEqual(rc, TEST_FAILED)
        self.assertEqual(ctx.restarted, TEST_FAILED)


class GlmarkHelpersTests(unittest.TestCase):
    def test_hardware_renderer(self) -> None:
        text = "direct rendering: Yes\nOpenGL renderer string: Mesa Intel(R) UHD Graphics 620\n"
        self.assertTrue(glmark.has_3d_acceleration(text))

    def test_software_renderer(self) -> None:
        text = "direct rendering: Yes\nOpenGL renderer string: llvmpipe (LLVM 17, 256 bits)\n"
        self.assertFalse(glmark.has_3d_acceleration(text))
        self.assertFalse(glmark.has_3d_acceleration("direct rendering: No\n"))

    def test_score(self) -> None:
        self.assertEqual(glmark.parse_glmark_score("...\n    glmark2 Score: 1171 \n"), 1171)
        self.assertIsNone(glmark.parse_glmark_score("Error: main: Could not initialize"))


class DmesgDeltaTests(unittest.TestCase):
    def test_only_new_lines(self) -> None:
        before = "[ 1.0] a\n[ 2.0] b"
        after = before + "\n[ 3.0] BUG: soft lockup\n[ 4.0] c"
        delta = dmesg_delta(before, after)
        self.assertEqual(delta, "[ 3.0] BUG: soft lockup\n[ 4.0] c")
        report = analyze_collected_logs(dmesg=delta)
        self.assertTrue(any(f.severity == "critical" for f in report.findings))


class CpuThresholdTests(unittest.TestCase):
    def test_all_core_threshold_is_midpoint(self) -> None:
        self.assertEqual(cpupower._all_core_threshold("3500000", "400000"), 1950000)


class ExpressHelpersTests(unittest.TestCase):
    def test_swap_fits_ram(self) -> None:
        self.assertTrue(express.swap_fits_ram("MemTotal: 8000000 kB\nSwapTotal: 7900000 kB\n"))
        self.assertFalse(express.swap_fits_ram("MemTotal: 8000000 kB\nSwapTotal: 2000000 kB\n"))
        self.assertFalse(express.swap_fits_ram("MemTotal: 8000000 kB\nSwapTotal: 0 kB\n"))

    def test_save_dmesg_gz_never_prompts(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "dmesg":
                return subprocess.CompletedProcess(cmd, 1, b"", b"")
            return subprocess.CompletedProcess(cmd, 0, b"kernel line\n", b"")

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "s.dmesg.gz")
            with mock.patch.object(express.subprocess, "run", side_effect=fake_run):
                self.assertTrue(express.save_dmesg_gz(path))
            with gzip.open(path, "rb") as gz:
                self.assertEqual(gz.read(), b"kernel line\n")
        self.assertEqual(calls[1][:2], ["sudo", "-n"])

    def test_volume_steps_follow_methodology(self) -> None:
        self.assertEqual(express.VOLUME_STEPS["settings"], (75, 25))
        self.assertEqual(express.VOLUME_STEPS["hibernate"], (100, 50))
        self.assertEqual(express.VOLUME_STEPS["suspend"], (75, 25))


if __name__ == "__main__":
    unittest.main()
