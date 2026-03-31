"""GUI test selection dialog for hw-test.

Provides a yad-based GUI for selecting test parameters after system information is gathered.
"""

from __future__ import annotations

import subprocess
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from hw_test.l10n import get_l10n, _
from hw_test.types import HardwareInfo


class TestSelectorGUI:
    """GUI dialog for test selection using yad."""

    def __init__(self, hardware_info: Optional[HardwareInfo] = None):
        self.l10n = get_l10n()
        self.hardware_info = hardware_info
        self.system_info = {}

    def _run_command(self, cmd: List[str], timeout: int = 30) -> Tuple[str, int]:
        """Run command and return (stdout, returncode)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip(), result.returncode
        except Exception:
            return "", -1

    def _run_command_as_root(self, cmd: List[str], timeout: int = 30) -> Tuple[str, int]:
        """Run command as root using su -."""
        from hw_test.auth import run_as_root

        stdout, stderr, rc = run_as_root(cmd, timeout=timeout)
        return stdout.strip() if stdout else "", rc

    def gather_system_info(self) -> Dict[str, Any]:
        """Gather system information for display."""
        info = {
            "cpu": "Unknown",
            "memory": "Unknown",
            "disk": "Unknown",
            "gpu": "Unknown",
            "hostname": "Unknown",
            "kernel": "Unknown",
            "uptime": "Unknown",
        }

        # CPU
        stdout, rc = self._run_command_as_root(["lscpu"])
        if rc == 0:
            for line in stdout.split("\n"):
                if "Model name" in line or "CPU model" in line:
                    info["cpu"] = line.split(":", 1)[1].strip()
                    break

        # Memory
        stdout, rc = self._run_command_as_root(["free", "-h"])
        if rc == 0:
            for line in stdout.split("\n"):
                if line.startswith("Mem:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        info["memory"] = parts[1]
                    break

        # Disk
        stdout, rc = self._run_command_as_root(["df", "-h", "/"])
        if rc == 0:
            lines = stdout.split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 2:
                    info["disk"] = parts[1]

        # GPU
        stdout, rc = self._run_command_as_root(["lspci", "-nn"])
        if rc == 0:
            for line in stdout.split("\n"):
                if "VGA" in line or "3D" in line or "Display" in line:
                    info["gpu"] = line.split(":", 2)[-1].strip()
                    break

        # Hostname
        stdout, rc = self._run_command(["hostname"])
        if rc == 0:
            info["hostname"] = stdout

        # Kernel
        stdout, rc = self._run_command(["uname", "-r"])
        if rc == 0:
            info["kernel"] = stdout

        # Uptime
        stdout, rc = self._run_command(["uptime", "-p"])
        if rc == 0:
            info["uptime"] = stdout.replace("up ", "")

        self.system_info = info
        return info

    def _check_capability(self, name: str) -> bool:
        """Check if a capability is available."""
        checks = {
            "fwupd": ["which", "fwupdmgr"],
            "glmark2": ["which", "glmark2"],
        }

        if name not in checks:
            return False

        cmd = checks[name]
        _, rc = self._run_command_as_root(cmd)
        return rc == 0

    def show(self, selected_tests: Optional[List[str]] = None) -> Optional[List[str]]:
        """
        Show test selection GUI dialog.

        Args:
            selected_tests: Previously selected tests (for edit mode)

        Returns:
            List of selected test IDs or None if cancelled
        """
        # Gather system info
        self.gather_system_info()

        # Check capabilities
        caps = {
            "fwupd": self._check_capability("fwupd"),
            "glmark2": self._check_capability("glmark2"),
        }

        # Build system info text
        system_text = (
            f"<b>Хост:</b> {self.system_info.get('hostname', 'Unknown')}\n"
            f"<b>CPU:</b> {self.system_info.get('cpu', 'Unknown')[:60]}...\n"
            f"<b>Память:</b> {self.system_info.get('memory', 'Unknown')}\n"
            f"<b>Диск:</b> {self.system_info.get('disk', 'Unknown')}\n"
            f"<b>GPU:</b> {self.system_info.get('gpu', 'Unknown')[:50]}...\n"
            f"<b>Ядро:</b> {self.system_info.get('kernel', 'Unknown')}\n"
            f"<b>Время работы:</b> {self.system_info.get('uptime', 'Unknown')}"
        )

        # Build test items with descriptions
        # Note: test IDs must match step names in hw_test/steps/__init__.py
        test_items = [
            # Basic tests
            (
                "hardware_detection",
                "Определение оборудования",
                "Сбор информации о всех компонентах системы",
                True,
            ),
            ("system_check", "Проверка системы", "Проверка целостности и состояния системы", True),
            ("log_collection", "Сбор логов", "Сохранение системных журналов", True),
            (
                "firmware_check",
                "Проверка прошивок",
                "Проверка обновлений микрокода и прошивок",
                caps.get("fwupd", False),
            ),
            # Performance tests
            (
                "performance",
                "Бенчмарки CPU/памяти",
                "Тестирование производительности процессора и памяти",
                True,
            ),
            ("diskperf", "Тест диска", "Измерение скорости чтения/записи диска", True),
            (
                "glmark",
                "Тест графики (glmark2)",
                "Бенчмарк графической подсистемы",
                caps.get("glmark2", False),
            ),
            (
                "cpupower",
                "Управление питанием CPU",
                "Проверка режимов энергосбережения процессора",
                True,
            ),
            # Express tests
            ("express_test", "Экспресс-тест", "Быстрая проверка основных функций", True),
            # Special tests
            ("syslogs", "Анализ логов", "Проверка системных журналов на ошибки", True),
            # System update
            ("upgrade", "Обновление системы", "Обновление пакетов системы", True),
            ("prepare", "Подготовка системы", "Подготовка к тестированию", True),
        ]

        # Filter available tests
        available_tests = [(tid, tname, tdesc) for tid, tname, tdesc, avail in test_items if avail]

        # Show system info first
        self._show_system_info(system_text)

        # Show test selection
        selected = self._show_test_selection(available_tests, selected_tests)

        if selected:
            return selected

        # If cancelled, return default
        from hw_test.steps import DEFAULT_STEP_ORDER

        return DEFAULT_STEP_ORDER.copy()

    def _show_system_info(self, system_text: str) -> None:
        """Show system information dialog."""
        try:
            subprocess.run(
                [
                    "yad",
                    "--info",
                    "--title",
                    "Информация о системе",
                    "--text",
                    system_text,
                    "--image",
                    "computer",
                    "--button",
                    "Продолжить:0",
                    "--width=500",
                    "--height=400",
                ],
                timeout=60,
            )
        except Exception as e:
            print(f"Failed to show system info: {e}")

    def _show_test_selection(
        self, available_tests: List[Tuple[str, str, str]], selected_tests: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Show test selection dialog."""
        # Build checklist items
        checklist_items = []
        for test_id, test_name, test_desc in available_tests:
            # Check if this test was previously selected
            is_selected = selected_tests is None or test_id in selected_tests
            checklist_items.extend([test_id, test_name, test_desc, str(is_selected).lower()])

        try:
            result = subprocess.run(
                [
                    "yad",
                    "--checklist",
                    "--title",
                    "Выбор параметров тестирования",
                    "--text",
                    "Выберите тесты для выполнения:",
                    "--column",
                    "ID",
                    "--column",
                    "Название",
                    "--column",
                    "Описание",
                    "--column",
                    "Выбор",
                    "--checklist-column",
                    "3",
                    "--multiple",
                    "--separator",
                    ",",
                    "--width=700",
                    "--height=500",
                    "--button",
                    "gtk-cancel:1",
                    "--button",
                    "gtk-ok:0",
                ]
                + checklist_items,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse output - yad returns comma-separated IDs
                selected_ids = [
                    tid.strip().strip('"')
                    for tid in result.stdout.strip().split(",")
                    if tid.strip()
                ]
                return selected_ids if selected_ids else None

            return None

        except FileNotFoundError as e:
            print(f"Test selection dialog failed: yad not found - {e}")
            return None
        except Exception as e:
            print(f"Test selection dialog failed: {e}")
            return None


def show_test_selector(
    hardware_info: Optional[HardwareInfo] = None,
    selected_tests: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """
    Show test selection GUI dialog.

    Args:
        hardware_info: Detected hardware information
        selected_tests: Previously selected tests

    Returns:
        List of selected test IDs or None if cancelled
    """
    selector = TestSelectorGUI(hardware_info)
    return selector.show(selected_tests)
