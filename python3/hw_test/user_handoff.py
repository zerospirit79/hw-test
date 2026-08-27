"""Передача выполнения от root к пользовательской сессии между шагами плана."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from hw_test.context import RuntimeContext, graphical_session
from hw_test.steps import create_step
from hw_test.constants import TEST_SKIPPED
from hw_test.terminal import close_desktop_terminal_if_needed, test_user_uid


def step_role(ctx: RuntimeContext, stepname: str) -> str:
    """Роль шага в плане: root, user или both."""
    plan = Path(ctx.workdir) / "STATE" / ctx.testplan
    if not plan.is_file():
        return ""
    for line in plan.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(stepname):
            return line.split("\t", 1)[0]
    return ""


def step_needs_user_handoff(ctx: RuntimeContext, stepname: str) -> bool:
    """Нужна ли интерактивная пользовательская сессия (не batch/TUI skip)."""
    role = step_role(ctx, stepname)
    if role == "root":
        return False
    if role not in ("user", "both"):
        return False
    # Headless config uses a console TUI; root can run it on the same tty.
    # openvt nesting otherwise leaves "press any key" on another pts.
    if stepname == "config" and not graphical_session():
        return False
    step = create_step(stepname, ctx)
    return step.pre() != TEST_SKIPPED


def user_has_graphical_session(username: str) -> bool:
    """Есть ли у пользователя активный DISPLAY или WAYLAND_DISPLAY."""
    import pwd

    from hw_test.de_terminal import _session_env_for_uid

    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        return False
    env = _session_env_for_uid(pw.pw_uid)
    return bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))


def ensure_express_packages(ctx: RuntimeContext) -> None:
    """Доустановить пакеты экспресс-теста, пока процесс ещё root."""
    if not (ctx.xprss_test and ctx.have_xorg) or os.geteuid() != 0:
        return
    missing = [
        pkg
        for pkg in (
            "yad",
            "notify-send",
            "xdg-utils",
            "pulseaudio-utils",
            "icon-theme-adwaita",
            "sound-theme-freedesktop",
        )
        if ctx.is_pkg_available(pkg) and not ctx.is_pkg_installed(pkg)
    ]
    if missing:
        ctx.spawn("apt-get", "install", "-y", "--", *missing)


def switch_to_user_in_process(ctx: RuntimeContext, next_step: str = "") -> bool:
    """Снизить привилегии до тестового пользователя в текущем терминале."""
    if os.geteuid() != 0:
        return True
    if not ctx.username:
        return False
    import pwd

    try:
        pw = pwd.getpwnam(ctx.username)
    except KeyError:
        return False
    if pw.pw_uid == 0:
        return False

    from hw_test.de_terminal import prepare_user_session_env, wait_for_display

    prepare_user_session_env(ctx, pw.pw_uid)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        if next_step == "express" and wait_for_display(120):
            prepare_user_session_env(ctx, pw.pw_uid)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False

    ctx.chown_workdir_for_user()
    try:
        os.initgroups(ctx.username, pw.pw_gid)
    except (AttributeError, PermissionError, OSError):
        try:
            os.setgroups([])
        except OSError:
            pass
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    os.environ["HOME"] = pw.pw_dir
    os.environ["USER"] = ctx.username
    os.environ["LOGNAME"] = ctx.username
    return True


def handoff_user_message(ctx: RuntimeContext, next_step: str) -> str:
    """Краткое сообщение о переключении сессии."""
    if ctx.langid == "ru":
        if next_step == "config":
            return "Запуск шага 5.4 «Определение плана тестирования»..."
        if next_step == "express":
            return "Запуск шага 9 «Экспресс-тест»..."
        return "Переключение на пользовательскую сессию..."
    if next_step == "config":
        return "Starting step 5.4 (test plan configuration)..."
    if next_step == "express":
        return "Starting step 9 (express test)..."
    return "Switching to user session..."


def exit_after_handoff(ctx: RuntimeContext) -> None:
    """Завершить root-процесс после открытия окна у пользователя."""
    if getattr(ctx, "desktop_icon_start", None):
        close_desktop_terminal_if_needed(uid=test_user_uid(ctx.username))
    raise SystemExit(0)


def handoff_to_user_session(ctx: RuntimeContext) -> None:
    """Передать следующий шаг пользовательской сессии или открыть второй терминал."""
    next_step = ""
    stepfile = Path(ctx.workdir) / "STATE" / "STEP"
    if stepfile.is_file():
        next_step = stepfile.read_text(encoding="utf-8").splitlines()[0].strip()

    if next_step == "express":
        ensure_express_packages(ctx)

    if switch_to_user_in_process(ctx, next_step):
        print(
            f"\n{ctx.CLR_OK}{handoff_user_message(ctx, next_step)}{ctx.CLR_NORM}\n",
            flush=True,
        )
        return

    if (
        not ctx.disable_autorun
        and ctx.username
        and os.geteuid() == 0
        and user_has_graphical_session(ctx.username)
    ):
        from hw_test.de_terminal import spawn_continue_in_user_session

        settings = Path(ctx.workdir) / "STATE" / "settings.ini"
        if spawn_continue_in_user_session(
            ctx.username,
            settings if settings.is_file() else None,
            ctx.progname,
        ):
            if ctx.langid == "ru":
                if next_step == "config":
                    msg = (
                        "Открыто второе окно для шага 5.4 «Определение плана тестирования». "
                        "Продолжайте в нём; окно с обновлением (root) можно закрыть."
                    )
                elif next_step == "express":
                    msg = (
                        "Открыто окно терминала для шага 9 «Экспресс-тест». "
                        "Продолжайте там; окно root можно закрыть."
                    )
                else:
                    msg = (
                        "Открыто второе окно терминала для продолжения тестирования. "
                        "Продолжайте там; это окно root можно закрыть."
                    )
            else:
                if next_step == "config":
                    msg = (
                        "A second terminal was opened for step 5.4 (test plan). "
                        "Continue there; you may close this root window."
                    )
                elif next_step == "express":
                    msg = (
                        "A terminal was opened for step 9 (express test). "
                        "Continue there; you may close this root window."
                    )
                else:
                    msg = (
                        "A second terminal was opened to continue testing. "
                        "Continue there; you may close this root window."
                    )
            print(f"\n{ctx.CLR_OK}{msg}{ctx.CLR_NORM}\n", flush=True)
            exit_after_handoff(ctx)
    if (
        next_step == "config"
        and not graphical_session()
        and ctx.username
        and not sys.stdin.isatty()
    ):
        from hw_test.de_terminal import spawn_continue_on_vt

        if spawn_continue_on_vt(ctx.username, ctx.progname):
            if ctx.langid == "ru":
                msg = (
                    "Шаг 5.4 «Определение плана тестирования» открыт на консоли tty1 "
                    "(Ctrl+Alt+F1). Завершите настройку там."
                )
            else:
                msg = (
                    "Step 5.4 (test plan) is open on console tty1 (Ctrl+Alt+F1). "
                    "Complete the configuration there."
                )
            print(f"\n{ctx.CLR_OK}{msg}{ctx.CLR_NORM}\n", flush=True)
            exit_after_handoff(ctx)
    if ctx.langid == "ru":
        msg = "Продолжите тестирование от пользователя: hw-test --continue"
        if next_step == "config":
            msg = "Шаг 5.4 (план тестирования): hw-test --continue"
        elif next_step == "express":
            msg = "Шаг 9 (экспресс-тест): hw-test --continue"
    else:
        msg = "Continue testing as user: hw-test --continue"
        if next_step == "config":
            msg = "Step 5.4 (test plan): hw-test --continue"
        elif next_step == "express":
            msg = "Step 9 (express test): hw-test --continue"
    print(f"\n{ctx.CLR_OK}{msg}{ctx.CLR_NORM}\n", flush=True)
    exit_after_handoff(ctx)
