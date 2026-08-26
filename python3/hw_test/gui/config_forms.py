"""Test plan configuration forms (config-form-gui.sh / config-form-tui.sh).

On ALT Server and other headless systems the form runs via ``dialog`` (TUI).
Graphics-only optional tests (express, glmark/v3d, webcam) are cleared when
there is no Xorg/Wayland stack — they cannot run without a desktop session.
"""

from __future__ import annotations

import os
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Sequence, Tuple

from hw_test import l10n
from hw_test.config_loader import load_config_files
from hw_test.context import FatalError, RuntimeContext, graphical_session
from hw_test.gui.forms import _run_capture

# Optional tests that require a graphical desktop (not available on typical Server).
_GRAPHICS_ONLY_TAGS = ("xprss", "v3d", "webcam")

# ncurses: wait after ESC so arrow keys (ESC [ A/B/C/D) are not treated as Cancel
# under load right after reboot (classic dialog false cancel on console).
_DIALOG_ESCDELAY_MS = "10000"


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


def _dialog_env() -> dict[str, str]:
    env = os.environ.copy()
    try:
        current = int(env.get("ESCDELAY", "1000") or "1000")
    except ValueError:
        current = 1000
    if current < int(_DIALOG_ESCDELAY_MS):
        env["ESCDELAY"] = _DIALOG_ESCDELAY_MS
    return env


def _drain_tty_input(timeout_s: float = 0.15) -> None:
    """Drop pending console bytes (partial ESC sequences left after a false cancel)."""
    if not sys.stdin.isatty():
        return
    fd = sys.stdin.fileno()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], max(0.0, deadline - time.monotonic()))
        if not ready:
            break
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break


def _run_dialog(cmd: Sequence[str], *, capture_stderr: bool) -> subprocess.CompletedProcess[str]:
    kwargs: dict = {
        "stdin": sys.stdin,
        "text": True,
        "env": _dialog_env(),
    }
    if capture_stderr:
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(cmd, **kwargs)


def _confirm_cancel_tui(ctx: RuntimeContext) -> bool:
    """Return True if the user confirms cancel; False to reopen the checklist."""
    if ctx.langid == "ru":
        text = (
            "Диалог плана тестирования закрыт (Cancel/Esc или сбой ввода).\n"
            "Стрелки вверх/вниз иногда ошибочно дают Esc на консоли.\n\n"
            "Отменить тестирование полностью?"
        )
        title = "Подтверждение отмены"
    else:
        text = (
            "The test plan dialog was closed (Cancel/Esc or input glitch).\n"
            "Up/Down arrows can be misread as Esc on the console.\n\n"
            "Cancel testing completely?"
        )
        title = "Confirm cancel"
    cmd = [
        "dialog",
        "--shadow",
        "--no-mouse",
        "--title",
        f"[ {title} ]",
        "--yesno",
        text,
        "12",
        "70",
    ]
    _drain_tty_input()
    proc = _run_dialog(cmd, capture_stderr=False)
    _drain_tty_input()
    # dialog yesno: 0 = Yes, 1 = No/Cancel, 255 = ESC
    return proc.returncode == 0


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
    # YAD expects TRUE/FALSE immediately after each CHK field (not all fields, then all values).
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
    """dialog checklist for optional tests (primary UI on ALT Server / headless)."""
    items, mate_item = _test_flags(ctx)
    version = os.environ.get("HWTEST_VERSION", "")
    build = os.environ.get("HWTEST_BUILD_DATE", "")
    v = f"v{version}/{build}"
    title = ctx.nls_title("Defining a Test Plan", "Определение плана тестирования")
    _, _, tui_width = l10n.load_config_menu(ctx.langid, ctx.libdir)
    n = len(items)
    h = n // 2 + (1 if can_install_mate else 0)
    height = 6 + h
    backtitle = f"{ctx.progname} {v}".strip()

    cmd: List[str] = [
        "dialog",
        "--no-tags",
        "--no-mouse",
        "--shadow",
        "--backtitle",
        backtitle,
        "--title",
        f"[ {title} ]",
        "--checklist",
        "",
        str(height),
        str(tui_width),
        str(h),
    ]
    if can_install_mate:
        cmd.extend(["mate", mate_item, "off"])
    for tag, label, enabled in items:
        # On headless Server do not pre-check graphics-only items even if detect set them.
        if tag in _GRAPHICS_ONLY_TAGS and not _has_desktop_stack(ctx):
            enabled = False
        cmd.extend([tag, label, "on" if enabled else "off"])

    if not sys.stdin.isatty():
        ctx.fatal("F20", "No terminal for test plan dialog (use ssh -t).")

    # Like config-form-tui.sh: UI on stdout (terminal), selected tags on stderr.
    # Retry after false Esc from arrow keys; only exit on confirmed cancel.
    while True:
        _drain_tty_input()
        proc = _run_dialog(cmd, capture_stderr=True)
        if proc.returncode == 0:
            break
        if _confirm_cancel_tui(ctx):
            ctx.fatal("F20", "Testing canceled.")
        os.system("clear")

    os.system("clear")

    ctx.install_mate = ""
    selected: set[str] = set()
    for tag in (proc.stderr or "").split():
        if tag == "mate":
            ctx.install_mate = "1"
        else:
            selected.add(tag)
    _apply_form_selection(ctx, items, selected)


def run_config_form(ctx: RuntimeContext) -> None:
    """Choose GUI or TUI based on environment."""
    sync_detected_hardware(ctx)
    if graphical_session() and ctx.has_binary("yad"):
        run_gui(ctx)
    elif ctx.has_binary("dialog"):
        run_tui(ctx)
    else:
        raise FatalError(1)
