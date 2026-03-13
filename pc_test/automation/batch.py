import json, logging
from typing import Any, Dict, List
from ..sysinfo import os_info
from ..repo.alt_repo import configure_by_info, dist_upgrade
from ..testsuite.runner import run_suite

log = logging.getLogger("pc_test.batch")

def run_batch(profile_json: str) -> Dict[str,Any]:
    profile = json.loads(profile_json) if isinstance(profile_json, str) else profile_json
    info = os_info.collect()

    source = profile.get("repo_source","internet")
    mirror = profile.get("mirror_url")
    auto_up = profile.get("auto_upgrade_on_boot", True)

    configure_by_info(info, source=source, mirror_url=mirror)
    if auto_up:
        dist_upgrade()

    suites: List[str] = profile.get("tests", ["basic"])
    results = run_suite(suites)

    report = {
        "system": info,
        "tests": results,
        "profile": profile,
    }
    return report
