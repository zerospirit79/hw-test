# Руководство разработчика hw-test

hw-test — инструмент автоматизации тестирования совместимости оборудования с ALT Linux
(методика Basealt SPO, наследие pc-test). Код на Python 3 заменяет прежние bash-скрипты шагов.

## Структура пакета

```
python3/hw_test/
├── main.py           # Точка входа, цикл шагов, завершение тестирования
├── cli.py            # Разбор аргументов командной строки
├── context.py        # RuntimeContext — глобальное состояние и shell-совместимые хелперы
├── config_loader.py  # Загрузка /etc/hw-test.conf и settings.ini
├── constants.py      # Коды статусов шагов (TEST_PASSED, TEST_SKIPPED, …)
├── internal_vars.py  # Ключи, сохраняемые в STATE/settings.ini
├── paths.py          # Пути установки (libexec, l10n)
├── launch_mode.py    # Режимы запуска: start, continue, finish, retest
├── user_handoff.py   # Переключение root → пользователь между шагами
├── steps/            # Модули шагов методики (prepare, detect, express, …)
├── gui/              # Диалоги yad/dialog для конфигурации
├── de_terminal.py    # Запуск в графическом терминале (kgx, konsole)
├── resume_autorun.py # Автопродолжение после перезагрузки
└── …
```

Установленные данные: `var/lib/hw-test/` (планы шагов), `usr/libexec/hw-test/l10n/` (локализация).

## Жизненный цикл запуска

1. `main()` создаёт `RuntimeContext`, загружает конфиги, разбирает CLI (`cli.parse_args`).
2. `resolve_launch_mode()` определяет режим по `~/HW-TEST` и флагам (`--start`, `--continue`, …).
3. Для нового прогона `start_new_run()` создаёт рабочий каталог и симлинк `~/HW-TEST`.
4. `run_main_loop()` выполняет шаги из плана до его исчерпания.
5. `_final_message()` сообщает о паузе, завершении первой фазы или создании архива.

## Рабочий каталог

Типичный путь: `~/.local/share/hw-test/ГГГГ-ММ-ДД/`. Симлинк `~/HW-TEST` указывает на него.

```
HW-TEST/
├── hw-test.log       # Журнал
├── xorg.log          # События X11/Wayland
├── STATE/
│   ├── start.txt     # План первой фазы (копия из /var/lib/hw-test/)
│   ├── finish.txt    # План финальной фазы (--finish)
│   ├── STEP          # Имя текущего шага (модуль в steps/)
│   ├── STATUS        # Код результата последнего шага
│   ├── NUMBER        # Номер раздела методики
│   ├── RESULTS       # Накопленные результаты (код TAB step_id)
│   └── settings.ini  # Снимок настроек RuntimeContext
└── TMP-ROOT/         # Временные артефакты root-шагов (переносятся в workdir)
```

## Формат плана шагов

Строки в `start.txt` / `finish.txt` (`/var/lib/hw-test/`):

```
<роль>	<step_id>
```

Роли:

| Роль   | Значение |
|--------|----------|
| `root` | Шаг выполняется от root (через sudo или перезапуск) |
| `user` | Только обычный пользователь (графика, экспресс-тест) |
| `both` | Допустимы оба; при root возможна передача сессии пользователю |

Пример (`var/lib/hw-test/start.txt`): `root prepare`, `both config`, `user express`.

## Интерфейс шага

Каждый шаг — класс в `steps/`, наследник `StepBase`, зарегистрированный через `@register_step`:

```python
@register_step
class MyStep(StepBase):
    STEP_ID = "my_step"      # имя модуля и значение в STATE/STEP
    number = "5.5"           # номер в методике
    en_name = "English title"
    ru_name = "Русское название"

    def pre(self) -> int:
        # Проверки до запуска; TEST_SKIPPED / TEST_BLOCKED / TEST_ALLOWED
        return TEST_ALLOWED

    def testcase(self) -> int:
        # Основная логика; TEST_PASSED или TEST_FAILED
        return TEST_PASSED

    def show_results(self, rc: int, *, log: bool = True) -> None:
        # Дополнительный вывод в лог (опционально)
        pass
```

Регистрация происходит при импорте модуля в `steps/__init__.py`. Новый шаг: создать файл, добавить импорт, строку в `var/lib/hw-test/start.txt` или `finish.txt`.

## Коды статусов

См. `constants.py`. Основные значения:

| Константа      | Код | Смысл |
|----------------|-----|-------|
| `TEST_PASSED`  | 0   | Успех |
| `TEST_FAILED`  | 128 | Ошибка |
| `TEST_SKIPPED` | 129 | Пропущен (нет условий) |
| `TEST_BLOCKED` | 130 | Заблокирован (нет GUI и т.п.) |
| `TEST_RUNNING` | 131 | Выполняется (только для вывода) |

## Флаги настроек

Атрибуты `RuntimeContext` для опциональных тестов — строки: `""` = выкл., `"1"` = вкл. (совместимость с bash и `settings.ini`). Расшифровка — в `internal_vars.SETTINGS_KEY_HELP`.

Обнаружение оборудования (`steps/detect.py`) выставляет флаги по наличию устройств; шаг `install` доустанавливает пакеты; последующие шаги проверяют флаги в `pre()`.

## Конфигурация

Порядок загрузки (поздний перекрывает ранний):

1. `/etc/hw-test.conf`
2. Аргументы CLI
3. `~/.config/hw-test.conf`
4. `STATE/settings.ini` (при `--continue`, кроме `batchmode` / `disable_autorun`)

## Переключение root ↔ user

Некоторые шаги требуют графической сессии пользователя. `user_handoff.py` и `de_terminal.py`:

- снижение привилегий в том же процессе (`setuid`);
- открытие второго терминала в сессии пользователя;
- запуск на VT для текстового `dialog`;
- systemd / autostart для продолжения после reboot.

## Тесты

```bash
cd /path/to/hw-test
python3 -m pytest tests/ -q
```

Модульные тесты мокают файловую систему и subprocess; при изменении контрактов шагов обновляйте соответствующие файлы в `tests/`.

## Полезные команды для отладки

```bash
hw-test --help
hw-test --batch --start          # сервер без GUI
hw-test --continue               # продолжить с ~/HW-TEST
less -r ~/HW-TEST/hw-test.log
```
