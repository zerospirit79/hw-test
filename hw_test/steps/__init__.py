"""Steps package for HW-Test."""

from __future__ import annotations

from typing import List

from hw_test.steps.base import BaseHWStep
from hw_test.steps.step_01_hardware_detection import HardwareDetectionStep
from hw_test.steps.step_02_express_test import ExpressTestStep
from hw_test.steps.step_03_system_check import SystemCheckStep
from hw_test.steps.step_04_performance import PerformanceStep
from hw_test.steps.step_05_firmware_check import FirmwareCheckStep
from hw_test.steps.step_06_log_collection import LogCollectionStep
from hw_test.steps.step_07_reboot import RebootStep, RebootAndContinueStep
from hw_test.steps.step_08_prepare import PrepareStep
from hw_test.steps.step_09_upgrade import UpgradeStep
from hw_test.steps.step_10_config import ConfigStep
from hw_test.steps.step_11_syslogs import SyslogsStep
from hw_test.steps.step_12_cpupower import CpuPowerStep
from hw_test.steps.step_13_diskperf import DiskPerfStep
from hw_test.steps.step_14_glmark import GlmarkStep
from hw_test.steps.step_15_finalize import FinalizeStep

__all__ = [
    "BaseHWStep",
    "HardwareDetectionStep",
    "ExpressTestStep",
    "SystemCheckStep",
    "PerformanceStep",
    "FirmwareCheckStep",
    "LogCollectionStep",
    "RebootStep",
    "RebootAndContinueStep",
    "PrepareStep",
    "UpgradeStep",
    "ConfigStep",
    "SyslogsStep",
    "CpuPowerStep",
    "DiskPerfStep",
    "GlmarkStep",
    "FinalizeStep",
]

# Registry of all available steps
AVAILABLE_STEPS = {
    "hardware_detection": HardwareDetectionStep,
    "express_test": ExpressTestStep,
    "system_check": SystemCheckStep,
    "performance": PerformanceStep,
    "firmware_check": FirmwareCheckStep,
    "log_collection": LogCollectionStep,
    "reboot": RebootStep,
    "reboot_and_continue": RebootAndContinueStep,
    "prepare": PrepareStep,
    "upgrade": UpgradeStep,
    "config": ConfigStep,
    "syslogs": SyslogsStep,
    "cpupower": CpuPowerStep,
    "diskperf": DiskPerfStep,
    "glmark": GlmarkStep,
    "finalize": FinalizeStep,
}

# Default step execution order (matches pc-test methodology order)
# Order:
# 1. Prepare - detect distro/architecture (p10, p11, c10f2, etc.)
# 2. Upgrade - add repository, apt-get update, apt-get dist-upgrade, update-kernel
# 3. Reboot and continue
# 4. System logs check (section 7)
# 5. Hardware detection (section 8.2, 8.3)
# 6. Component tests (section 10)
# 7. Log collection
# 8. Finalize
DEFAULT_STEP_ORDER = [
    "prepare",  # Detect distro, architecture
    "upgrade",  # Add repo, apt-get update, dist-upgrade, update-kernel
    "reboot_and_continue",  # Reboot after upgrade
    "syslogs",  # Section 7: Check and save logs
    "hardware_detection",  # Section 8.2, 8.3: Hardware info and spec verification
    "config",  # Test configuration
    "firmware_check",  # Firmware updates
    "express_test",  # Section 10: Express tests
    "cpupower",  # Section 10.1, 10.6: CPU power and ACPI
    "diskperf",  # Section 10: Disk performance
    "glmark",  # Section 10.3: Graphics
    "performance",  # Section 10: Benchmarks
    "system_check",  # Section 10: System checks
    "log_collection",  # Collect all logs
    "finalize",  # Create archive
]


def get_step_class(step_name: str):
    """Get a step class by name."""
    return AVAILABLE_STEPS.get(step_name)


def get_available_steps() -> List[str]:
    """Get list of available step names."""
    return list(AVAILABLE_STEPS.keys())
