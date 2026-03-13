import time, json
from typing import List, Dict, Any
from .registry import REGISTRY
from . import tests as _tests  # noqa: F401  # ensure imports
from ..utils import logging as _logsetup

def run_suite(suites: List[str], ctx: Dict[str,Any] | None = None) -> Dict[str,Any]:
    ctx = ctx or {}
    results: Dict[str,Any] = {"suites": suites, "tests": []}
    # Простая логика: basic включает net.ping_external
    plan: List[str] = []
    for s in suites:
        if s == "basic":
        plan.append("net.ping_external")
    for name in plan:
        cls = REGISTRY.get(name)
        if not cls:
            results["tests"].append({"name": name, "ok": False, "error": "unknown test"})
            continue
        t0 = time.time()
        try:
            res = cls().run(ctx)
            ok = bool(res.get("ok", False))
            results["tests"].append({"name": name, "ok": ok, "data": res})
        except Exception as e:
            results["tests"].append({"name": name, "ok": False, "error": str(e)})
        results["tests"][-1]["elapsed_s"] = round(time.time() - t0, 3)
    return results
