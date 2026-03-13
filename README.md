hw-test — инструмент для экспресс‑проверки рабочих станций ALT Linux (p10/p11/c10f2/c11f1).

Быстрый старт:
1. python3 -m pip install -e .
2. hw-test --help
3. hw-test --branch p11 --mode online --finish -n TEST
## PC Test интеграция

- Импортировано содержимое репозитория pc-test в tools/pc-test.
- Добавлен единый Python CLI:
  - Установка зависимостей:
    ```
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    ```
  - Запуск:
    ```
    ./scripts/pc-test --help
    ./scripts/pc-test diag
    ./scripts/pc-test collect --out ./logs
    # универсальный режим вызова bash-скриптов
    ./scripts/pc-test run scripts/diag.sh -- --json
    ```
- Постепенная миграция bash → Python: логику переносим в python/pc_test/*.py и
  подменяем обработчики команд в python/pc_test/cli.py.

Примеры SMART:
```
./scripts/pc-test smart
./scripts/pc-test smart --dev /dev/sda --dev /dev/nvme0n1 --json
```
