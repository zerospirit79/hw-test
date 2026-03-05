import argparse
from .main import run

def build_parser():
    p = argparse.ArgumentParser("hw-test")
    p.add_argument("--branch", choices=["p10","p11","c10f2","c11f1"], help="Целевая ветка ALT Linux")
    p.add_argument("--mode", choices=["online","mirror","offline"], default="online", help="Режим источников пакетов")
    p.add_argument("--mirror-url", help="URL зеркала для mirror/offline")
    p.add_argument("--batch", action="store_true", help="Неблокирующий режим")
    p.add_argument("--continue", "-C", dest="cont", action="store_true", help="Продолжить сценарий")
    p.add_argument("--finish", "-F", action="store_true", help="Финализировать и собрать архив")
    p.add_argument("--preferred-browser", help="Браузер для видео (firefox/chromium)")
    p.add_argument("--no-suspend-mask", action="store_true", help="Не маскировать sleep/suspend")
    p.add_argument("--name", "-n", help="Имя отчёта (например, INVENTORY123)")
    return p

def main():
    args = build_parser().parse_args()
    run(args)
