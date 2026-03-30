"""CLI entry point for HW-Test."""

import argparse
import logging
import sys
import os
import json
from datetime import datetime
from typing import List, Optional

from hw_test import __version__
from hw_test.types import TestConfig, TestStatus, HardwareInfo
from hw_test.steps import (
    AVAILABLE_STEPS,
    DEFAULT_STEP_ORDER,
    get_step_class,
)
from hw_test.auth import (
    authenticate_root,
    run_as_root,
    is_root_authenticated,
    get_authenticator,
)
from hw_test.state import get_test_state, TestState
from hw_test.l10n import get_l10n, _
from hw_test.dialogs import DialogManager


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    return logging.getLogger("hw_test")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="hw-test",
        description="Hardware compatibility testing tool for ALT Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hw-test --start                    # Run all tests interactively
  hw-test --start --batch            # Run all tests in batch mode
  hw-test --start --steps hardware_detection,express_test
  hw-test --list-steps               # Show available test steps
  hw-test --version                  # Show version
        """,
    )

    # Main modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--start", action="store_true", help="Start hardware testing")
    mode_group.add_argument("--list-steps", action="store_true", help="List available test steps")

    # Options
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--batch", action="store_true", help="Run in batch mode (no interactive prompts)"
    )
    parser.add_argument(
        "--name", type=str, default="default", help="Test session name (default: default)"
    )
    parser.add_argument(
        "--steps", type=str, help="Comma-separated list of steps to run (default: all)"
    )
    parser.add_argument("--skip", type=str, help="Comma-separated list of steps to skip")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/var/lib/hw-test",
        help="Directory for output files (default: /var/lib/hw-test)",
    )
    parser.add_argument("--log-file", type=str, help="Log file path (default: stdout only)")
    parser.add_argument(
        "--timeout", type=int, default=3600, help="Global timeout in seconds (default: 3600)"
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=["en", "ru"],
        default="ru",
        help="Interface language (default: ru)",
    )

    return parser


def list_steps() -> None:
    """Print available test steps."""
    print("\nAvailable test steps:")
    print("-" * 50)

    for step_name in DEFAULT_STEP_ORDER:
        step_class = get_step_class(step_name)
        if step_class:
            print(f"\n  {step_name}")
            print(f"    Description: {step_class.description}")
            print(f"    Requires root: {'Yes' if step_class.required_privileges else 'No'}")

    print("\n" + "-" * 50)
    print(f"Total: {len(AVAILABLE_STEPS)} steps")


def show_test_menu(config: TestConfig) -> List[str]:
    """
    Show interactive test selection menu using GUI (yad) or TUI (dialog).

    Returns:
        List of selected test steps
    """
    from hw_test.auth import run_as_root

    l10n = get_l10n()
    dm = DialogManager()

    # Detect available capabilities
    capabilities = {}

    # Check for fwupd
    _, _, rc = run_as_root(["which", "fwupdmgr"])
    capabilities["fwupd"] = rc == 0

    # Check for NUMA
    stdout, _, rc = run_as_root(["lscpu", "--parse=NODE"])
    if rc == 0:
        nodes = set()
        for line in stdout.split("\n"):
            if line and not line.startswith("#"):
                parts = line.split(",")
                if len(parts) >= 1 and parts[0].isdigit():
                    nodes.add(parts[0])
        capabilities["numa"] = len(nodes) > 1

    # Check for webcams
    stdout, _, rc = run_as_root(["ls", "/dev/video*"], timeout=5)
    capabilities["webcam"] = rc == 0 and "/dev/video" in stdout

    # Check for fingerprint
    stdout, _, rc = run_as_root(["lsusb"])
    capabilities["fingerprint"] = rc == 0 and any(
        kw in stdout.lower() for kw in ["fingerprint", "goodix", "validity"]
    )

    # Check for Bluetooth
    _, _, rc = run_as_root(["which", "bluetoothctl"])
    capabilities["bluetooth"] = rc == 0

    # Check for IPMI
    _, _, rc = run_as_root(["which", "ipmitool"])
    capabilities["ipmi"] = rc == 0

    # Check for smartcard
    _, _, rc = run_as_root(["which", "pcsc_scan"])
    capabilities["smartcard"] = rc == 0

    # Test categories with descriptions
    test_categories = [
        (
            "Базовые тесты",
            [
                ("hardware_detection", "Определение оборудования", True),
                ("system_check", "Проверка системы", True),
                ("log_collection", "Сбор логов", True),
                ("firmware_check", "Проверка прошивок", capabilities.get("fwupd", False)),
            ],
        ),
        (
            "Тесты производительности",
            [
                ("performance", "Бенчмарки (CPU, память, диск)", True),
                ("diskperf", "Тест диска", True),
                ("glmark", "Тест графики", True),
                ("cpupower", "Тест управления питанием CPU", True),
            ],
        ),
        (
            "Экспресс-тесты",
            [
                ("express_test", "Экспресс-тестирование", True),
            ],
        ),
        (
            "Специальные тесты",
            [
                ("syslogs", "Анализ системных логов", True),
                ("numa_test", "NUMA топология", capabilities.get("numa", False)),
                ("webcam_test", "Веб-камеры", capabilities.get("webcam", False)),
                ("fingerprint_test", "Сканеры отпечатков", capabilities.get("fingerprint", False)),
                ("bluetooth_test", "Bluetooth", capabilities.get("bluetooth", False)),
                ("ipmi_test", "IPMI/BMC", capabilities.get("ipmi", False)),
                ("smartcard_test", "Смарт-карты", capabilities.get("smartcard", False)),
            ],
        ),
        (
            "Обновление системы",
            [
                ("upgrade", "Обновление системы", True),
                ("prepare", "Подготовка системы", True),
            ],
        ),
    ]

    # Build menu text
    menu_title = "Выбор параметров тестирования"
    menu_text = "Выберите тесты для выполнения:\n\n"

    # Build checklist for GUI or menu for TUI
    if dm.gui_available:
        # Build yad checklist
        yad_cmd = [
            "yad",
            "--form",
            "--title",
            menu_title,
            "--width",
            "600",
            "--height",
            "500",
            "--button",
            "gtk-ok:0",
            "--button",
            "gtk-cancel:1",
        ]

        # Add preset modes as radio buttons
        yad_cmd.extend(
            [
                "--field=Полный тест:RB",
                "TRUE",
                "--field=Базовый тест:RB",
                "FALSE",
                "--field=Экспресс тест:RB",
                "FALSE",
                "--field=Выбрать вручную:RB",
                "FALSE",
            ]
        )

        # Add test checkboxes
        for category, tests in test_categories:
            yad_cmd.extend(["", ""])  # Separator
            for test_id, test_name, available in tests:
                if available:
                    yad_cmd.extend([f"--field={test_name}:FLT", "TRUE"])

        # Run yad
        import subprocess

        try:
            result = subprocess.run(yad_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Parse output
                output = result.stdout.strip().split("|")
                # Get selected preset
                preset = output[0] if output else "1"
                if "Полный" in preset:
                    return DEFAULT_STEP_ORDER.copy()
                elif "Базовый" in preset:
                    return ["hardware_detection", "system_check", "log_collection"]
                elif "Экспресс" in preset:
                    return ["express_test", "hardware_detection", "log_collection"]
                else:
                    # Manual selection - parse checkboxes
                    selected = []
                    idx = 4  # After preset radio buttons
                    for category, tests in test_categories:
                        for test_id, test_name, available in tests:
                            if available and idx < len(output):
                                if output[idx].strip().upper() == "TRUE":
                                    if test_id in DEFAULT_STEP_ORDER:
                                        selected.append(test_id)
                            idx += 1
                    return selected if selected else DEFAULT_STEP_ORDER.copy()
            else:
                # Cancelled
                return DEFAULT_STEP_ORDER.copy()
        except Exception as e:
            print(f"GUI dialog failed: {e}")
            # Fallback to TUI
            dm.tui_available = True

    # TUI fallback using dialog
    if dm.tui_available:
        # Show preset selection first
        preset_result = dm.run_command(
            [
                "dialog",
                "--stdout",
                "--title",
                menu_title,
                "--menu",
                "Выберите режим тестирования:",
                "20",
                "70",
                "4",
                "1",
                "Полный тест (все доступные)",
                "2",
                "Базовый тест (минимальный)",
                "3",
                "Экспресс тест",
                "4",
                "Выбрать вручную",
            ]
        )

        if preset_result[0] != 0:
            return DEFAULT_STEP_ORDER.copy()

        choice = preset_result[1]

        if choice == "1":
            dm.msgbox("Выбран полный режим", menu_title)
            return DEFAULT_STEP_ORDER.copy()
        elif choice == "2":
            dm.msgbox("Выбран базовый режим", menu_title)
            return ["hardware_detection", "system_check", "log_collection"]
        elif choice == "3":
            dm.msgbox("Выбран экспресс режим", menu_title)
            return ["express_test", "hardware_detection", "log_collection"]
        elif choice == "4":
            # Manual selection - build checklist
            menu_items = []
            for category, tests in test_categories:
                for test_id, test_name, available in tests:
                    if available and test_id in DEFAULT_STEP_ORDER:
                        menu_items.extend([test_id, test_name, "OFF"])

            if menu_items:
                result = dm.run_command(
                    [
                        "dialog",
                        "--stdout",
                        "--title",
                        menu_title,
                        "--checklist",
                        "Выберите тесты (пробел для выбора):",
                        "25",
                        "80",
                        "15",
                    ]
                    + menu_items
                )

                if result[0] == 0 and result[1]:
                    selected = result[1].replace('"', "").split()
                    dm.msgbox(f"Выбрано тестов: {len(selected)}", menu_title)
                    return selected

            return DEFAULT_STEP_ORDER.copy()

    # Fallback to text-based menu
    print("\n" + "=" * 60)
    print("МЕНЮ ВЫБОРА ПАРАМЕТРОВ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print()

    print("Предустановленные режимы:")
    print("  [1] Полный тест (все доступные)")
    print("  [2] Базовый тест (минимальный)")
    print("  [3] Экспресс тест")
    print()

    while True:
        try:
            choice = input("Выберите режим (1-3) [по умолчанию 1]: ").strip()
            if not choice:
                choice = "1"

            if choice == "1":
                print("\n✓ Выбран полный режим")
                return DEFAULT_STEP_ORDER.copy()
            elif choice == "2":
                print("\n✓ Выбран базовый режим")
                return ["hardware_detection", "system_check", "log_collection"]
            elif choice == "3":
                print("\n✓ Выбран экспресс режим")
                return ["express_test", "hardware_detection", "log_collection"]
            else:
                print("Неверный выбор. Попробуйте снова.")

        except (KeyboardInterrupt, EOFError):
            print("\n\n✗ Выбор отменён пользователем.")
            return DEFAULT_STEP_ORDER.copy()


def run_tests(
    config: TestConfig, logger: logging.Logger, test_state: Optional[TestState] = None
) -> int:
    """Run the test suite."""
    logger.info(f"Starting HW-Test v{__version__}")
    logger.info(f"Test name: {config.name}")
    logger.info(f"Batch mode: {config.batch_mode}")

    # Initialize or load state
    is_resumed = False
    if test_state is None:
        test_state = get_test_state(config)

    if test_state.load() and test_state.is_resumed_test():
        is_resumed = True
        logger.info("Обнаружен предыдущий сеанс теста. Возобновление...")
        summary = test_state.get_summary()
        print(f"\n↻ Возобновление теста после перезагрузки")
        print(f"  Имя теста: {summary['test_name']}")
        print(f"  Выполнено шагов: {summary['completed_steps']}")
        print(f"  Перезагрузок: {summary['reboot_count']}")
        if summary.get("reboot_reason"):
            print(f"  Причина перезагрузки: {summary['reboot_reason']}")
        print()

        # Clear reboot flag after reboot
        test_state.clear_reboot_flag()
    else:
        # Initialize new test state
        steps_to_run = config.steps_to_run if config.steps_to_run else DEFAULT_STEP_ORDER.copy()
        test_state.initialize(config.name, steps_to_run)
        logger.info("Новый сеанс теста.")

    # Determine steps to execute
    if config.steps_to_run and not is_resumed:
        steps_to_execute = config.steps_to_run
    else:
        steps_to_execute = test_state.state.get("steps_to_run", DEFAULT_STEP_ORDER.copy())

    # Remove skipped steps
    if config.skip_steps:
        steps_to_execute = [s for s in steps_to_execute if s not in config.skip_steps]

    # Skip already completed steps when resuming
    if is_resumed:
        completed = set(test_state.state.get("completed_steps", []))
        failed = set(test_state.state.get("failed_steps", []))
        steps_to_execute = [s for s in steps_to_execute if s not in completed and s not in failed]
        logger.info(f"Пропущено {len(completed) + len(failed)}已完成 шагов")

    logger.info(f"Выполнение {len(steps_to_execute)} шагов: {', '.join(steps_to_execute)}")

    # Initialize hardware info (will be populated by first step)
    hardware_info = HardwareInfo()

    # Execute steps
    results = []
    failed_count = 0
    warning_count = 0
    reboot_requested = False
    reboot_reason = None

    for step_name in steps_to_execute:
        step_class = get_step_class(step_name)

        if not step_class:
            logger.warning(f"Неизвестный шаг: {step_name}, пропускаем...")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Выполнение шага: {step_name}")
        logger.info(f"{'='*60}")

        # Mark step as started
        test_state.mark_step_started(step_name)

        try:
            step = step_class(config=config, hardware_info=hardware_info)
            result = step.run()
            results.append(result)

            # Update hardware info for subsequent steps
            if hasattr(step, "detected_hardware"):
                hardware_info = step.detected_hardware
                test_state.set_hardware_info(
                    {
                        "cpu_model": hardware_info.cpu_model,
                        "cpu_cores": hardware_info.cpu_cores,
                        "total_memory_mb": hardware_info.total_memory_mb,
                    }
                )

            # Mark step completed
            if not test_state.mark_step_completed(step_name, result):
                logger.error("Не удалось сохранить состояние после шага %s", step_name)
                print(f"\n✗ Предупреждение: Не удалось сохранить состояние после шага {step_name}")
                print("  Тест продолжится, но состояние может быть потеряно при перезагрузке.")

            # Count results
            if result.status == TestStatus.FAILED or result.status == TestStatus.ERROR:
                failed_count += 1
            elif result.status == TestStatus.WARNING:
                warning_count += 1

            # Print summary for this step
            print(f"\n[{result.status.value.upper()}] {step_name}: {result.message}")
            if result.duration_seconds > 0:
                print(f"  Длительность: {result.duration_seconds:.2f}s")

            if result.warnings:
                for w in result.warnings:
                    print(f"  ⚠ Предупреждение: {w}")

            if result.errors:
                for e in result.errors:
                    print(f"  ✗ Ошибка: {e}")

            # Check if reboot was requested (from reboot step)
            if (
                step_name in ["reboot", "reboot_and_continue"]
                and result.status == TestStatus.PASSED
            ):
                reboot_requested = True
                reboot_reason = result.details.get("reboot_reason", "Перезагрузка запрошена тестом")
                if not test_state.mark_reboot_required(reboot_reason):
                    logger.error("Не удалось сохранить состояние перед перезагрузкой!")
                    print("\n✗ Ошибка: Не удалось сохранить состояние теста.")
                    print("  Перезагрузка отменена до устранения проблемы с правами доступа.")
                    return 1

        except Exception as e:
            logger.exception(f"Шаг {step_name} завершился ошибкой: {e}")
            test_state.mark_step_failed(step_name, str(e))
            failed_count += 1
            print(f"\n[ERROR] {step_name}: {str(e)}")

        # Check if reboot is required
        if test_state.state.get("requires_reboot"):
            print(f"\n⚠ Требуется перезагрузка: {test_state.state.get('reboot_reason')}")
            print("Состояние теста сохранено. Тест продолжится автоматически после перезагрузки.")

            # Actually trigger reboot if reboot step was executed
            if reboot_requested and not is_resumed:
                print("\n⟳ Выполняется перезагрузка системы...")
                print("После загрузки системы тест продолжится автоматически.")
                import time

                time.sleep(3)

                # Execute reboot as root
                from hw_test.auth import run_as_root

                run_as_root(["shutdown", "-r", "now", "HW-Test: плановая перезагрузка"])

                # If we get here, reboot failed
                print(
                    "⚠ Не удалось выполнить перезагрузку. Пожалуйста, перезагрузите систему вручную."
                )
                print(f"  Для продолжения теста выполните: hw-test --start --name {config.name}")

            return 0

    # Final summary
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)

    summary = test_state.get_summary()
    print(f"Всего шагов выполнено: {summary['completed_steps']}")
    print(f"Успешно: {summary['completed_steps'] - summary['failed_steps']}")
    print(f"Предупреждений: {warning_count}")
    print(f"Ошибок: {summary['failed_steps']}")
    print(f"Перезагрузок: {summary['reboot_count']}")

    if summary["failed_steps"] > 0:
        print("\n⚠ Некоторые тесты завершились ошибкой. Проверьте логи.")
        test_state.finalize("failed")
        return 1
    elif summary["requires_reboot"]:
        print("\n⟳ Требуется перезагрузка для продолжения теста.")
        return 0
    elif warning_count > 0 or summary["skipped_steps"] > 0:
        print("\n✓ Тестирование завершено с предупреждениями.")
        test_state.finalize("completed")
        test_state.cleanup()
        return 0
    else:
        print("\n✓ Все тесты успешно пройдены!")
        test_state.finalize("completed")
        test_state.cleanup()
        return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --list-steps
    if args.list_steps:
        list_steps()
        return 0

    # Require --start for running tests
    if not args.start:
        parser.print_help()
        return 1

    # Setup logging
    logger = setup_logging(verbose=args.verbose, log_file=args.log_file)

    # Parse steps
    steps_to_run = []
    if args.steps:
        steps_to_run = [s.strip() for s in args.steps.split(",")]
        # Validate steps
        for step in steps_to_run:
            if step not in AVAILABLE_STEPS:
                print(f"Ошибка: Неизвестный шаг '{step}'")
                print(f"Доступные шаги: {', '.join(AVAILABLE_STEPS.keys())}")
                return 1

    skip_steps = []
    if args.skip:
        skip_steps = [s.strip() for s in args.skip.split(",")]

    # Create configuration
    config = TestConfig(
        name=args.name,
        batch_mode=args.batch,
        verbose=args.verbose,
        data_dir=args.output_dir,
        log_dir=os.path.join(args.output_dir, "logs"),
        steps_to_run=steps_to_run,
        skip_steps=skip_steps,
        timeout_seconds=args.timeout,
        language=args.language,
    )

    # Load or initialize test state
    test_state = get_test_state(config)
    is_resumed = test_state.load() and test_state.is_resumed_test()

    # Authenticate as root (only for new tests, not resumed)
    if not is_resumed:
        print("=" * 60)
        print("HW-Test - Тестирование оборудования")
        print("=" * 60)
        print()

        if not authenticate_root():
            print("\n✗ Не удалось аутентифицироваться как root.")
            print("  Тестирование требует привилегий root для выполнения команд.")
            return 1

        # Show test selection menu (only in interactive mode)
        if not args.batch and not args.steps:
            selected_steps = show_test_menu(config)
            config.steps_to_run = selected_steps

    # Run tests
    return run_tests(config, logger, test_state)


if __name__ == "__main__":
    sys.exit(main())
