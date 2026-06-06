"""TTY helpers."""

from __future__ import annotations

import os
import pwd
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

_KGX_COMMS = frozenset({"kgx", "gnome-console", "Console"})
_KGX_ENV = "HW_TEST_KGX"


def test_user_uid(username: str | None = None) -> int:
    """UID of the user under test (not root when hw-test runs via sudo)."""
    if username:
        try:
            return pwd.getpwnam(username).pw_uid
        except KeyError:
            pass
    return os.getuid()


def _kgx_exe() -> Path | None:
    path = shutil.which("kgx")
    if not path:
        return None
    try:
        return Path(path).resolve()
    except OSError:
        return Path(path)


def _process_ppid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("Ppid:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def _process_comm(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _process_name(pid: int) -> str:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("Name:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def _process_exe(pid: int) -> Path | None:
    try:
        return Path(os.readlink(f"/proc/{pid}/exe")).resolve()
    except OSError:
        return None


def _pid_is_kgx(pid: int, kgx: Path | None) -> bool:
    comm = _process_comm(pid)
    name = _process_name(pid)
    exe = _process_exe(pid)
    if comm in _KGX_COMMS or name in _KGX_COMMS:
        return True
    if exe is not None:
        if kgx and exe == kgx:
            return True
        if exe.name == "kgx" or "gnome-console" in exe.name:
            return True
    return False


def _find_kgx_ancestor_pid(start: int | None = None) -> int | None:
    kgx = _kgx_exe()
    pid = os.getppid() if start is None else start
    for _ in range(25):
        if pid <= 1:
            break
        if _pid_is_kgx(pid, kgx):
            return pid
        next_pid = _process_ppid(pid)
        if next_pid is None:
            break
        pid = next_pid
    return None


def _has_pc_test_kgx_for_uid(uid: int) -> bool:
    try:
        proc = subprocess.run(
            ["pgrep", "-u", str(uid), "-x", "kgx", "-a"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    for line in (proc.stdout or "").splitlines():
        if "PC Test" in line or "hw-test" in line:
            return True
    return False


def running_in_kgx() -> bool:
    """True when hw-test runs inside gnome-console (kgx)."""
    if os.environ.get(_KGX_ENV) == "1":
        return True
    if os.environ.get("TERM_PROGRAM") == "kgx":
        return True
    return _find_kgx_ancestor_pid() is not None


def _signal_kgx_pid(pid: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except OSError:
            return
        if sig == signal.SIGTERM:
            time.sleep(0.3)
            if not Path(f"/proc/{pid}").exists():
                return


def _pkill_pc_test_kgx(uid: int) -> None:
    """Last resort: close kgx window launched for hw-test by command line."""
    try:
        proc = subprocess.run(
            ["pgrep", "-u", str(uid), "-x", "kgx", "-a"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return
    for line in (proc.stdout or "").splitlines():
        if "PC Test" not in line and "hw-test" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        _signal_kgx_pid(pid)
        return


def close_kgx_window(*, uid: int | None = None) -> None:
    """Close kgx hosting hw-test (works when hw-test runs as root via sudo)."""
    target_uid = test_user_uid() if uid is None else uid
    pid = _find_kgx_ancestor_pid()
    if pid is not None:
        _signal_kgx_pid(pid)
        return
    _pkill_pc_test_kgx(target_uid)


def read_key(*, abort_on_ctrl_c: bool = False) -> bool:
    """Read one key in raw mode.

    Returns False if the user pressed Ctrl-C and abort_on_ctrl_c is True.
    Otherwise returns True.
    """
    if not sys.stdin.isatty():
        return True
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except KeyboardInterrupt:
        print(flush=True)
        if abort_on_ctrl_c:
            return False
        raise
    except Exception:
        return True
    print(flush=True)
    if abort_on_ctrl_c and ch == "\x03":
        return False
    return True


def close_desktop_terminal_if_needed(*, uid: int | None = None) -> None:
    """Close gnome-console after pause_before_exit (kgx stays open otherwise)."""
    target_uid = test_user_uid() if uid is None else uid
    if running_in_kgx() or _has_pc_test_kgx_for_uid(target_uid):
        close_kgx_window(uid=target_uid)
