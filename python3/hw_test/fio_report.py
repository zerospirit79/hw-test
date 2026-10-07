"""Summary table of fio results (methodology 11.1.8)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# Порядок строк таблицы, как в примере протокола (раздел 12.5)
FIO_TESTS = ("rndw-4k", "rndw-64k", "rndw-1m", "seqw-1m", "seqr-1m")

_CLAT_RE = re.compile(r"^\s+clat \((?P<unit>[num]sec)\):.*?\bavg=\s*(?P<avg>[\d.]+)", re.M)
_BW_RE = re.compile(r"^\s+bw \(\s*(?P<unit>[KMG]i?B/s)\):.*?\bavg=\s*(?P<avg>[\d.]+)", re.M)
_IOPS_RE = re.compile(r"^\s+iops\s*:.*?\bavg=\s*(?P<avg>[\d.]+)", re.M)
_CPU_RE = re.compile(
    r"^\s+cpu\s*:\s*usr=(?P<usr>[\d.]+)%,\s*sys=(?P<sys>[\d.]+)%,\s*ctx=(?P<ctx>\d+)", re.M
)

_CLAT_TO_USEC = {"nsec": 0.001, "usec": 1.0, "msec": 1000.0}
_BW_TO_MIB = {
    "KiB/s": 1 / 1024,
    "MiB/s": 1.0,
    "GiB/s": 1024.0,
    "KB/s": 1000 / 1048576,
    "MB/s": 1000000 / 1048576,
    "GB/s": 1000000000 / 1048576,
}


@dataclass
class FioResult:
    test: str
    iops: float
    bw_mib: float
    clat_usec: float
    cpu_usr: float
    cpu_sys: float
    cpu_ctx: int


def parse_fio_log(test: str, text: str) -> Optional[FioResult]:
    """Extract average IOPS, bandwidth, completion latency and CPU load."""
    clat = _CLAT_RE.search(text)
    bw = _BW_RE.search(text)
    iops = _IOPS_RE.search(text)
    cpu = _CPU_RE.search(text)
    if not (clat and bw and iops and cpu):
        return None
    return FioResult(
        test=test,
        iops=float(iops.group("avg")),
        bw_mib=float(bw.group("avg")) * _BW_TO_MIB[bw.group("unit")],
        clat_usec=float(clat.group("avg")) * _CLAT_TO_USEC[clat.group("unit")],
        cpu_usr=float(cpu.group("usr")),
        cpu_sys=float(cpu.group("sys")),
        cpu_ctx=int(cpu.group("ctx")),
    )


def collect_fio_results(workdir: Path) -> dict[str, list[FioResult]]:
    """Map ``fio-<dev>`` directories to parsed results in methodology order."""
    out: dict[str, list[FioResult]] = {}
    for devdir in sorted(Path(workdir).glob("fio-*")):
        if not devdir.is_dir():
            continue
        rows = []
        for test in FIO_TESTS:
            log = devdir / f"{test}.log"
            if not log.is_file():
                continue
            res = parse_fio_log(test, log.read_text(encoding="utf-8", errors="replace"))
            if res:
                rows.append(res)
        if rows:
            out[devdir.name[len("fio-") :]] = rows
    return out


def format_fio_table(rows: Iterable[FioResult]) -> list[str]:
    """Markdown table: Test | IOPs | BW (MiB/s) | clat (usec) | CPU usr | CPU sys | CPU ctx."""
    lines = [
        "| Test | IOPs | BW (MiB/s) | clat (usec) | CPU usr | CPU sys | CPU ctx |",
        "|---|--:|--:|--:|--:|--:|--:|",
    ]
    for r in rows:
        lines.append(
            f"| {r.test} | {r.iops:,.2f} | {r.bw_mib:,.2f} | {r.clat_usec:,.2f} "
            f"| {r.cpu_usr:.2f}% | {r.cpu_sys:.2f}% | {r.cpu_ctx:,} |"
        )
    return lines
