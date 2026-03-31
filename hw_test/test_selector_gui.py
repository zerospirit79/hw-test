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
            "numa": [
                "bash",
                "-c",
                "test $(lscpu --parse=NODE 2>/dev/null | grep -v '^#' | sort -u | wc -l) -gt 1",
            ],
            "webcam": ["bash", "-c", "ls /dev/video* >/dev/null 2>&1"],
            "fingerprint": [
                "bash",
                "-c",
                "lsusb 2>/dev/null | grep -qi 'fingerprint\\|goodix\\|validity'",
            ],
            "bluetooth": ["which", "bluetoothctl"],
            "ipmi": ["which", "ipmitool"],
            "smartcard": ["which", "pcsc_scan"],
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
            "numa": self._check_capability("numa"),
            "webcam": self._check_capability("webcam"),
            "fingerprint": self._check_capability("fingerprint"),
            "bluetooth": self._check_capability("bluetooth"),
            "ipmi": self._check_capability("ipmi"),
            "smartcard": self._check_capability("smartcard"),
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
            ("numa_test", "NUMA топология", "Проверка топологии NUMA", caps.get("numa", False)),
            ("webcam_test", "Веб-камеры", "Проверка веб-камер", caps.get("webcam", False)),
            (
                "fingerprint_test",
                "Сканеры отпечатков",
                "Проверка сканеров отпечатков пальцев",
                caps.get("fingerprint", False),
            ),
            (
                "bluetooth_test",
                "Bluetooth",
                "Проверка Bluetooth адаптера",
                caps.get("bluetooth", False),
            ),
            ("ipmi_test", "IPMI/BMC", "Проверка интерфейса IPMI", caps.get("ipmi", False)),
            ("smartcard_test", "Смарт-карты", "Проверка смарт-карт", caps.get("smartcard", False)),
            # System update
            ("upgrade", "Обновление системы", "Обновление пакетов системы", True),
            ("prepare", "Подготовка системы", "Подготовка к тестированию", True),
        ]

        # Build yad command
        yad_cmd = [
            "yad",
            "--title=Выбор параметров тестирования",
            "--width=700",
            "--height=650",
            "--button=gtk-ok:0",
            "--button=gtk-cancel:1",
            "--notebooks",
        ]

        # Page 1: System Info
        yad_cmd.extend(
            [
                "--tab=Информация о системе",
                f"--field={system_text}:LBL",
                "",
            ]
        )

        # Page 2: Test Selection
        page2_fields = []
        for test_id, test_name, test_desc, available in test_items:
            if available:
                # Use checkbox with tooltip
                page2_fields.extend(
                    [
                        f"--field={test_name}:CHK",
                        "TRUE",  # Default checked
                    ]
                )

        yad_cmd.extend(page2_fields)
        yad_cmd.extend(["--tab=Тесты"])

        # Page 3: Presets
        yad_cmd.extend(
            [
                "--tab=Пресеты",
                "--field=Полный тест (все доступные):RB",
                "TRUE",
                "--field=Базовый тест (минимальный):RB",
                "FALSE",
                "--field=Экспресс тест (быстрый):RB",
                "FALSE",
                "--field=Производительность (бенчмарки):RB",
                "FALSE",
            ]
        )

        # Run yad
        try:
            result = subprocess.run(
                yad_cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return None

            output = result.stdout.strip().split("|")

            # Parse output
            # First field from each tab
            # Tab 1 (System Info): just display, no input
            # Tab 2 (Tests): checkboxes
            # Tab 3 (Presets): radio button selection

            # Check if preset selected (last field)
            preset_field = output[-1] if output else ""

            if "Полный" in preset_field:
                # Return all available tests
                return [t[0] for t in test_items if t[3]]
            elif "Базовый" in preset_field:
                return ["hardware_detection", "system_check", "log_collection"]
            elif "Экспресс" in preset_field:
                return ["express_test", "hardware_detection", "log_collection"]
            elif "Производительность" in preset_field:
                return ["performance", "diskperf", "glmark", "cpupower"]

            # Otherwise, parse checkboxes
            # Skip first field (system info display) and last field (preset)
            selected = []
            test_idx = 0
            for test_id, test_name, test_desc, available in test_items:
                if available:
                    # Checkbox value is at position 1 + test_idx (skip system info field)
                    checkbox_idx = 1 + test_idx
                    if checkbox_idx < len(output):
                        val = output[checkbox_idx].strip().lower()
                        if val in ["true", "1", "t"]:
                            selected.append(test_id)
                    test_idx += 1

            return selected if selected else None

        except Exception as e:
            print(f"Error running test selector: {e}")
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
