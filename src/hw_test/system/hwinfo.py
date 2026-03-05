from pathlib import Path
from ..utils.shell import run

def collect_hwinfo(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    cmds = {
        "uname": "uname -a",
        "lspci": "lspci -vvnn || true",
        "lsusb": "lsusb -v || true",
        "inxi": "inxi -Fazy || true",
        "dmidecode": "sudo dmidecode || true"
    }
    for name, cmd in cmds.items():
        (outdir / f"{name}.txt").write_text(run(cmd), encoding="utf-8")
