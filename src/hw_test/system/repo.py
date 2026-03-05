from pathlib import Path
from .distro import is_sp_branch
from ..utils.shell import run

def switch_repo(target_branch, mode="online", mirror_url=None):
    if mode == "online":
        run(f"sudo apt-repo {target_branch}", check=True)
        run("sudo apt-get update", check=True)
    elif mode in ("mirror","offline"):
        if not mirror_url:
            raise ValueError("mirror_url required for mirror/offline mode")
        run(f"sudo apt-repo {target_branch}", check=True)
        Path("/etc/apt/sources.list.d/alt-mirror.list").write_text(f"rpm {mirror_url} {target_branch} classic\n")
        run("sudo apt-get update", check=True)
    else:
        raise ValueError("Unknown mode")
    if is_sp_branch(target_branch):
        run("sudo systemctl enable --now NetworkManager || true", check=False)
        run("sudo apt-get install -y xorg-x11 xinit || true", check=False)
