import json
from pathlib import Path

def load_locale(lang="ru"):
    base = Path(__file__).resolve().parents[2] / "data" / "locale"
    path = base / f"{lang}.json"
    if not path.exists():
        path = base / "en.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
