from pathlib import Path
import tarfile, time, shutil

def collect_logs(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    # journalctl
    try:
        import subprocess
        with open(outdir / "journal.txt", "w", encoding="utf-8") as f:
            subprocess.run(["journalctl","-b","-x"], stdout=f, stderr=subprocess.STDOUT, check=False)
    except Exception:
        pass

def finalize(name: str = "TEST", srcdir: Path = Path.home() / "PC-TEST"):
    ts = time.strftime("%Y%m%d-%H%M%S")
    tarpath = Path.home() / f"hw-test-{name}-{ts}.tar.gz"
    with tarfile.open(tarpath, "w|gz") as tar:
        if srcdir.exists():
            tar.add(srcdir, arcname=srcdir.name)
    mnt = Path("/mnt/pc-test")
    if mnt.exists():
        shutil.copy2(tarpath, mnt / tarpath.name)
