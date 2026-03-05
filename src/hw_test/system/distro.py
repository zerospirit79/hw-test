from pathlib import Path

def detect_branch():
    osr = {}
    p = Path("/etc/os-release")
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                osr[k] = v.strip().strip('"')
    for key in ("ALT_BRANCH","ALTLinuxBranch","BRANCH"):
        if key in osr and osr[key]:
            return osr[key]
    ver = (osr.get("VERSION_ID", "") or "").strip()
    edition = (osr.get("EDITION", "") or osr.get("ALT_EDITION", "") or "").lower()
    rel = Path("/etc/altlinux-release")
    if "sp" in edition or "server" in edition or "corp" in edition:
        if rel.exists():
            txt = rel.read_text().lower()
            for br in ("c11f1","c10f2"):
                if br in txt:
                    return br
        if ver.startswith("11"):
            return "c11f1"
        return "c10f2"
    if ver.startswith("11"):
        return "p11"
    return "p10"

def is_sp_branch(b: str) -> bool:
    return b in ("c10f2","c11f1")
