"""Step 7: System Reboot."""

from __future__ import annotations

import subprocess
import os
from typing import List, Dict, Any, Optional, Tuple

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class RebootStep(BaseHWStep):
    """
    Reboot the system and continue testing after reboot.

    This step marks the test state as requiring reboot.
    After reboot, the test will automatically continue from where it left off.
    """

    name = "System Reboot"
    description = "Reboot the system and continue testing after reboot"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.reboot_reason = "Плановая перезагрузка в процессе тестирования"

    def set_reboot_reason(self, reason: str) -> None:
        """Set the reason for reboot."""
        self.reboot_reason = reason

    def _run_command(
        self, cmd: List[str], timeout: int = 60, use_root: bool = True
    ) -> Tuple[str, str, int]:
        """Run a command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def execute(self) -> StepResult:
        """
        Execute system reboot.

        This step does NOT actually reboot the system. Instead, it sets a flag
        in the test state indicating that a reboot is required. The CLI will
        handle the actual reboot after saving the state.
        """
        errors = []
        warnings = []

        self.logger.info("Подготовка к перезагрузке системы...")

        try:
            # Check if reboot is actually needed
            # This can be overridden by setting a condition in the step
            if not self.config.batch_mode:
                # In interactive mode, we could prompt the user
                # But for now, we just set the flag
                pass

            # The actual reboot will be triggered by the CLI
            # after this step completes and state is saved

            return StepResult(
                step_name=self.name,
                status=TestStatus.PASSED,
                message="Перезагрузка будет выполнена после сохранения состояния",
                details={"reboot_reason": self.reboot_reason, "action": "state_flag_set"},
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.exception(f"Ошибка при подготовке перезагрузки: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Ошибка при подготовке перезагрузки: {str(e)}",
                errors=[str(e)],
            )


class RebootAndContinueStep(RebootStep):
    """
    Reboot the system and continue testing.

    This step actually triggers the reboot after saving state.
    """

    name = "Reboot and Continue"
    description = "Reboot the system and automatically continue testing"

    def execute(self) -> StepResult:
        """Execute reboot and mark for continuation."""
        errors = []
        warnings = []

        self.logger.info("Выполнение перезагрузки системы...")

        try:
            # First, sync disks
            self._run_command(["sync"], use_root=True)

            # Schedule reboot
            # We use 'shutdown -r now' for immediate reboot
            stdout, stderr, rc = self._run_command(
                ["shutdown", "-r", "now", "HW-Test: плановая перезагрузка"],
                timeout=30,
                use_root=True,
            )

            # If shutdown command succeeded, the system is rebooting
            # The test will continue after reboot via systemd service or manual restart

            if rc == 0:
                # Give some time for shutdown to start
                import time

                time.sleep(2)

                return StepResult(
                    step_name=self.name,
                    status=TestStatus.PASSED,
                    message="Система перезагружается. Тест продолжится автоматически.",
                    details={
                        "reboot_reason": self.reboot_reason,
                        "action": "reboot_triggered",
                        "shutdown_output": stdout[:200] if stdout else "",
                    },
                    errors=errors,
                    warnings=warnings,
                )
            else:
                # Shutdown failed, but we still want to mark for reboot
                warnings.append(f"Команда shutdown вернула код {rc}: {stderr}")

                return StepResult(
                    step_name=self.name,
                    status=TestStatus.WARNING,
                    message="Не удалось выполнить перезагрузку, но флаг установлен",
                    details={
                        "reboot_reason": self.reboot_reason,
                        "action": "state_flag_set",
                        "error": stderr,
                    },
                    errors=errors,
                    warnings=warnings,
                )

        except Exception as e:
            self.logger.exception(f"Перезагрузка не удалась: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Перезагрузка не удалась: {str(e)}",
                errors=[str(e)],
            )
