from pathlib import Path
import configparser

def load_config():
    cfg = configparser.ConfigParser()
    paths = ["/etc/hw-test.conf", str(Path.home() / ".config/hw-test.conf"), "etc/hw-test.conf"]
    cfg.read(paths, encoding="utf-8")
    out = {}
    if cfg.has_section("hw-test"):
        sec = cfg["hw-test"]
        for k in ("branch","mode","mirror_url","preferred_browser","express_video_set","mask_sleep"):
            out[k] = sec.get(k, fallback=None)
    return out
