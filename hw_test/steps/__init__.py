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

# Default step execution order (matches pc-test bash order)
DEFAULT_STEP_ORDER = [
    "prepare",
    "upgrade",
    "hardware_detection",
    "config",
    "firmware_check",
    "syslogs",
    "express_test",
    "cpupower",
    "diskperf",
    "glmark",
    "system_check",
    "performance",
    "reboot_and_continue",
    "log_collection",
    "finalize",
]


def get_step_class(step_name: str):
    """Get a step class by name."""
    return AVAILABLE_STEPS.get(step_name)


def get_available_steps() -> List[str]:
    """Get list of available step names."""
    return list(AVAILABLE_STEPS.keys())
