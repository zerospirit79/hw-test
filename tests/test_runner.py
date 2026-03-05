import subprocess
import sys
import pathlib


def test_scenarios():
    repo = pathlib.Path(__file__).parent
    scripts = [
        "s05_prechecks.py",
        "s06_repo_switch.py",
        "s07_upgrade.py",
        "s08_hw_collect.py",
        "s09_express_test.py",
        "s10_01_basic_checks.py",
        "s10_11_final_logs.py",
        "s11_01_user_session.py",
        "s11_02_multimedia_keys.py",
    ]

    for name in scripts:
        ret = subprocess.run(
            [sys.executable, str(repo / name)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert ret.returncode == 0, (
            f"{name} failed:\n"
            f"stdout:\n{ret.stdout}\n"
            f"stderr:\n{ret.stderr}"
        )
