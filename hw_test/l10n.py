"""Localization module for hw-test.

Provides Russian and English translations for all user-facing messages.
"""

from typing import Dict, Optional
import os


class Localization:
    """Handles localization (NLS) for messages."""

    MESSAGES: Dict[str, Dict[str, str]] = {
        "en": {
            # General
            "program_name": "HW-Test",
            "version": "Version",
            "starting_program": "Starting program",
            "resumption": "Resumption of testing",
            "first_part_complete": "The first part of testing is complete!",
            "testing_complete": "Testing is complete!",
            "creating_archive": "Creating the archive...",
            "archive_moved_to": "Now this archive has been moved to",
            "press_key_close": "Press any key to close this window...",
            # Authentication
            "root_required": "Root privileges required",
            "auth_title": "ROOT AUTHENTICATION",
            "auth_prompt": "Enter root password",
            "auth_attempt": "Attempt",
            "auth_success": "Authentication successful",
            "auth_failed": "Authentication failed",
            "auth_cancelled": "Authentication cancelled by user",
            "auth_max_attempts": "Maximum number of attempts exceeded",
            "password_empty": "Password cannot be empty",
            # Test status
            "test_passed": "PASSED",
            "test_failed": "FAILED",
            "test_warning": "WARNING",
            "test_skipped": "SKIPPED",
            "test_error": "ERROR",
            "test_running": "RUNNING",
            # Steps
            "step_prepare": "System Preparation",
            "step_upgrade": "System Upgrade",
            "step_hardware_detection": "Hardware Detection",
            "step_config": "Configuration",
            "step_firmware_check": "Firmware Check",
            "step_syslogs": "System Logs Check",
            "step_express_test": "Express Test",
            "step_cpupower": "CPU Power Test",
            "step_diskperf": "Disk Performance Test",
            "step_glmark": "Graphics Test",
            "step_system_check": "System Check",
            "step_performance": "Performance Benchmarks",
            "step_reboot": "System Reboot",
            "step_log_collection": "Log Collection",
            "step_finalize": "Finalization",
            # Messages
            "reboot_required": "Reboot required",
            "reboot_reason": "Reason for reboot",
            "test_will_continue": "Test will continue automatically after reboot",
            "state_saved": "Test state saved",
            "state_loaded": "Previous test session detected, resuming...",
            "tests_completed": "Tests completed",
            "tests_failed": "Some tests failed",
            "tests_with_warnings": "Tests completed with warnings",
            # Summary
            "summary_title": "TEST SUMMARY",
            "summary_total_steps": "Total steps executed",
            "summary_passed": "Passed",
            "summary_failed": "Failed",
            "summary_warnings": "Warnings",
            "summary_reboots": "Reboots",
            # Errors
            "error_step_failed": "Step failed",
            "error_unknown_step": "Unknown step",
            "error_auth_required": "Authentication required",
            "error_command_failed": "Command failed",
            "error_timeout": "Command timed out",
            # Warnings
            "warning_no_root": "Running without root privileges. Some tests may be skipped.",
            "warning_large_updates": "Large number of pending updates",
            "warning_disk_space": "Low disk space",
            # Reboot
            "rebooting": "Rebooting the system...",
            "reboot_manual": "Please reboot the system manually",
            "reboot_continue_cmd": "To continue testing run",
            # Archive
            "archive_created": "Archive created",
            "archive_path": "Archive path",
            "archive_size": "Archive size",
        },
        "ru": {
            # General
            "program_name": "HW-Test",
            "version": "Версия",
            "starting_program": "Запуск программы",
            "resumption": "Возобновление тестирования",
            "first_part_complete": "Первая часть тестирования завершена!",
            "testing_complete": "Тестирование завершено!",
            "creating_archive": "Создание архива",
            "archive_moved_to": "Теперь этот архив перемещён в",
            "press_key_close": "Нажмите любую клавишу для закрытия этого окна...",
            # Authentication
            "root_required": "Требуются права root",
            "auth_title": "АУТЕНТИФИКАЦИЯ ROOT",
            "auth_prompt": "Введите пароль root",
            "auth_attempt": "Попытка",
            "auth_success": "Аутентификация успешна",
            "auth_failed": "Неверный пароль",
            "auth_cancelled": "Аутентификация отменена пользователем",
            "auth_max_attempts": "Превышено максимальное количество попыток",
            "password_empty": "Пароль не может быть пустым",
            # Test status
            "test_passed": "ВЫПОЛНЕНО",
            "test_failed": "ОШИБКА",
            "test_warning": "ПРЕДУПРЕЖДЕНИЕ",
            "test_skipped": "ПРОПУЩЕНО",
            "test_error": "ОШИБКА",
            "test_running": "ВЫПОЛНЕНИЕ",
            # Steps
            "step_prepare": "Подготовка системы",
            "step_upgrade": "Обновление системы",
            "step_hardware_detection": "Определение оборудования",
            "step_config": "Конфигурация",
            "step_firmware_check": "Проверка прошивок",
            "step_syslogs": "Проверка журналов",
            "step_express_test": "Экспресс-тест",
            "step_cpupower": "Тест CPU",
            "step_diskperf": "Тест дисков",
            "step_glmark": "Тест графики",
            "step_system_check": "Проверка системы",
            "step_performance": "Тесты производительности",
            "step_reboot": "Перезагрузка",
            "step_log_collection": "Сбор логов",
            "step_finalize": "Завершение",
            # Messages
            "reboot_required": "Требуется перезагрузка",
            "reboot_reason": "Причина перезагрузки",
            "test_will_continue": "Тест продолжится автоматически после перезагрузки",
            "state_saved": "Состояние теста сохранено",
            "state_loaded": "Обнаружен предыдущий сеанс теста. Возобновление...",
            "tests_completed": "Тестирование завершено",
            "tests_failed": "Некоторые тесты завершились ошибкой",
            "tests_with_warnings": "Тестирование завершено с предупреждениями",
            # Summary
            "summary_title": "ИТОГИ ТЕСТИРОВАНИЯ",
            "summary_total_steps": "Всего шагов выполнено",
            "summary_passed": "Успешно",
            "summary_failed": "Ошибок",
            "summary_warnings": "Предупреждений",
            "summary_reboots": "Перезагрузок",
            # Errors
            "error_step_failed": "Шаг завершился ошибкой",
            "error_unknown_step": "Неизвестный шаг",
            "error_auth_required": "Требуется аутентификация",
            "error_command_failed": "Команда не выполнена",
            "error_timeout": "Превышено время ожидания команды",
            # Warnings
            "warning_no_root": "Запуск без прав root. Некоторые тесты могут быть пропущены.",
            "warning_large_updates": "Большое количество ожидающих обновлений",
            "warning_disk_space": "Недостаточно места на диске",
            # Reboot
            "rebooting": "Выполняется перезагрузка системы...",
            "reboot_manual": "Пожалуйста, перезагрузите систему вручную",
            "reboot_continue_cmd": "Для продолжения теста выполните",
            # Archive
            "archive_created": "Архив создан",
            "archive_path": "Путь к архиву",
            "archive_size": "Размер архива",
        },
    }

    def __init__(self, lang_id: Optional[str] = None):
        """
        Initialize localization.

        Args:
            lang_id: Language code ('en' or 'ru'). If None, auto-detect from locale.
        """
        if lang_id is None:
            lang_id = self._detect_locale()

        self.lang_id = lang_id if lang_id in self.MESSAGES else "ru"

    def _detect_locale(self) -> str:
        """Detect language from environment."""
        lang = (
            os.environ.get("LC_ALL")
            or os.environ.get("LC_MESSAGES")
            or os.environ.get("LANG")
            or "ru_RU.UTF-8"
        )

        # Extract language code
        lang_code = lang.split(".")[0].split("_")[0].lower()
        return lang_code if lang_code in ["en", "ru"] else "ru"

    def get(self, key: str, default: str = "") -> str:
        """
        Get localized message.

        Args:
            key: Message key
            default: Default value if key not found

        Returns:
            Localized message string
        """
        return self.MESSAGES.get(self.lang_id, {}).get(key, default)

    def _(self, key: str) -> str:
        """Shorthand for get()."""
        return self.get(key)

    def format(self, key: str, *args, **kwargs) -> str:
        """
        Get localized message with formatting.

        Args:
            key: Message key
            *args: Positional arguments for format
            **kwargs: Keyword arguments for format

        Returns:
            Formatted localized message
        """
        template = self.get(key)
        try:
            return template.format(*args, **kwargs)
        except (KeyError, IndexError, ValueError):
            return template

    def set_language(self, lang_id: str) -> None:
        """
        Set language.

        Args:
            lang_id: Language code ('en' or 'ru')
        """
        if lang_id in self.MESSAGES:
            self.lang_id = lang_id

    @property
    def is_russian(self) -> bool:
        """Check if current language is Russian."""
        return self.lang_id == "ru"

    @property
    def is_english(self) -> bool:
        """Check if current language is English."""
        return self.lang_id == "en"


# Global localization instance
_l10n: Optional[Localization] = None


def get_l10n() -> Localization:
    """Get or create global localization instance."""
    global _l10n
    if _l10n is None:
        _l10n = Localization()
    return _l10n


def _(key: str) -> str:
    """Shorthand for get_l10n().get()."""
    return get_l10n().get(key)


def set_language(lang_id: str) -> None:
    """Set global language."""
    get_l10n().set_language(lang_id)
