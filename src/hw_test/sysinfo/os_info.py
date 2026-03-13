import os, re, pathlib, subprocess, json
from typing import Dict, Any, List

def _run(cmd: list) -> tuple[str,int]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout.strip(), p.returncode

def parse_os_release(path: str = "/etc/os-release") -> Dict[str,str]:
    data: Dict[str,str] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k,v = line.split("=",1)
                    data[k]=v.strip().strip('"')
    return data

def detect_branch(osr: Dict[str,str], rpm_release_text: str) -> str:
    t = (osr.get("VERSION","") + " " + osr.get("VERSION_ID","") + " " + rpm_release_text).lower()
    if "sisyphus" in t:
        return "sisyphus"
    for br in ("p11","p10","p9","c10f2","c9f2"):
        if re.search(rf"\b{br}\b", t):
        return br
    vid = osr.get("VERSION_ID","").lower()
    if vid.startswith("11"): return "p11"
    if vid.startswith("10"): return "p10"
    return "unknown"

def read_apt_sources() -> List[Dict[str,str]]:
    items: List[Dict[str,str]] = []
    for d in ("/etc/apt/sources.list.d",):
        p = pathlib.Path(d)
        if not p.exists(): continue
        for f in p.glob("*.list"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
            for line in text.splitlines():
                s=line.strip()
                if not s or s.startswith("#"): continue
                items.append({"file":f.name,"line":s})
    return items

def collect() -> Dict[str,Any]:
    osr = parse_os_release()
    rpm_out,_ = _run(["rpm","-qa","--qf","%{NAME}-%{VERSION}-%{RELEASE}\n"])
    uname,_ = _run(["uname","-r"])
    arch = os.uname().machine
    is_sp = "sp-release" in rpm_out.lower() or "альт сп" in (osr.get("NAME","").lower())
    sp_release = None
    if is_sp:
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", osr.get("VERSION","")) or re.search(r"(\d+\.\d+(?:\.\d+)?)", rpm_out)
        sp_release = m.group(1) if m else None
    branch = detect_branch(osr, rpm_out)
    return {
        "distro": {
            "name": osr.get("NAME"),
            "version": osr.get("VERSION"),
            "version_id": osr.get("VERSION_ID"),
            "edition": osr.get("VARIANT","") or osr.get("ID",""),
            "is_sp": is_sp,
            "sp_release": sp_release,
            "branch": branch,
        },
        "kernel": {"version": uname},
        "arch": arch,
        "repos": read_apt_sources(),
    }
