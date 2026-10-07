"""Network subsystem step (methodology 10.2.1-10.2.3)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from hw_test.constants import (
    TEST_ALLOWED,
    TEST_BLOCKED,
    TEST_FAILED,
    TEST_PASSED,
    TEST_SKIPPED,
)
from hw_test.manual import overall_status, record_subresult
from hw_test.steps.base import StepBase, register_step

SYS_NET = Path("/sys/class/net")
IB_MODULES = (
    "ib_ipoib",
    "rdma_ucm",
    "ib_uverbs",
    "ib_umad",
    "rdma_cm",
    "ib_cm",
    "ib_mad",
    "iw_cm",
)


def physical_ifaces(sys_net: Path = SYS_NET) -> list[tuple[str, str]]:
    """(name, kind) for interfaces backed by a device; kind is 'wifi' or 'eth'."""
    out = []
    if not sys_net.is_dir():
        return out
    for iface in sorted(sys_net.iterdir()):
        if not (iface / "device").exists():
            continue
        if (iface / "type").is_file() and (iface / "type").read_text().strip() == "32":
            continue  # IPoIB is checked separately (10.2.3)
        wifi = (iface / "wireless").exists() or (iface / "phy80211").exists()
        out.append((iface.name, "wifi" if wifi else "eth"))
    return out


def ping_ok(output: str) -> bool:
    return bool(re.search(r"\b0% packet loss", output))


def ibv_has_devices(output: str) -> bool:
    """ibv_devices prints a header and a dashed line before device rows."""
    rows = [ln for ln in output.splitlines() if ln.strip() and not set(ln.strip()) <= set("- \t")]
    return len(rows) > 1


@register_step
class NetworkStep(StepBase):
    STEP_ID = "network"
    number = "10.2"
    en_name = "Checking the network subsystem"
    ru_name = "Проверка сетевой подсистемы"

    def pre(self) -> int:
        if not self.ctx.ifaces and not self.ctx.infb_test:
            return TEST_SKIPPED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        if ctx.username and ctx.langid != "en":
            os.environ["LANG"] = "C"
            os.environ["LC_ALL"] = "C"
        report: list[str] = []
        per_kind: dict[str, list[int]] = {"eth": [], "wifi": []}

        for name, kind in physical_ifaces():
            rc = self._check_iface(name, report)
            if rc is not None:
                per_kind[kind].append(rc)
        statuses = []
        for kind, number in (("eth", "10.2.1"), ("wifi", "10.2.2")):
            rc = overall_status(per_kind[kind])
            record_subresult(self.STEP_ID, number, rc)
            statuses.append(rc)

        if ctx.infb_test:
            rc = self._check_infiniband(report)
            record_subresult(self.STEP_ID, "10.2.3", rc)
            statuses.append(rc)

        Path("network.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return overall_status(statuses)

    def _check_iface(self, name: str, report: list[str]) -> int | None:
        """PASSED/FAILED for a connected interface, None when there is no link."""
        ctx = self.ctx
        oper = (SYS_NET / name / "operstate").read_text().strip()
        addr = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", name], capture_output=True, text=True
        ).stdout
        report += [f"# ip -4 addr show dev {name}  (operstate: {oper})", addr.rstrip()]
        if oper != "up":
            ctx.spawn(f": {name}: no link, skipped")
            return None
        if " inet " not in addr:
            ctx.spawn(f": {name}: no IPv4 address")
            return TEST_FAILED
        # Вторая попытка: первый пакет по Wi-Fi часто теряется при выходе из энергосбережения
        for _attempt in range(2):
            proc = subprocess.run(
                ["ping", "-4", "-c", "3", "-W", "5", "-I", name, "--", ctx.ping_server or "ya.ru"],
                capture_output=True,
                text=True,
            )
            report += [
                f"# ping -4 -c 3 -I {name} {ctx.ping_server}",
                (proc.stdout or proc.stderr).rstrip(),
            ]
            ok = proc.returncode == 0 and ping_ok(proc.stdout or "")
            if ok:
                break
        ctx.spawn(f": {name}: {'0% packet loss' if ok else 'ping failed'}")
        return TEST_PASSED if ok else TEST_FAILED

    def _check_infiniband(self, report: list[str]) -> int:
        ctx = self.ctx
        if not ctx.has_binary("ibv_devices"):
            return TEST_BLOCKED
        ctx.spawn("modprobe", "-a", *IB_MODULES)
        proc = subprocess.run(["ibv_devices"], capture_output=True, text=True)
        report += ["# ibv_devices", (proc.stdout or proc.stderr).rstrip()]
        return TEST_PASSED if ibv_has_devices(proc.stdout or "") else TEST_FAILED
