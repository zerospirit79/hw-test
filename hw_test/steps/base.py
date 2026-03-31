"""Base class for hardware test steps."""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.auth import run_as_root, is_root_authenticated
from hw_test.system_utils import (
    CommandLogger,
    is_pkg_installed,
    has_binary,
)


logger = logging.getLogger(__name__)


class BaseHWStep(ABC):
    """
    Abstract base class for all hardware test steps.

    Each test step should inherit from this class and implement:
    - name: Human-readable name of the step
    - description: Detailed description of what the step does
    - execute(): Main test logic
    """

    name: str = "Base Step"
    description: str = "Base test step"
    requires_root: bool = False
    required_privileges: bool = False  # Alias for requires_root (for CLI compatibility)
    timeout_seconds: int = 300

    # Pre-check: conditions for test to be allowed/blocked
    # Override in subclasses to add custom pre-checks
    required_packages: List[str] = []
    required_binaries: List[str] = []
    required_desktop: Optional[str] = None
    requires_xorg: bool = False
    requires_systemd: bool = False

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        """
        Initialize the test step.

        Args:
            config: Test configuration
            hardware_info: Detected hardware information (may be None for early steps)
        """
        self.config = config
        self.hardware_info = hardware_info
        self.logger = logging.getLogger(f"hw_test.steps.{self.__class__.__name__}")

    def setup(self) -> bool:
        """
        Setup hook called before execute().

        Returns:
            True if setup succeeded, False otherwise
        """
        self.logger.debug(f"Setting up step: {self.name}")
        return True

    def teardown(self) -> None:
        """Cleanup hook called after execute(), even if it failed."""
        self.logger.debug(f"Tearing down step: {self.name}")

    def pre(self) -> Tuple[bool, Optional[str]]:
        """
        Pre-check hook called before setup().
        Override in subclasses to add custom pre-checks.

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
            - If allowed is False, test will be blocked/skipped with reason
        """
        # Check required packages
        for pkg in self.required_packages:
            if not is_pkg_installed(pkg):
                return False, f"Required package '{pkg}' is not installed"

        # Check required binaries
        for binary in self.required_binaries:
            if not has_binary(binary):
                return False, f"Required binary '{binary}' not found"

        # Check desktop environment
        if self.required_desktop:
            from hw_test.system_utils import get_current_desktop

            current = get_current_desktop()
            if current != self.required_desktop:
                return (
                    False,
                    f"Requires {self.required_desktop} desktop (current: {current or 'none'})",
                )

        # Check Xorg
        if self.requires_xorg:
            if not is_pkg_installed("xorg-server") and not has_binary("Xorg"):
                return False, "Xorg server is required but not found"

        # Check systemd
        if self.requires_systemd:
            if not os.path.exists("/run/systemd/system"):
                return False, "systemd is required but not running"

        return True, None

    def is_allowed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if test is allowed to run (not blocked).
        Combines pre() check with root authentication.

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        allowed, reason = self.pre()
        if not allowed:
            return False, reason

        if self.requires_root and not is_root_authenticated():
            return False, "Root authentication required"

        return True, None

    def is_blocked(self) -> Tuple[bool, Optional[str]]:
        """
        Check if test is blocked (can be retried later).
        Override in subclasses for custom block conditions.

        Returns:
            Tuple of (blocked: bool, reason: Optional[str])
        """
        # Default: not blocked
        return False, None

    @abstractmethod
    def execute(self) -> StepResult:
        """
        Execute the test step.

        Returns:
            StepResult with status, message, and any errors/warnings
        """
        pass

    def run_command(
        self, cmd: List[str], timeout: int = 30, use_root: bool = False
    ) -> Tuple[str, str, int]:
        """
        Run a command, optionally as root.

        Args:
            cmd: Command and arguments as list
            timeout: Command timeout in seconds
            use_root: If True, run command as root using su -c

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        if use_root and self.requires_root:
            if not is_root_authenticated():
                self.logger.warning("Root not authenticated, command may fail")
            return run_as_root(cmd, timeout)
        else:
            import subprocess

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                return result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Command timed out: {' '.join(cmd)}")
                return "", "Timeout", -1
            except Exception as e:
                self.logger.debug(f"Command failed: {' '.join(cmd)} - {e}")
                return "", str(e), -1

    def run(self) -> StepResult:
        """
        Run the complete step lifecycle: pre -> setup -> execute -> teardown.

        Returns:
            StepResult from execute() or error/blocked/skipped result
        """
        start_time = time.time()

        # Pre-check phase
        allowed, reason = self.is_allowed()
        if not allowed:
            # Check if blocked (can retry) or should skip
            blocked, block_reason = self.is_blocked()
            if blocked:
                self.logger.info(f"Step {self.name} is blocked: {block_reason or reason}")
                return StepResult(
                    step_name=self.name,
                    status=TestStatus.WARNING,  # Blocked, not failed
                    message=f"Test blocked: {reason}",
                    details={"blocked": True, "reason": reason},
                )
            else:
                self.logger.info(f"Step {self.name} skipped: {reason}")
                return StepResult(
                    step_name=self.name,
                    status=TestStatus.SKIPPED,
                    message=f"Test skipped: {reason}",
                    details={"skipped": True, "reason": reason},
                )

        # Setup phase
        if not self.setup():
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message="Setup failed",
                errors=["Step setup failed"],
            )

        try:
            # Execute phase
            self.logger.info(f"Starting step: {self.name}")
            result = self.execute()
            result.duration_seconds = time.time() - start_time

            if result.errors:
                self.logger.error(f"Step {self.name} completed with errors: {result.errors}")
            if result.warnings:
                self.logger.warning(f"Step {self.name} completed with warnings: {result.warnings}")

            self.logger.info(
                f"Step {self.name} completed: {result.status.value} "
                f"in {result.duration_seconds:.2f}s"
            )

            return result

        except Exception as e:
            self.logger.exception(f"Step {self.name} raised exception: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Exception during execution: {str(e)}",
                errors=[str(e)],
                duration_seconds=time.time() - start_time,
            )

        finally:
            # Teardown phase (always runs)
            try:
                self.teardown()
            except Exception as e:
                self.logger.warning(f"Teardown for {self.name} failed: {e}")

    def get_result_dict(self, result: StepResult) -> Dict[str, Any]:
        """Convert StepResult to dictionary for JSON serialization."""
        return {
            "step_name": result.step_name,
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
            "warnings": result.warnings,
        }
