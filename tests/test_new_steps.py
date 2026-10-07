"""Steps for methodology 10.2, 10.4, 10.6.2, 10.8, 10.9, 10.10.x (ALT #53400)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from hw_test.constants import TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.manual import overall_status, record_subresult
from hw_test.protocol import build_rows
from hw_test.steps import list_steps, network, numa, power
from hw_test.steps.ipmi import has_ipmi_device

ROOT = Path(__file__).resolve().parents[1]


class InTmpDir(unittest.TestCase):
    def setUp(self) -> None:
        self._old = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        os.chdir(self.tmp)

    def tearDown(self) -> None:
        os.chdir(self._old)
        self._tmp.cleanup()


class PlanTests(unittest.TestCase):
    def test_plan_and_numbers_reference_registered_steps(self) -> None:
        steps = set(list_steps())
        for name in ("start.txt", "finish.txt", "numbers.txt"):
            for line in (ROOT / "var/lib/hw-test" / name).read_text().splitlines():
                if line.strip():
                    self.assertIn(line.split("\t")[-1], steps, f"{name}: {line}")


class ManualTests(InTmpDir):
    def test_record_subresult_replaces(self) -> None:
        record_subresult("x", "10.2.1", TEST_FAILED)
        record_subresult("x", "10.2.2", TEST_SKIPPED)
        record_subresult("x", "10.2.1", TEST_PASSED)
        self.assertEqual(
            Path("results-x.txt").read_text().splitlines(), ["10.2.2\tSKIPPED", "10.2.1\tPASSED"]
        )

    def test_overall_status(self) -> None:
        self.assertEqual(overall_status([TEST_PASSED, TEST_FAILED]), TEST_FAILED)
        self.assertEqual(overall_status([TEST_SKIPPED, TEST_PASSED]), TEST_PASSED)
        self.assertEqual(overall_status([TEST_SKIPPED, TEST_BLOCKED]), TEST_BLOCKED)
        self.assertEqual(overall_status([]), TEST_SKIPPED)

    def test_protocol_uses_subresults_with_parent(self) -> None:
        Path("results-sound.txt").write_text("10.4.1\tPASSED\n10.4.2\tFAILED\n")
        Path("results-power.txt").write_text("10.6.2.3\tSKIPPED\n")
        rows = {r.number: r.status for r in build_rows(self.tmp)}
        self.assertEqual(rows["10.4.1.3"], "PASSED")
        self.assertEqual(rows["10.4.2.1"], "FAILED")
        self.assertEqual(rows["10.6.2.3"], "SKIPPED")
        self.assertEqual(rows["10.6.2.4"], "")


class NetworkTests(InTmpDir):
    def test_physical_ifaces(self) -> None:
        net = self.tmp / "net"
        for name, extra in (("lo", None), ("enp1s0", None), ("wlp2s0", "wireless"), ("ib0", None)):
            d = net / name
            d.mkdir(parents=True)
            if name != "lo":
                (d / "device").mkdir()
            if extra:
                (d / extra).mkdir()
            (d / "type").write_text("32\n" if name == "ib0" else "1\n")
        self.assertEqual(
            network.physical_ifaces(net), [("enp1s0", "eth"), ("wlp2s0", "wifi")]
        )

    def test_ping_and_ibv(self) -> None:
        self.assertTrue(network.ping_ok("3 packets transmitted, 3 received, 0% packet loss"))
        self.assertFalse(network.ping_ok("3 packets transmitted, 0 received, 100% packet loss"))
        self.assertFalse(network.ibv_has_devices("    device\t\t node GUID\n    ------\t\t----\n"))
        self.assertTrue(
            network.ibv_has_devices(
                "    device\t\t node GUID\n    ------\t\t----\n    mlx4_0\t248a07030069dfa0\n"
            )
        )


class NumaTests(InTmpDir):
    def test_cpulist(self) -> None:
        self.assertEqual(numa.parse_cpulist("0-2,8,10-11\n"), {0, 1, 2, 8, 10, 11})

    def test_numa_maps_pages(self) -> None:
        text = (
            "7f00 default anon=10 dirty=10 N0=6 N1=4 kernelpagesize_kB=4\n"
            "7f10 bind:1 anon=65536 N1=65536 kernelpagesize_kB=4\n"
        )
        self.assertEqual(numa.numa_maps_pages(text), {0: 6, 1: 65540})

    def test_nodes_without_cpus_are_ignored(self) -> None:
        for n, cpus in ((0, "0-3"), (1, "4-7"), (2, "")):
            d = self.tmp / f"node{n}"
            d.mkdir()
            (d / "cpulist").write_text(cpus + "\n")
        self.assertEqual(numa.numa_nodes(self.tmp), {0: {0, 1, 2, 3}, 1: {4, 5, 6, 7}})


class IpmiTests(InTmpDir):
    def test_has_ipmi_device(self) -> None:
        self.assertFalse(has_ipmi_device(self.tmp))
        (self.tmp / "ipmi0").write_text("")
        self.assertTrue(has_ipmi_device(self.tmp))


class PowerTests(InTmpDir):
    def make_power(self, state: str, disk: str = "[disabled]\n") -> Path:
        d = self.tmp / "power"
        d.mkdir()
        (d / "state").write_text(state)
        (d / "disk").write_text(disk)
        return d

    def test_sleep_supported(self) -> None:
        d = self.make_power("freeze mem\n")
        self.assertEqual(power.sleep_supported("suspend", d), (True, ""))
        ok, reason = power.sleep_supported("hibernate", d)
        self.assertFalse(ok)
        self.assertIn("lockdown", reason)

    def test_hibernate_needs_swap(self) -> None:
        d = self.make_power("freeze mem disk\n", "[platform] shutdown reboot\n")
        with mock.patch.object(power, "swap_fits_ram", return_value=False):
            ok, reason = power.sleep_supported("hibernate", d)
            self.assertEqual((ok, reason), (False, "SWAP is smaller than RAM"))
        with mock.patch.object(power, "swap_fits_ram", return_value=True):
            self.assertEqual(power.sleep_supported("hibernate", d), (True, ""))

    def ctx(self) -> SimpleNamespace:
        return SimpleNamespace(
            power_test="1",
            have_systemd="1",
            langid="en",
            spawn=mock.Mock(return_value=0),
            chown_workdir_for_user=mock.Mock(),
            has_binary=lambda name: True,
        )

    def test_resume_after_reboot_and_poweroff(self) -> None:
        """Re-entry after boot: markers turn reboot/poweroff into PASSED."""
        Path(power.STEP_FILE).write_text("2\n")
        Path("PWR-REBOOT-STARTED").write_text("started\n")
        step = power.PowerStep(ctx=self.ctx())
        with mock.patch.object(step, "_restart", wraps=step._restart) as restart, mock.patch(
            "hw_test.resume_autorun.setup_resume_autorun"
        ), mock.patch.object(power.time, "sleep"), mock.patch.object(power.subprocess, "run"):
            with self.assertRaises(SystemExit):
                step.testcase()
            self.assertEqual(restart.call_count, 2)
        self.assertEqual(Path(power.STEP_FILE).read_text(), "3\n")
        self.assertTrue(Path("PWR-POWEROFF-STARTED").is_file())
        self.assertIn("10.6.2.2\tPASSED", Path("results-power.txt").read_text())

        # После включения компьютера шаг продолжается и завершается
        step = power.PowerStep(ctx=self.ctx())
        self.assertEqual(step.testcase(), TEST_PASSED)
        self.assertFalse(Path(power.STEP_FILE).exists())
        self.assertIn("10.6.2.1\tPASSED", Path("results-power.txt").read_text())

    def test_sleep_marker_after_boot_is_failure(self) -> None:
        Path("PWR-HIBERNATE-STARTED").write_text("started\n")
        step = power.PowerStep(ctx=self.ctx())
        self.assertEqual(step._sleep("hibernate"), TEST_FAILED)
        self.assertFalse(Path("PWR-HIBERNATE-STARTED").exists())

    def test_sleep_detects_gap(self) -> None:
        step = power.PowerStep(ctx=self.ctx())
        patches = (
            mock.patch.object(power, "sleep_supported", return_value=(True, "")),
            mock.patch.object(step, "_set_alarm", return_value=True),
            mock.patch.object(power.subprocess, "run"),
            mock.patch.object(power, "slept_seconds", side_effect=[0.0, 0.5, 31.0]),
            mock.patch.object(power.time, "sleep"),
        )
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.assertEqual(step._sleep("suspend"), TEST_PASSED)
        with mock.patch.object(power, "sleep_supported", return_value=(False, "no")):
            self.assertEqual(step._sleep("suspend"), TEST_SKIPPED)


if __name__ == "__main__":
    unittest.main()
