from pathlib import Path
from typing import Optional
from .sources import render_sources_for_release
from ..utils.cmd import run_cmd
import shutil, logging, os, json

log = logging.getLogger("hw_test.repo")

SOURCES_DIR = Path("/etc/apt/sources.list.d")
BACKUP_DIR = Path("/var/lib/pc-test/backup")

def backup_sources():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for f in SOURCES_DIR.glob("*.list"):
        dst = BACKUP_DIR / f"{f.name}.bak"
        try:
            dst.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            shutil.copy2(f, dst)

def restore_sources():
    for b in BACKUP_DIR.glob("*.bak"):
        orig = SOURCES_DIR / b.name.replace(".bak","")
        shutil.copy2(b, orig)

def switch_release(branch: str, source: str = "internet", mirror_url: Optional[str] = None, disable_others: bool = True):
    text = render_sources_for_release(branch, source=source, mirror_url=mirror_url)
    target = SOURCES_DIR / "pc-test.list"
    if not SOURCES_DIR.exists():
        raise RuntimeError(f"{SOURCES_DIR} does not exist (run as root?)")
    backup_sources()
    target.write_text(text, encoding="utf-8")
    if disable_others:
        for f in SOURCES_DIR.glob("*.list"):
            if f.name != "pc-test.list":
                f.rename(f.with_suffix(f.suffix + ".disabled"))
    run_cmd(["apt-get", "update"])

def dist_upgrade():
    run_cmd(["apt-get","dist-upgrade","-y"])

def install_packages(pkgs: list[str]):
    if not pkgs: return
    run_cmd(["apt-get","install","-y", *pkgs])

def configure_by_info(info: dict, source: str = "internet", mirror_url: Optional[str] = None):
    branch = info.get("distro",{}).get("branch","unknown")
    is_sp = info.get("distro",{}).get("is_sp", False)
    # Для СП — можно подключить специальные каналы (заглушка для расширения)
    switch_release(branch, source=source, mirror_url=mirror_url)
