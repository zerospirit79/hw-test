import argparse, sys
from pathlib import Path
from hw_test.diag import run as diag_run
from hw_test.collect import run as collect_run
from hw_test.smart import run as smart_run
from hw_test.sensors import run as sensors_run
from hw_test.bench import run as bench_run

def project_root() -> Path:
    # hw_test/ -> python/ -> <repo root>
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

    # bench (CPU/RAM/IO)
    p_bench = subparsers.add_parser("bench", help="Запустить набор тестов производительности", description="CPU, RAM и I/O бенчмарки",)
    p_bench.add_argument("--duration", type=int, default=15, help="Длительность CPU‑теста, сек")
    p_bench.add_argument("--cpus", type=int, default=0, help="Число потоков CPU (0 = все)")
    p_bench.add_argument("--ram-mb", type=int, default=512, help="Объём на процесс RAM‑теста, МБ")
    p_bench.add_argument("--io-size-mb", type=int, default=1024, help="Объём I/O, МБ")
    p_bench.add_argument("--tmpdir", default=None, help="Каталог для временных файлов")
    p_bench.add_argument("--json", action="store_true", help="JSON‑вывод")
    p_bench.set_defaults(handler=lambda ns: bench_run(
        json_out=ns.json,
        duration=ns.duration,
        cpus=ns.cpus,
        ram_mb=ns.ram_mb,
        io_size_mb=ns.io_size_mb,
        tmpdir=ns.tmpdir
    ))
    ns = parser.parse_args()
    rc = ns.handler(ns)
    if isinstance(rc, int):
        sys.exit(rc)
