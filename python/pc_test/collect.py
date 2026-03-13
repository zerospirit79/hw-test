from __future__ import annotations
import shutil, os, json
from pathlib import Path
from .utils.cmd import run_cmd

DEFAULT_FILES = ["/var/log/syslog", "/var/log/messages", "/var/log/dmesg"]

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def collect(out_dir: str = "logs"):
    out = Path(out_dir)
    _ensure_dir(out)
    cmds = [
        (["uname", "-a"], "uname.txt"),
        (["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], "lsblk.txt"),
        (["df", "-hT"], "df.txt"),
        (["ip", "addr"], "ip_addr.txt"),
        (["lspci", "-nn"], "lspci.txt"),
        (["lsusb"], "lsusb.txt"),
        (["dmesg", "-T"], "dmesg.txt"),
    ]
    for cmd, fname in cmds:
        r = run_cmd(cmd, timeout=20)
        try:
            (out / fname).write_text(r["stdout"] or r["stderr"] or "", encoding="utf-8", errors="ignore")
        except Exception:
            pass
    for f in DEFAULT_FILES:
        fp = Path(f)
        if fp.exists():
            try:
                shutil.copy2(fp, out / fp.name)
            except Exception:
                pass
    tar = out.with_suffix(".tar.gz")
    if tar.exists():
        tar.unlink()
    shutil.make_archive(out.as_posix(), "gztar", root_dir=out.parent.as_posix(), base_dir=out.name)
    return {"out_dir": out.as_posix(), "archive": tar.as_posix()}

def run(out: str = "logs", json_out: bool = False):
    res = collect(out)
    if json_out:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"Собрано в {res['out_dir']}, архив: {res['archive']}")
    return 0
