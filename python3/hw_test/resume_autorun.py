"""Resume after reboot: graphical autostart or systemd service (headless)."""

from __future__ import annotations

import os
import pwd
import shutil
import subprocess
from pathlib import Path

from hw_test.context import RuntimeContext, graphical_session
from hw_test.desktop import chown_autostart_tree, copy_desktop_file, remove_desktop_file

RESUME_ON_LOGIN = "RESUME_ON_LOGIN"
RESUME_UNIT_SUFFIX = "-resume.service"
SYSTEM_INSTANCE_SUFFIX = "-resume@"


def _print_headless_resume_hint(ctx: RuntimeContext) -> None:
    """Tell the operator that login alone resumes testing (no need to type hw-test)."""
    user = ctx.username or "user"
    if ctx.langid == "ru":
        msg = (
            f"После перезагрузки войдите как «{user}» (консоль или SSH) — "
            f"{ctx.progname} продолжит тестирование сам, без ввода команды "
            f"(как автозапуск в графике)."
        )
    else:
        msg = (
            f"After reboot, log in as “{user}” (console or SSH) — "
            f"{ctx.progname} will continue automatically (same idea as desktop autostart)."
        )
    print(f"\n{ctx.CLR_OK}{msg}{ctx.CLR_NORM}\n", flush=True)


def resume_unit_name(progname: str) -> str:
    return f"{progname}{RESUME_UNIT_SUFFIX}"


def system_instance_unit(progname: str, username: str) -> str:
    return f"{progname}{SYSTEM_INSTANCE_SUFFIX}{username}.service"


def system_template_unit(progname: str) -> Path:
    return Path(f"/usr/lib/systemd/system/{progname}-resume@.service")


def want_headless_resume(ctx: RuntimeContext) -> bool:
    """True when systemd resume should be used instead of a .desktop autostart."""
    if ctx.disable_autorun:
        return False
    mode = getattr(ctx, "headless_autorun", "")
    if mode == "0":
        return False
    if mode == "1":
        return True
    return bool(ctx.have_systemd) and not graphical_session()


def setup_resume_autorun(ctx: RuntimeContext, *, force: bool = False) -> None:
    """Register resume after reboot (graphical .desktop or headless systemd unit)."""
    if ctx.disable_autorun or not ctx.homedir or not ctx.username:
        return

    if graphical_session():
        if force or os.geteuid() != 0:
            copy_desktop_file(ctx.progname, ctx.homedir, ctx.disable_autorun, force=force)
        disable_headless_resume(ctx.progname, ctx.username, ctx.homedir)
        return

    if want_headless_resume(ctx):
        if enable_headless_resume(ctx.progname, ctx.username, ctx.homedir):
            chown_autostart_tree(ctx.homedir, ctx.username)
            remove_desktop_file(ctx.progname, ctx.homedir)
            ctx.spawn(
                f": Headless resume on login enabled "
                f"(profile.d + {RESUME_ON_LOGIN} for {ctx.username})"
            )
            _print_headless_resume_hint(ctx)


def _clear_resume_hooks_impl(progname: str, username: str, homedir: str) -> None:
    if homedir and username:
        chown_autostart_tree(homedir, username)
    remove_desktop_file(progname, homedir)
    if username:
        disable_headless_resume(progname, username, homedir)


def clear_resume_autorun(ctx: RuntimeContext) -> None:
    """Remove graphical and headless resume hooks when testing is finished."""
    homedir = ctx.homedir or os.environ.get("HOME", "")
    if os.geteuid() != 0 and ctx.username:
        try:
            pw = pwd.getpwnam(ctx.username)
        except KeyError:
            _clear_resume_hooks_impl(ctx.progname, ctx.username, homedir)
            return
        if (
            subprocess.run(
                [
                    "sudo",
                    "-n",
                    ctx.progname,
                    f"--uid={pw.pw_uid}",
                    "--cleanup-resume",
                ],
                check=False,
            ).returncode
            == 0
        ):
            return
    _clear_resume_hooks_impl(ctx.progname, ctx.username, homedir)


def _system_dropin_dir(progname: str, username: str) -> Path:
    return Path("/etc/systemd/system") / system_instance_unit(progname, username) / ".d"


def _write_system_dropin(progname: str, username: str, home: Path) -> None:
    """Override /home/%i conditions when the test user home is elsewhere."""
    if home == Path("/home") / username:
        dropin = _system_dropin_dir(progname, username)
        if dropin.is_dir():
            shutil.rmtree(dropin)
        return
    dropin = _system_dropin_dir(progname, username)
    dropin.mkdir(parents=True, exist_ok=True)
    (dropin / "override.conf").write_text(
        "[Unit]\n"
        f"ConditionPathExists={home}/HW-TEST/STATE/STEP\n"
        f"ConditionPathExists={home}/HW-TEST/hw-test.log\n",
        encoding="utf-8",
    )


def _resume_marker_path(homedir: str) -> Path:
    return Path(homedir) / "HW-TEST" / "STATE" / RESUME_ON_LOGIN


def _write_resume_marker(username: str, homedir: str) -> bool:
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        return False
    home = Path(homedir or pw.pw_dir)
    marker = home / "HW-TEST" / "STATE" / RESUME_ON_LOGIN
    state = marker.parent
    state.mkdir(parents=True, exist_ok=True)
    marker.write_text("", encoding="utf-8")
    if os.geteuid() == 0:
        subprocess.run(
            ["chown", "-R", f"{username}:{username}", str(state)],
            check=False,
        )
    return True


def _remove_resume_marker(homedir: str) -> None:
    _resume_marker_path(homedir).unlink(missing_ok=True)


def enable_headless_resume(progname: str, username: str, homedir: str) -> bool:
    """Mark headless resume for the next interactive login (TTY/SSH).

    Primary hook is ``/etc/profile.d/hw-test-resume.sh`` (same idea as graphical
    ``~/.config/autostart``: user logs in → hw-test continues). The systemd
    template is optional legacy; boot-time enable is intentionally not used so
    TUI steps (dialog) still have a real console.
    """
    if not _write_resume_marker(username, homedir):
        return False
    if system_template_unit(progname).is_file():
        unit = system_instance_unit(progname, username)
        home = Path(homedir or pwd.getpwnam(username).pw_dir)
        _write_system_dropin(progname, username, home)
        # Drop legacy symlinks that started resume from multi-user.target at boot.
        subprocess.run(["systemctl", "disable", unit], check=False)
        subprocess.run(["systemctl", "daemon-reload"], check=False)
    return True


def disable_headless_resume(progname: str, username: str, homedir: str) -> None:
    """Disable headless resume for the test user."""
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        pw = None
    home = homedir or (pw.pw_dir if pw else "")
    if home:
        _remove_resume_marker(home)
    unit = system_instance_unit(progname, username)
    subprocess.run(["systemctl", "disable", unit], check=False)
    dropin = _system_dropin_dir(progname, username)
    if dropin.is_dir():
        shutil.rmtree(dropin)
    subprocess.run(["systemctl", "daemon-reload"], check=False)
