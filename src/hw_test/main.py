from pathlib import Path
from .config import load_config
from .system.distro import detect_branch
from .system.repo import switch_repo
from .system.packages import ensure_packages
from .system.power import apply_sleep_policy
from .system.hwinfo import collect_hwinfo
from .system.multimedia import play_video
from .system.journal import collect_logs, finalize
from .utils.video_sets import load_video_set

def run(args):
    cfg = load_config()
    branch = getattr(args, "branch", None) or cfg.get("branch") or detect_branch()
    mode = getattr(args, "mode", None) or cfg.get("mode") or "online"
    mirror = getattr(args, "mirror_url", None) or cfg.get("mirror_url") or None

    switch_repo(branch, mode, mirror)
    ensure_packages(want_graphics=True, want_media=True)

    mask_sleep_cfg = (cfg.get("mask_sleep", "true") or "true").lower() == "true"
    mask_sleep = mask_sleep_cfg and not getattr(args, "no_suspend_mask", False)
    apply_sleep_policy(mask=mask_sleep)

    out_base = Path.home() / "PC-TEST"
    collect_hwinfo(out_base / "hw")

    vset_name = cfg.get("express_video_set", "youtube")
    urls = load_video_set(vset_name)
    play_video(urls, preferred_browser=getattr(args, "preferred_browser", None) or cfg.get("preferred_browser"))

    collect_logs(out_base / "logs")

    if getattr(args, "finish", False):
        finalize(name=getattr(args, "name", None) or "TEST", srcdir=out_base)
