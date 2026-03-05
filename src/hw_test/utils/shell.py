import subprocess

def run(cmd, check=False):
    proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{proc.stdout.decode('utf-8', errors='ignore')}")
    return proc.stdout.decode("utf-8", errors="ignore")
