from __future__ import annotations
import os
import json
import shutil
import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any
from hw_test.utils.cmd import run_cmd

DEFAULT_FILES = [
    "/var/log/syslog",
    "/var/log/messages",
    "/var/log/dmesg",
    "/var/log/kern.log",
    "/var/log/auth.log",
    "/etc/os-release",
    "/etc/fstab",
]

BASE_CMDS: List[Tuple[List[str], str]] = [
    (["uname", "-a"], "uname.txt"),
    (["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], "lsblk.txt"),
    (["df", "-hT"], "df.txt"),
    (["ip", "addr"], "ip_addr.txt"),
    (["ip", "route"], "ip_route.txt"),
    (["lspci", "-nn"], "lspci.txt"),
    (["lsusb"], "lsusb.txt"),
    (["dmesg", "-T"], "dmesg.txt"),
    (["lscpu"], "lscpu.txt"),
    (["free", "-h"], "free.txt"),
]

EXTRA_CMDS: List[Tuple[List[str], str]] = [
    (["journalctl", "-b", "-n", "5000"], "journalctl_b.txt"),
    (["journalctl", "--list-boots"], "journalctl_list.txt"),
    (["ss", "-tupn"], "sockets.txt"),
]

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _sanitize_name(name: str) -> str:
    safe = name.replace(" ", "_").replace("/", "_")
    return safe[:120]

def _write_command_output(out_dir: Path, cmd: List[str], fname: str, rc: int, stdout: str, stderr: str) -> None:
    header = []
    header.append("CMD: " + " ".join(cmd))
    header.append(f"RC: {rc}")
    if stderr:
        header.append("STDERR: " + stderr.strip())
    content = "\n".join(header) + "\n\n" + (stdout or "")
    (out_dir / _sanitize_name(fname)).write_text(content, encoding="utf-8", errors="ignore")

def _copy_if_exists(src: Path, dst_dir: Path) -> bool:
    if src.exists():
        try:
            shutil.copy2(src, dst_dir / src.name)
            return True
        except Exception:
            return False
    return False

def collect(out_dir: str = "logs") -> Dict[str, Any]:
    out = Path(out_dir)
    _ensure_dir(out)

    warnings: List[str] = []
    executed: List[Dict[str, Any]] = []
    cmds = list(BASE_CMDS) + EXTRA_CMDS  # можно убрать EXTRA_CMDS, если нужно «минимально»

    for cmd, fname in cmds:
        # Пропускаем, если бинарь отсутствует
        if shutil.which(cmd[0]) is None:
            try:
                _write_command_output(out, cmd, fname, 127, "", f"{cmd[0]} not found")
            except Exception:
                pass
            warnings.append(f"Command not found: {cmd[0]}")
            continue
        r = run_cmd(cmd, timeout=30)
        rc = int(r.get("rc", 1))
        stdout = r.get("stdout", "") or ""
        stderr = r.get("stderr", "") or ""
        try:
            _write_command_output(out, cmd, fname, rc, stdout, stderr)
        except Exception:
            warnings.append(f"Failed to write file: {fname}")
        executed.append({
            "cmd": cmd,
            "file": fname,
            "rc": rc,
            "bytes_stdout": len(stdout.encode("utf-8", errors="ignore")),
            "bytes_stderr": len(stderr.encode("utf-8", errors="ignore")),
        })
        if rc == 124:
            warnings.append(f"Timeout for: {' '.join(cmd)}")

    copied: List[str] = []
    for f in DEFAULT_FILES:
        fp = Path(f)
        if _copy_if_exists(fp, out):
            copied.append(fp.name)
        else:
            # Не считаем это фатальным: отсутствие файла или отказ по правам
            warnings.append(f"Missing or failed to copy: {f}")

    # manifest.json с метаданными
    manifest = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "host": os.uname().nodename if hasattr(os, "uname") else "",
        "executed": executed,
        "copied": copied,
        "warnings": warnings,
    }
    try:
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Архив
    tar = out.with_suffix(".tar.gz")
    if tar.exists():
        try:
            tar.unlink()
        except Exception:
            warnings.append(f"Cannot remove existing archive: {tar}")
    archive_path = None
    try:
        shutil.make_archive(out.as_posix(), "gztar", root_dir=out.parent.as_posix(), base_dir=out.name)
        archive_path = tar.as_posix()
    except Exception as e:
        warnings.append(f"Archiving failed: {e}")

    # Возвращаем ровно ваш формат, чтобы не ломать вызовы
    return {"out_dir": out.as_posix(), "archive": archive_path}

def run(out: str = "logs", json_out: bool = False) -> int:
    res = collect(out)
    if json_out:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"Собрано в {res['out_dir']}, архив: {res['archive']}")
    return 0