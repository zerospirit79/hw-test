import argparse, sys
from pathlib import Path
from pc_test.diag import run as diag_run
from pc_test.collect import run as collect_run
from pc_test.smart import run as smart_run
from pc_test.sensors import run as sensors_run

def project_root() -> Path:
    # python/pc_test/ -> python/ -> <repo root>
    return Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(prog="pc-test", description="Hardware test CLI (Python migration)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # diag (Python)
    p_diag = subparsers.add_parser("diag", help="Диагностика (Python)")
    p_diag.add_argument("--json", action="store_true", help="JSON-вывод")
    p_diag.add_argument("--lshw", action="store_true", help="Добавить lshw -json")
    p_diag.set_defaults(handler=lambda ns: diag_run(json_out=ns.json, include_lshw=ns.lshw))

    # collect (Python)
    p_collect = subparsers.add_parser("collect", help="Сбор логов (Python)")
    p_collect.add_argument("--out", default="logs", help="Каталог для логов")
    p_collect.add_argument("--json", action="store_true", help="JSON-вывод")
    p_collect.set_defaults(handler=lambda ns: collect_run(out=ns.out, json_out=ns.json))

    # универсальный режим для оставшихся bash-скриптов
    # smart (Python)
    p_smart = subparsers.add_parser("smart", help="Проверка S.M.A.R.T. устройств")
    p_smart.add_argument("--dev", action="append", help="Устройство (можно несколько флагов --dev)")
    p_smart.add_argument("--json", action="store_true", help="JSON-вывод")
    p_smart.set_defaults(handler=lambda ns: smart_run(devices=ns.dev, json_out=ns.json))

    p_run = subparsers.add_parser("run", help="Запустить bash-скрипт из tools/pc-test по относительному пути")
    p_run.add_argument("path", help="Относительный путь внутри tools/pc-test (например, scripts/legacy.sh)")
    p_run.add_argument("args", nargs=argparse.REMAINDER, help="Аргументы для скрипта")
    def _run_bash(ns):
        script = project_root() / "tools" / "pc-test" / ns.path
        if not script.exists():
            print(f"Ошибка: не найден скрипт {script}", file=sys.stderr)
            return 1
        import subprocess
        cmd = [str(script), *[str(a) for a in ns.args if a != ""]]
        try:
            return subprocess.call(cmd)
        except FileNotFoundError:
            print(f"Ошибка: не удалось выполнить {cmd[0]} (нет прав или отсутствует)", file=sys.stderr)
            return 1
    p_run.set_defaults(handler=_run_bash)

    ns = parser.parse_args()
    rc = ns.handler(ns)
    if isinstance(rc, int):
        sys.exit(rc)
