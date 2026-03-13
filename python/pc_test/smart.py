from __future__ import annotations
import glob, json
from .utils.cmd import run_cmd

def list_block_devices() -> list[str]:
    devs: list[str] = []
    # SATA/SAS
    devs += glob.glob("/dev/sd?")  # sda, sdb ...
    # NVMe: устройства дисков (без разделов p1, p2)
    for d in glob.glob("/dev/nvme*n*"):
        if "p" not in d:
            devs.append(d)
    # Можно расширить под mmcblk, если понадобится
    return sorted(set(devs))

def check_device(dev: str):
    cmd = ["smartctl", "-a", "-j", dev]
    r = run_cmd(cmd, timeout=25)
    if r["rc"] != 0:
        return {"device": dev, "error": f"rc={r['rc']}", "stderr": r["stderr"]}
    try:
        data = json.loads(r["stdout"]) if r["stdout"] else {}
    except Exception:
        return {"device": dev, "error": "parse_error", "raw": r["stdout"]}
    # краткий статус
    passed = None
    if isinstance(data, dict):
        passed = data.get("smart_status", {}).get("passed")
        data["_summary"] = {"passed": passed}
    return data

def run(devices=None, json_out: bool = False):
    devs = devices or list_block_devices()
    results = {d: check_device(d) for d in devs}
    if json_out:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if not devs:
        print("Устройства не найдены")
        return 0
    for d, data in results.items():
        if isinstance(data, dict) and "_summary" in data:
            status = data["_summary"]["passed"]
            if status is True:
                print(f"{d}: SMART OK")
            elif status is False:
                print(f"{d}: SMART FAIL/WARN")
            else:
                print(f"{d}: SMART неизвестен")
        else:
            err = data.get("error") if isinstance(data, dict) else "unknown"
            print(f"{d}: ошибка проверки ({err})")
    return 0
