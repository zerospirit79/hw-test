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
)
from hw_test.state import get_test_state, TestState
from hw_test.l10n import get_l10n, _
from hw_test.dialogs import DialogManager


def write_file_as_root(filepath: str, content: str, mode: str = "644") -> bool:
    """
    Write content to file using root privileges via su -.

    Args:
        filepath: Full path to the file
        content: Content to write
        mode: File permissions (default: 644)

    Returns:
        True if successful, False otherwise
    """
    import base64

    # Encode content to base64 to avoid shell escaping issues
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    # Use base64 decode to write content safely
    cmd = f"echo {encoded} | base64 -d > {filepath} && chmod {mode} {filepath}"
    stdout, stderr, rc = run_as_root(["bash", "-c", cmd])
    return rc == 0


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


def show_test_menu(config: TestConfig, hardware_info=None) -> List[str]:
    """
    Show interactive test selection menu using GUI (yad).
    Displays system information and allows test selection.

    Args:
        config: Test configuration
        hardware_info: Detected hardware information

    Returns:
        List of selected test steps
    """
    from hw_test.test_selector_gui import show_test_selector

    # Use the new GUI selector
    selected = show_test_selector(
        hardware_info, config.steps_to_run if config.steps_to_run else None
    )

    if selected:
        return selected

    # If cancelled or GUI not available, return default
    from hw_test.steps import DEFAULT_STEP_ORDER

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
    hardware_info = None
    if not is_resumed:
        print("=" * 60)
        print("HW-Test - Тестирование оборудования")
        print("=" * 60)
        print()

        if not authenticate_root():
            print("\n✗ Не удалось аутентифицироваться как root.")
            print("  Тестирование требует привилегий root для выполнения команд.")
            return 1

        # For new interactive tests: run hardware detection first, then show GUI menu
        if not args.batch and not args.steps:
            # Step 1: Run hardware detection to gather system info
            print("\nℹ Сбор информации о системе...")
            logger.info("Running hardware detection...")

            try:
                from hw_test.steps import get_step_class
                from hw_test.types import HardwareInfo

                hw_step_class = get_step_class("hardware_detection")
                hw_step = hw_step_class(config, None)

                # Execute hardware detection
                hw_result = hw_step.execute()

                if hw_result.status != TestStatus.ERROR:
                    hardware_info = hw_step.detected_hardware
                    logger.info("Hardware detection completed")
                    print(f"✓ Обнаружено оборудование: {hardware_info.cpu_model}")
                else:
                    logger.warning("Hardware detection failed, continuing without hardware info")

            except Exception as e:
                logger.warning(f"Hardware detection error: {e}")
                hardware_info = None

            # Step 2: Show GUI test selection menu with system info
            print("\n📋 Выбор параметров тестирования...")
            selected_steps = show_test_menu(config, hardware_info)
            config.steps_to_run = selected_steps
            logger.info(f"Selected tests: {selected_steps}")

    # Make write_file_as_root available to steps via config
    config.write_file_callback = write_file_as_root

    # Run tests
    return run_tests(config, logger, test_state)


if __name__ == "__main__":
    sys.exit(main())
