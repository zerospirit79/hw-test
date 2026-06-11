"""Загрузка /etc/hw-test.conf, ~/.config/hw-test.conf и STATE/settings.ini.

Формат: key=value, комментарии с #, списки в скобках (local_media_labels).
Неизвестные ключи игнорируются; применяются только атрибуты RuntimeContext.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

# Saved in STATE/settings.ini must not override CLI launch flags on --continue.
SETTINGS_INI_SKIP_KEYS = frozenset({"batchmode", "disable_autorun"})


def _apply_line(ctx: Any, line: str) -> None:
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if "=" not in line:
        return
    key, _, raw = line.partition("=")
    key = key.strip()
    raw = raw.strip()
    if not key or not hasattr(ctx, key):
        return
    if raw.startswith("(") and raw.endswith(")"):
        try:
            value = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            value = raw
    else:
        value = raw.strip("'\"")
    setattr(ctx, key, value)


def load_config_files(ctx: Any, *paths: Path, skip_keys: frozenset[str] | None = None) -> None:
    ignored = skip_keys or frozenset()
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key = line.strip().split("=", 1)[0].strip() if "=" in line else ""
            if key in ignored:
                continue
            _apply_line(ctx, line)


def detect_langid() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            base = val.split(".")[0].split("_")[0]
            if base:
                return base
    return "en"
