"""Draft of the testing protocol (methodology sections 2, 12.4 and 12.5).

Builds a title page and the main table with every methodology item.
Automated steps get their status from STATE/RESULTS; manual items stay
empty for the tester. Output: protocol.md and protocol.html in the workdir.
"""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from hw_test.constants import TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.fio_report import collect_fio_results, format_fio_table

METHODOLOGY_VERSION = "2.1 от 19.09.2023"
TO_FILL = "<заполнить>"

STATUS_NAMES = {
    TEST_PASSED: "PASSED",
    TEST_FAILED: "FAILED",
    TEST_SKIPPED: "SKIPPED",
    TEST_BLOCKED: "BLOCKED",
}

SECUREBOOT_VAR = Path(
    "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
)
KERNEL_WORKAROUNDS = ("pcie_aspm=off", "pci=nomsi", "pci=noaer")


@dataclass
class Item:
    number: str
    title: str
    step: str = ""
    evidence: Optional[Callable[[Path], list[str]]] = None


@dataclass
class Row:
    number: str
    title: str
    status: str = ""
    evidence: list[str] = field(default_factory=list)
    comment: str = ""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _file_evidence(name: str, header: str = "") -> Callable[[Path], list[str]]:
    def get(wd: Path) -> list[str]:
        text = _read(wd / name).strip()
        if not text:
            return []
        return ([header] if header else []) + text.splitlines()

    return get


def _grep_evidence(name: str, pattern: str, header: str = "") -> Callable[[Path], list[str]]:
    def get(wd: Path) -> list[str]:
        lines = [ln for ln in _read(wd / name).splitlines() if re.search(pattern, ln)]
        return ([header] if header and lines else []) + lines

    return get


def _hdparm_evidence(wd: Path) -> list[str]:
    out = []
    for f in sorted(wd.glob("hdparm-*.txt")):
        for ln in _read(f).splitlines():
            if "Timing" in ln:
                out.append(f"/dev/{f.stem[len('hdparm-') :]}: {ln.strip()}")
    return out


def _fio_evidence(wd: Path) -> list[str]:
    out = []
    for dev, rows in collect_fio_results(wd).items():
        out += [f"/dev/{dev}:", "", *format_fio_table(rows), ""]
    return out


ITEMS: tuple[Item, ...] = (
    Item("3", "Проверка режимов загрузки системы"),
    Item("3.2", "Загрузка средствами IPMI"),
    Item("3.3.1", "Установка ОС в режиме загрузки UEFI"),
    Item("3.3.2", "Восстановление ОС в режиме загрузки UEFI"),
    Item("3.3.3", "Установка ОС в режиме загрузки Legacy/CSM"),
    Item("3.3.4", "Восстановление ОС в режиме загрузки Legacy/CSM"),
    Item("3.4.4", "Проверка возможности загрузки дистрибутивного образа по сети"),
    Item("3.4.6", "AoE-загрузка средствами ПНС на ВК «Эльбрус»"),
    Item("4", "Проверка возможности установки ОС"),
    Item("5", "Обновление ОС до актуального состояния", "upgrade"),
    Item("6", "Проверка возможности обновления прошивки компонентов оборудования", "fwupd"),
    Item("7", "Проверка и сохранение журналов", "syslogs"),
    Item("8.2", "Сбор информации о системе и оборудовании", "collect"),
    Item(
        "8.3.1",
        "Проверка CPU и материнской платы",
        "",
        _file_evidence("inxi-CM.txt", "# inxi -CM"),
    ),
    Item("8.3.2", "Проверка оперативной памяти", "", _file_evidence("inxi-m.txt", "# inxi -m")),
    Item("8.3.3", "Проверка дисковой подсистемы", "", _file_evidence("inxi-D.txt", "# inxi -D")),
    Item(
        "8.3.4",
        "Проверка подсистемы вывода изображения",
        "",
        _file_evidence("inxi-G.txt", "# inxi -G"),
    ),
    Item(
        "8.3.5",
        "Проверка наличия 3D-ускорения",
        "",
        _grep_evidence("glxinfo.txt", r"^(direct rendering|OpenGL renderer string):", "$ glxinfo"),
    ),
    Item(
        "8.3.6",
        "Проверка возможностей привода CD/DVD/Blu-ray",
        "",
        _file_evidence("dvd-info.txt"),
    ),
    Item("9", "Экспресс-тест основных компонентов", "express"),
    Item("10.1", "Проверка CPU под нагрузкой", "cpupower", _file_evidence("cpu-freq.txt")),
    Item(
        "10.2.1",
        "Проверка Ethernet (при наличии)",
        "",
        _file_evidence("network.txt"),
    ),
    Item("10.2.2", "Проверка Wi-Fi (при наличии)"),
    Item("10.2.3", "Проверка Infiniband/RDMA (при наличии)"),
    Item("10.2.4", "Проверка производительности сетевых интерфейсов"),
    Item("10.3.1", "Проверка режимов работы видеокарты"),
    Item("10.3.2", "Проверка датчика автоматического поворота экрана (при наличии)"),
    Item("10.3.3", "Проверка VGA (при наличии)"),
    Item("10.3.4", "Проверка HDMI (при наличии)"),
    Item("10.3.5", "Проверка DisplayPort (при наличии)"),
    Item("10.3.6", "Проверка Thunderbolt (при наличии)"),
    Item("10.3.7", "Проверка работы двух подключенных мониторов"),
    Item("10.3.8", "Проверка работы трёх подключенных мониторов"),
    Item("10.4.1.1", "Проверка состояния регулятора громкости"),
    Item("10.4.1.2", "Проверка воспроизведения звука через терминал"),
    Item("10.4.1.3", "Проверка изменения громкости в графическом режиме"),
    Item("10.4.1.4", "Проверка выключения звука (mute)"),
    Item("10.4.1.5", "Проверка включения звука (unmute)"),
    Item("10.4.1.6", "Проверка функциональных клавиш изменения громкости (при наличии)"),
    Item("10.4.2.1", "Проверка записи и воспроизведения звука в терминале"),
    Item("10.4.2.2", "Проверка записи и воспроизведения звука в приложении"),
    Item("10.4.3.1", "Проверка записи и воспроизведения звука через mini-jack/3.5мм"),
    Item("10.4.3.2", "Проверка вывода звука через порт HDMI/DisplayPort/Thunderbolt"),
    Item("10.5", "Host-адаптеры и RAID-контроллеры"),
    Item(
        "10.5.1",
        "Проверка производительности интерфейсов блочных устройств",
        "",
        _hdparm_evidence,
    ),
    Item("10.6.1.1", "Проверка включения/выключения компьютера (GUI)"),
    Item("10.6.1.2", "Проверка перезагрузки компьютера (GUI)"),
    Item("10.6.1.3", "Проверка «спящего» режима (GUI)"),
    Item("10.6.1.4", "Проверка «ждущего» режима (GUI)"),
    Item("10.6.1.5", "Проверка изменения действий при нажатии кнопки питания"),
    Item("10.6.1.6.1", "Закрытие крышки ноутбука: завершение работы"),
    Item("10.6.1.6.2", "Закрытие крышки ноутбука: «спящий» режим"),
    Item("10.6.1.6.3", "Закрытие крышки ноутбука: «ждущий» режим"),
    Item("10.6.2.1", "Проверка выключения компьютера (консоль)"),
    Item("10.6.2.2", "Проверка перезагрузки компьютера (консоль)"),
    Item("10.6.2.3", "Проверка «спящего» режима (консоль)"),
    Item("10.6.2.4", "Проверка «ждущего» режима (консоль)"),
    Item("10.7.1.1", "Проверка реакции на подключение/отключение внешнего БП"),
    Item("10.7.1.2", "Проверка изменения яркости экрана"),
    Item("10.7.2", "Проверка энергосбережения в консоли"),
    Item("10.8", "Проверка NUMA (при наличии)", "numa", _file_evidence("numa.txt")),
    Item("10.9", "Проверка IPMI (при наличии)", "ipmi", _file_evidence("ipmi.txt")),
    Item("10.10.1", "Проверка интерфейса eSATA (при наличии)"),
    Item("10.10.2", "Проверка сенсорного экрана (при наличии)"),
    Item("10.10.3", "Проверка встроенной камеры (при наличии)", "webcam"),
    Item("10.10.4", "Проверка интерфейса PS/2 (при наличии)"),
    Item("10.10.5", "Проверка работы сенсорной панели (при наличии)"),
    Item("10.10.6", "Проверка функциональных клавиш клавиатуры (при наличии)"),
    Item(
        "10.10.7",
        "Проверка работы сканера отпечатка пальца (при наличии)",
        "fprnt",
        _file_evidence("fprintd.txt"),
    ),
    Item("10.10.8", "Проверка интерфейсов USB 1.0-3.2"),
    Item("10.10.9", "Проверка USB 3.2 Gen2/USB4 и Thunderbolt 3/4 (при наличии)"),
    Item(
        "10.10.10",
        "Проверка Bluetooth (при наличии)",
        "bluez",
        _file_evidence("bluetooth.txt"),
    ),
    Item("10.10.11", "Проверка разъёма для карт памяти (при наличии)"),
    Item(
        "10.10.12",
        "Проверка разъёма для смарт-карт (при наличии)",
        "scard",
        _file_evidence("smartcard.txt"),
    ),
    Item("10.10.13", "Проверка привода CD/DVD/Blu-ray (при наличии)"),
    Item("10.11", "Контрольная проверка сообщений ядра", "finalize"),
    Item("11.1", "Производительность дисковой подсистемы", "diskperf", _fio_evidence),
    Item(
        "11.2",
        "Производительность видеоподсистемы",
        "glmark",
        _grep_evidence("glmark2.log", r"glmark2 Score:"),
    ),
    Item("11.3", "Проверка расширителя портов (при наличии)"),
)


def read_results(workdir: Path) -> dict[str, int]:
    """Last recorded status of each step (a retest overrides earlier runs)."""
    wd = Path(workdir)
    path = wd / "STATE" / "RESULTS"
    if not path.is_file():
        path = wd / "RESULTS"
    out: dict[str, int] = {}
    for line in _read(path).splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0].strip().lstrip("-").isdigit():
            out[parts[1].strip()] = int(parts[0])
    return out


def read_subresults(workdir: Path) -> dict[str, str]:
    """Statuses of methodology sub-items written by steps (results-<step>.txt)."""
    out: dict[str, str] = {}
    for path in sorted(Path(workdir).glob("results-*.txt")):
        for line in _read(path).splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[1].strip():
                out[parts[0].strip()] = parts[1].strip()
    return out


def _subresult(sub: dict[str, str], number: str) -> str:
    """Status of the item or of its nearest parent (10.4.1.3 -> 10.4.1)."""
    parts = number.split(".")
    while parts:
        key = ".".join(parts)
        if key in sub:
            return sub[key]
        parts.pop()
    return ""


def build_rows(workdir: Path) -> list[Row]:
    wd = Path(workdir)
    results = read_results(wd)
    sub = read_subresults(wd)
    rows = []
    for item in ITEMS:
        status = ""
        if item.step and item.step in results:
            status = STATUS_NAMES.get(results[item.step], str(results[item.step]))
        elif not item.step:
            status = _subresult(sub, item.number)
        rows.append(
            Row(
                number=item.number,
                title=item.title,
                status=status,
                evidence=item.evidence(wd) if item.evidence else [],
                comment=_read(wd / f"comments-{item.number}.txt").strip(),
            )
        )
    return rows


def _os_release() -> str:
    m = re.search(r'^PRETTY_NAME="?([^"\n]*)"?', _read(Path("/etc/os-release")), re.M)
    return m.group(1) if m else ""


def _kernel(wd: Path) -> str:
    parts = _read(wd / "uname.txt").split()
    return parts[2] if len(parts) > 2 else os.uname().release


def _dmi(name: str) -> str:
    return _read(Path("/sys/class/dmi/id") / name).strip()


def _boot_mode() -> str:
    if not Path("/sys/firmware/efi").is_dir():
        return "Legacy/CSM"
    try:
        data = SECUREBOOT_VAR.read_bytes()
    except OSError:
        return "UEFI"
    return "UEFI + SecureBoot" if data[-1:] == b"\x01" else "UEFI (SecureBoot выключен)"


def _configuration(wd: Path) -> list[str]:
    out = []
    m = re.search(r"^Model name:\s*(.+)$", _read(wd / "lscpu.txt"), re.M)
    if m:
        out.append(f"Процессор: {m.group(1).strip()}")
    m = re.search(r"^MemTotal:\s*(\d+)", _read(Path("/proc/meminfo")), re.M)
    if m:
        out.append(f"Память: {int(m.group(1)) / 1048576:.1f} GiB (MemTotal)")
    for name, pattern, label in (
        ("inxi-D.txt", r"^\s*ID-\d+:", "Диск"),
        ("inxi-G.txt", r"^\s*Device-\d+:", "Видео"),
        ("lspci.txt", r"(Ethernet|Network) controller", "Сеть"),
    ):
        for ln in _read(wd / name).splitlines():
            if re.search(pattern, ln):
                text = re.sub(r"^\s*(ID|Device)-\d+:\s*", "", ln).strip()
                out.append(f"{label}: {text}")
    return out


def _kernel_workarounds() -> list[str]:
    cmdline = _read(Path("/proc/cmdline")).split()
    return [opt for opt in KERNEL_WORKAROUNDS if opt in cmdline]


def build_title(workdir: Path) -> list[tuple[str, str]]:
    wd = Path(workdir)
    vendor = " ".join(v for v in (_dmi("sys_vendor"), _dmi("product_name")) if v)
    version = _dmi("product_version")
    model = f"{vendor} ({version})" if vendor and version else vendor
    kernel = _kernel(wd)
    workarounds = _kernel_workarounds()
    if workarounds:
        kernel += "; параметры ядра: " + " ".join(workarounds)
    return [
        ("Дата и место тестирования", f"{date.today():%d.%m.%Y}, {TO_FILL}"),
        ("Версия методики", METHODOLOGY_VERSION),
        ("Версия ядра ОС", kernel),
        ("Дистрибутив", f"{_os_release()}; ISO и MD5: {TO_FILL}"),
        ("Модель компьютера", model or TO_FILL),
        ("Конфигурация", "\n".join(_configuration(wd)) or TO_FILL),
        ("Выбранный режим загрузки", _boot_mode()),
        ("Ссылка на результаты", TO_FILL),
        ("Мнение тестировщика", TO_FILL),
    ]


def _problems(rows: list[Row]) -> list[str]:
    out = []
    for r in rows:
        if r.status in ("FAILED", "BLOCKED"):
            note = f" — {r.comment}" if r.comment else ""
            out.append(f"{r.number}. {r.title}: {r.status}{note}")
    return out


def render_markdown(title: list[tuple[str, str]], rows: list[Row]) -> str:
    lines = ["# Протокол тестирования (черновик hw-test)", "", "## Титульный лист", ""]
    lines += ["| Поле | Значение |", "|---|---|"]
    for key, value in title:
        lines.append(f"| {key} | {value.replace(chr(10), '<br>')} |")
    lines += ["", "### Обнаруженные проблемы и способы их решения или обхода", ""]
    lines += [f"- {p}" for p in _problems(rows)] or [f"- {TO_FILL}"]
    lines += ["", "## Протокол", "", "| N | Шаг | Статус |", "|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.number} | {r.title} | {r.status or '—'} |")
    lines += ["", "## Выводы команд и комментарии", ""]
    for r in rows:
        if not (r.evidence or r.comment):
            continue
        lines += [f"### {r.number}. {r.title}", ""]
        if r.comment:
            lines += [r.comment, ""]
        if any(e.startswith("| ") for e in r.evidence):
            lines += r.evidence + [""]
        elif r.evidence:
            lines += ["```", *r.evidence, "```", ""]
    return "\n".join(lines).rstrip() + "\n"


_HTML_STYLE = """
body{font-family:sans-serif;margin:2em auto;max-width:60em;padding:0 1em;
color:#222;background:#fff}
table{border-collapse:collapse;width:100%;margin:1em 0}
th,td{border:1px solid #999;padding:.3em .5em;vertical-align:top;text-align:left}
pre{background:#f4f4f4;padding:.5em;overflow-x:auto;font-size:.85em}
.PASSED{color:#060}.FAILED{color:#b00}.BLOCKED{color:#a60}.SKIPPED{color:#666}
.todo{color:#b00}
@media print{pre{white-space:pre-wrap}}
"""


def render_html(title: list[tuple[str, str]], rows: list[Row]) -> str:
    esc = html.escape

    def val(v: str) -> str:
        text = esc(v).replace("\n", "<br>")
        return text.replace(esc(TO_FILL), f'<span class="todo">{esc(TO_FILL)}</span>')

    out = [
        "<!doctype html>",
        '<html lang="ru"><head><meta charset="utf-8">',
        "<title>Протокол тестирования</title>",
        f"<style>{_HTML_STYLE}</style></head><body>",
        "<h1>Протокол тестирования (черновик hw-test)</h1>",
        "<h2>Титульный лист</h2><table>",
    ]
    out += [f"<tr><th>{esc(k)}</th><td>{val(v)}</td></tr>" for k, v in title]
    out.append("</table><h3>Обнаруженные проблемы и способы их решения или обхода</h3><ul>")
    out += [f"<li>{esc(p)}</li>" for p in _problems(rows)] or [f"<li>{val(TO_FILL)}</li>"]
    out.append("</ul><h2>Протокол</h2><table>")
    out.append(
        "<tr><th>N</th><th>Шаг (команда/действие, вывод, комментарии)</th><th>Статус</th></tr>"
    )
    for r in rows:
        body = esc(r.title)
        if r.comment:
            body += f"<br><i>{esc(r.comment)}</i>"
        if r.evidence:
            body += "<pre>" + esc("\n".join(r.evidence)) + "</pre>"
        status = f'<td class="{esc(r.status)}">{esc(r.status or "—")}</td>'
        out.append(f"<tr><td>{esc(r.number)}</td><td>{body}</td>{status}</tr>")
    out.append("</table></body></html>")
    return "\n".join(out) + "\n"


def write_protocol(workdir: Path) -> tuple[Path, Path]:
    wd = Path(workdir)
    title = build_title(wd)
    rows = build_rows(wd)
    md = wd / "protocol.md"
    page = wd / "protocol.html"
    md.write_text(render_markdown(title, rows), encoding="utf-8")
    page.write_text(render_html(title, rows), encoding="utf-8")
    return md, page
