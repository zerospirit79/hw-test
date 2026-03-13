import subprocess, shlex, os, logging
from typing import Union, Sequence, Optional

log = logging.getLogger("pc_test.cmd")

def run_cmd(cmd: Union[str, Sequence[str]],
            check: bool = True,
            capture: bool = True,
            env: Optional[dict] = None,
            timeout: Optional[int] = None):
    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = list(cmd)
    log.debug("Run: %s", " ".join(args))
    p = subprocess.run(args, capture_output=capture, text=True, env=env, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(args)}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p
