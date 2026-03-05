from pathlib import Path

def load_video_set(name: str):
    base = Path(__file__).resolve().parents[2]
    mapping = {
        "youtube": base / "data" / "youtube.txt",
        "rv": base / "data" / "rvsets.txt",
    }
    path = mapping.get(name, mapping["youtube"])
    if path.exists():
        return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith('#')]
    return ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
