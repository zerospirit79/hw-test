"""Test plan configuration forms (config-form-gui.sh / config-form-tui.sh).

On ALT Server the form is a one-shot numbered list on ``/dev/tty`` (no dialog,
no full-screen redraw): console CSI clear is unreliable and arrow-key UIs
leave garbage on the screen. Graphics-only optional tests are cleared when
there is no desktop session.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Sequence, TextIO, Tuple

from hw_test import l10n
from hw_test.config_loader import load_config_files
from hw_test.context import FatalError, RuntimeContext, graphical_session
from hw_test.gui.forms import _run_capture
from hw_test.resume_autorun import clear_resume_autorun
from hw_test.version import HWTEST_BUILD_DATE, HWTEST_VERSION

# Optional tests that require a graphical desktop (not available on typical Server).
_GRAPHICS_ONLY_TAGS = ("xprss", "v3d", "webcam")


def _test_enabled(ctx: RuntimeContext, tag: str) -> bool:
    val = str(getattr(ctx, f"{tag}_test", "") or "").strip().strip("'\"")
    return val in ("1", "yes", "true", "on")


def sync_detected_hardware(ctx: RuntimeContext) -> None:
    """Load settings for the config form (optional tests are chosen in step 5.4 only)."""
    settings = Path(ctx.workdir) / "STATE" / "settings.ini"
    if settings.is_file():
        load_config_files(ctx, settings)


def _test_flags(ctx: RuntimeContext) -> tuple[List[Tuple[str, str, bool]], str]:
    sync_detected_hardware(ctx)
    mate_item, tests_list, _ = l10n.load_config_menu(ctx.langid, ctx.libdir)
    items = [(tag, label, _test_enabled(ctx, tag)) for tag, label in tests_list]
    return items, mate_item


def _has_desktop_stack(ctx: RuntimeContext) -> bool:
    """True when Xorg/Wayland and a known DE were detected (Workstation-like)."""
    if not ctx.have_xorg:
        return False
    return bool(ctx.have_mate or ctx.have_kde5 or ctx.have_xfce or ctx.have_gnome)


def clear_graphics_only_tests(ctx: RuntimeContext) -> list[str]:
    """Disable optional tests that cannot run without a desktop; return cleared tags."""
    if _has_desktop_stack(ctx):
        return []
    cleared: list[str] = []
    for tag in _GRAPHICS_ONLY_TAGS:
        attr = f"{tag}_test"
        if _test_enabled(ctx, tag):
            setattr(ctx, attr, "")
            cleared.append(tag)
    return cleared


def _warn_cleared_graphics_tests(ctx: RuntimeContext, cleared: list[str]) -> None:
    if not cleared:
        return
    names = ", ".join(cleared)
    if ctx.langid == "ru":
        msg = (
            f"Тесты, требующие графическую среду ({names}), отключены: "
            "на этой системе нет рабочего стола (типично для ALT Server)."
        )
    else:
        msg = (
            f"Graphics-only tests ({names}) were disabled: "
            "no desktop environment on this system (typical for ALT Server)."
        )
    print(f"{ctx.CLR_WARN}{msg}{ctx.CLR_NORM}", flush=True)


def _apply_form_selection(ctx: RuntimeContext, items: List[Tuple[str, str, bool]], selected: set[str]) -> None:
    for tag, _label, _ in items:
        setattr(ctx, f"{tag}_test", "1" if tag in selected else "")
    cleared = clear_graphics_only_tests(ctx)
    _warn_cleared_graphics_tests(ctx, cleared)


def _parse_number_selection(line: str, n_items: int) -> set[int] | None:
    """Parse '1 3 8' / '1,3,8' into 1-based indexes. None = invalid."""
    raw = line.replace(",", " ").split()
    if not raw:
        return set()
    indexes: set[int] = set()
    for tok in raw:
        if not tok.isdigit():
            return None
        num = int(tok)
        if num < 1 or num > n_items:
            return None
        indexes.add(num)
    return indexes


def _select_tests_tty(
    title: str,
    hint: str,
    items: Sequence[Tuple[str, str, bool]],
) -> set[str]:
    """Print checklist once; read a line of numbers from /dev/tty (no screen redraw)."""
    try:
        out: TextIO = open("/dev/tty", "w", encoding="utf-8", errors="replace", buffering=1)
        inp: TextIO = open("/dev/tty", "r", encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OSError("no /dev/tty") from exc

    try:
        out.write(f"\n{title}\n\n")
        for i, (_tag, label, enabled) in enumerate(items, start=1):
            mark = "[x]" if enabled else "[ ]"
            out.write(f" {i:2d} {mark} {label}\n")
        out.write(f"\n{hint}\n> ")
        out.flush()
        try:
            line = inp.readline()
        except KeyboardInterrupt:
            raise
        if line == "":
            raise KeyboardInterrupt
        line = line.strip()
        if line.lower() in ("q", "quit"):
            raise KeyboardInterrupt
        if not line:
            return {tag for tag, _label, enabled in items if enabled}
        parsed = _parse_number_selection(line, len(items))
        if parsed is None:
            out.write("Invalid selection; enter numbers like: 8 13\n")
            out.flush()
            raise ValueError("invalid selection")
        return {items[i - 1][0] for i in parsed}
    finally:
        out.close()
        inp.close()


def _cancel_test_plan(ctx: RuntimeContext) -> None:
    """Stop auto-resume after cancel; incomplete STEP remains for explicit --continue."""
    try:
        clear_resume_autorun(ctx)
    except Exception:
        pass
    if ctx.langid == "ru":
        tip = (
            f"План тестирования отменён. Автопродолжение после входа отключено.\n"
            f"Продолжить с этого места: {ctx.progname} --continue\n"
            f"Начать заново: {ctx.progname} --start"
        )
    else:
        tip = (
            f"Test plan canceled. Login auto-resume disabled.\n"
            f"Resume here: {ctx.progname} --continue\n"
            f"Start over: {ctx.progname} --start"
        )
    print(f"\n{ctx.CLR_WARN}{tip}{ctx.CLR_NORM}\n", flush=True)
    ctx.fatal("F20", "Testing canceled.")


def run_gui(ctx: RuntimeContext) -> None:
    """YAD checklist form for optional tests."""
    items, _ = _test_flags(ctx)
    title = ctx.nls_title("Defining a Test Plan", "Определение плана тестирования")
    argv = [
        "yad",
        "--borders=15",
        "--form",
        "--window-icon=utilities-system-monitor",
        "--separator= ",
        f"--title={title}",
    ]
    for _tag, label, enabled in items:
        argv.append(f"--field={label}:CHK")
        argv.append("TRUE" if enabled else "FALSE")

    proc = _run_capture(ctx, argv)
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        ctx.fatal("F20", "Testing canceled.")
    values = proc.stdout.split()
    selected = {
        tag
        for i, (tag, _label, _enabled) in enumerate(items)
        if i < len(values) and values[i].upper() in ("TRUE", "1", "YES", "ON")
    }
    _apply_form_selection(ctx, items, selected)


def run_tui(ctx: RuntimeContext, can_install_mate: bool = False) -> None:
    """Numbered checklist on the console (primary UI on ALT Server)."""
    items, mate_item = _test_flags(ctx)
    if can_install_mate:
        items = [("mate", mate_item, False), *items]
    version = os.environ.get("HWTEST_VERSION") or HWTEST_VERSION
    build = os.environ.get("HWTEST_BUILD_DATE") or HWTEST_BUILD_DATE
    v = f"v{version}"
    if build:
        v = f"{v}/{build}"
    title = ctx.nls_title("Defining a Test Plan", "Определение плана тестирования")
    heading = f"{ctx.progname} {v} — {title}"
    if ctx.langid == "ru":
        hint = (
            "Введите номера включаемых тестов через пробел (пример: 8 13).\n"
            "Enter — оставить как отмечено [x], q — отмена."
        )
    else:
        hint = (
            "Enter numbers to enable (example: 8 13).\n"
            "Enter keeps [x] marks, q cancels."
        )

    prepared: List[Tuple[str, str, bool]] = []
    for tag, label, enabled in items:
        if tag in _GRAPHICS_ONLY_TAGS and not _has_desktop_stack(ctx):
            enabled = False
        prepared.append((tag, label, enabled))

    sys.stdout.flush()
    sys.stderr.flush()
    while True:
        try:
            selected = _select_tests_tty(heading, hint, prepared)
            break
        except KeyboardInterrupt:
            _cancel_test_plan(ctx)
            return
        except ValueError:
            continue
        except OSError:
            ctx.fatal("F20", "No terminal for test plan dialog (use ssh -t).")

    ctx.install_mate = "1" if "mate" in selected else ""
    selected.discard("mate")
    _apply_form_selection(ctx, [(t, l, e) for t, l, e in prepared if t != "mate"], selected)


def run_config_form(ctx: RuntimeContext) -> None:
    """Choose GUI or TUI based on environment."""
    sync_detected_hardware(ctx)
    if graphical_session() and ctx.has_binary("yad"):
        run_gui(ctx)
    else:
        run_tui(ctx)
