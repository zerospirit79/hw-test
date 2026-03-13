import json, platform, psutil
from .utils.cmd import run_cmd

def _lshw_json():
    r = run_cmd(["lshw", "-json"], timeout=30)
    if r["rc"] == 0 and r["stdout"].strip():
        try:
            return json.loads(r["stdout"])
        except Exception:
            return None
    return None

def summarize(include_lshw: bool = False):
    info = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "cpu": {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "freq_mhz": (psutil.cpu_freq().current if psutil.cpu_freq() else None),
            "load_perc": psutil.cpu_percent(interval=0.2),
        },
        "memory": {
            "total_bytes": psutil.virtual_memory().total,
            "available_bytes": psutil.virtual_memory().available,
        },
        "disks": [],
        "net": [],
    }
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
            info["disks"].append({
                "device": p.device, "mount": p.mountpoint, "fstype": p.fstype,
                "total": u.total, "free": u.free
            })
        except Exception:
            continue
    for nic, addrs in psutil.net_if_addrs().items():
        info["net"].append({
            "iface": nic,
            "addresses": [a.address for a in addrs if getattr(a, "address", None)]
        })
    if include_lshw:
        info["lshw"] = _lshw_json()
    return info

def run(json_out: bool = False, include_lshw: bool = False):
    data = summarize(include_lshw=include_lshw)
    if json_out:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
        print(f"OS: {data['os']['system']} {data['os']['release']} ({data['os']['machine']})")
    print(f"CPU: {data['cpu']['physical_cores']} phys / {data['cpu']['logical_cores']} threads, ~{data['cpu']['freq_mhz']} MHz")
    print(f"Mem total: {data['memory']['total_bytes']}")
    print("Disks:")
    for d in data["disks"]:
        print(f"  {d['device']} -> {d['mount']} {d['fstype']} total={d['total']} free={d['free']}")
    print("Net ifaces:")
    for n in data["net"]:
        addrs = ", ".join(n['addresses']) if n['addresses'] else "-"
        print(f"  {n['iface']}: {addrs}")
    return 0
