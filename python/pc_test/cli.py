import argparse
import subprocess
import sys
from pathlib import Path

def project_root() -> Path:
    # python/pc_test/ -> python/ -> <repo root>
    return Path(__file__).resolve().parents[2]

def run_bash(relative_path, *args) -> int:
    script = project_root() / "tools" / "pc-test" / relative_path
    if not script.exists():
        print(f"Ошибка: не найден скрипт {script}", file=sys.stderr)
        return 1
    cmd = [str(script), *[str(a) for a in args if a != ""]]
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print(f"Ошибка: не удалось выполнить {cmd[0]} (нет прав или отсутствует)", file=sys.stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(prog="pc-test", description="Unified hardware test CLI (migration to Python)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Примеры команд. Подставьте реальные пути скриптов из pc-test:
    # Ниже добавлены универсальные заглушки, чтобы вы могли быстро подцепить свои скрипты.
    p_passthrough = subparsers.add_parser("run", help="Запустить bash-скрипт из tools/pc-test по относительному пути")
    p_passthrough.add_argument("path", help="Относительный путь внутри tools/pc-test (например, scripts/diag.sh)")
    p_passthrough.add_argument("args", nargs=argparse.REMAINDER, help="Аргументы для скрипта")
    p_passthrough.set_defaults(handler=lambda ns: run_bash(ns.path, *ns.args))

    # Пример целевых алиасов (замените/добавьте конкретику):
    # diag
    p_diag = subparsers.add_parser("diag", help="Диагностика (пока вызывает bash)")
    p_diag.add_argument("--json", action="store_true", help="Вывод JSON (если поддерживается)")
    p_diag.set_defaults(handler=lambda ns: run_bash("scripts/diag.sh", "--json" if ns.json else ""))

    # collect
    p_collect = subparsers.add_parser("collect", help="Сбор логов (пока вызывает bash)")
    p_collect.add_argument("--out", default="logs", help="Каталог для логов")
    p_collect.set_defaults(handler=lambda ns: run_bash("scripts/collect.sh", "--out", ns.out))

    ns = parser.parse_args()
    rc = ns.handler(ns)
    if isinstance(rc, int):
        sys.exit(rc)
