from __future__ import annotations
import subprocess, shlex

def run_cmd(cmd: list[str] | str, timeout: int = 15, check: bool = False, text: bool = True):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        cp = subprocess.run(cmd, capture_output=True, text=text, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return {"rc": 124, "stdout": "", "stderr": f"timeout: {e}"}
    if check and cp.returncode != 0:
        return {"rc": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr or "non-zero exit"}
    return {"rc": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
