"""NUMA step (methodology 10.8).

Instead of unpacking the installer squashfs, a memory stressor is bound
to every node in turn with numactl; the verdict comes from the CPU affinity
and the per-node page counts of the running process (/proc/PID/numa_maps).
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from hw_test.constants import TEST_ALLOWED, TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.manual import record_subresult
from hw_test.steps.base import StepBase, register_step

SYS_NODES = Path("/sys/devices/system/node")
LOCAL_SHARE = 0.9  # доля страниц процесса, которая должна быть на заданном узле


def parse_cpulist(text: str) -> set[int]:
    cpus: set[int] = set()
    for part in text.strip().split(","):
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            cpus.update(range(int(lo), int(hi) + 1))
        else:
            cpus.add(int(part))
    return cpus


def numa_nodes(sys_nodes: Path = SYS_NODES) -> dict[int, set[int]]:
    """Nodes that have CPUs: {node: cpus}."""
    out: dict[int, set[int]] = {}
    if not sys_nodes.is_dir():
        return out
    for node in sys_nodes.glob("node[0-9]*"):
        cpulist = node / "cpulist"
        cpus = parse_cpulist(cpulist.read_text()) if cpulist.is_file() else set()
        if cpus:
            out[int(node.name[4:])] = cpus
    return dict(sorted(out.items()))


def numa_maps_pages(text: str) -> dict[int, int]:
    """Sum the N<node>=<pages> counters of /proc/PID/numa_maps."""
    pages: dict[int, int] = {}
    for node, count in re.findall(r"\bN(\d+)=(\d+)", text):
        pages[int(node)] = pages.get(int(node), 0) + int(count)
    return pages


def _descendants(pid: int) -> list[int]:
    children: dict[int, list[int]] = {}
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        children.setdefault(int(fields[1]), []).append(int(stat.parent.name))
    out, todo = [], [pid]
    while todo:
        cur = todo.pop()
        out.append(cur)
        todo.extend(children.get(cur, []))
    return out


def _read(path: str) -> str:
    try:
        return Path(path).read_text()
    except OSError:
        return ""


@register_step
class NumaStep(StepBase):
    STEP_ID = "numa"
    number = "10.8"
    en_name = "Checking NUMA"
    ru_name = "Проверка NUMA"

    def pre(self) -> int:
        ctx = self.ctx
        if not ctx.numa_test:
            return TEST_SKIPPED
        if not (ctx.has_binary("numactl") and ctx.has_binary("stress-ng")):
            return TEST_BLOCKED
        if len(numa_nodes()) < 2:
            ctx.spawn(": Less than two NUMA nodes, enable NUMA in BIOS/UEFI")
            return TEST_SKIPPED
        return TEST_ALLOWED

    def testcase(self) -> int:
        ctx = self.ctx
        if ctx.username and ctx.langid != "en":
            os.environ["LANG"] = "C"
            os.environ["LC_ALL"] = "C"
        report = []
        for cmd in (["numactl", "-H"], ["numastat"]):
            if not ctx.has_binary(cmd[0]):
                continue
            proc = subprocess.run(cmd, capture_output=True, text=True)
            report += [f"# {' '.join(cmd)}", (proc.stdout or "").rstrip()]
        rc = TEST_PASSED
        for node, cpus in numa_nodes().items():
            ok = self._run_on_node(node, cpus, report)
            sub = "10.8.2" if node == 0 else "10.8.3" if node == 1 else f"10.8.{node + 2}"
            record_subresult(self.STEP_ID, sub, TEST_PASSED if ok else TEST_FAILED)
            if not ok:
                rc = TEST_FAILED
        record_subresult(self.STEP_ID, "10.8.1", rc)
        Path("numa.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        return rc

    def _run_on_node(self, node: int, cpus: set[int], report: list[str]) -> bool:
        ctx = self.ctx
        cmd = [
            "numactl",
            f"--cpunodebind={node}",
            f"--membind={node}",
            "stress-ng",
            "--vm",
            "1",
            "--vm-bytes",
            "256M",
            "--vm-keep",
            "--timeout",
            "20s",
        ]
        ctx.cmd_title(" ".join(cmd))
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(8)
        best_pid, best = 0, {}
        for pid in _descendants(proc.pid):
            pages = numa_maps_pages(_read(f"/proc/{pid}/numa_maps"))
            if sum(pages.values()) > sum(best.values()):
                best_pid, best = pid, pages
        allowed = set()
        if best_pid:
            m = re.search(r"^Cpus_allowed_list:\s*(\S+)", _read(f"/proc/{best_pid}/status"), re.M)
            allowed = parse_cpulist(m.group(1)) if m else set()
            if ctx.has_binary("numastat"):
                stat = subprocess.run(
                    ["numastat", "-p", str(best_pid)], capture_output=True, text=True
                )
                report += [
                    f"# numastat -p {best_pid}  (node {node})",
                    (stat.stdout or "").rstrip(),
                ]
        proc.wait()
        total = sum(best.values())
        share = best.get(node, 0) / total if total else 0.0
        ok = bool(allowed) and allowed <= cpus and share >= LOCAL_SHARE
        line = (
            f"node {node}: pages on node {share:.0%}, "
            f"CPUs allowed {sorted(allowed)[:8]}{'...' if len(allowed) > 8 else ''}, "
            f"{'OK' if ok else 'FAIL'}"
        )
        report.append(line)
        ctx.spawn(f": {line}")
        return ok
