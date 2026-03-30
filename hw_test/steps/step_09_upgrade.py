"""Step 2: System Upgrade."""

import time
from typing import List, Dict, Any, Optional

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class UpgradeStep(BaseHWStep):
    """
    System and kernel update.
    
    Performs:
    - APT lists update
    - System dist-upgrade
    - Kernel update
    - Package installation verification
    """

    name = "System Upgrade"
    description = "Update system packages and kernel"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.upgrade_info: Dict[str, Any] = {}

    def _run_command(self, cmd: List[str], timeout: int = 300, use_root: bool = True) -> tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _update_apt_lists(self) -> bool:
        """Update APT package lists."""
        self.logger.info("Updating APT package lists...")
        stdout, stderr, rc = self._run_command(['apt-get', 'update'], timeout=300)
        if rc != 0:
            self.logger.warning(f"apt-get update failed: {stderr}")
            return False
        return True

    def _dist_upgrade(self) -> tuple[bool, str]:
        """Perform distribution upgrade."""
        self.logger.info("Performing dist-upgrade...")
        stdout, stderr, rc = self._run_command(
            ['apt-get', 'dist-upgrade', '-y'],
            timeout=600
        )
        if rc != 0:
            return False, stderr
        return True, ""

    def _update_kernel(self) -> tuple[bool, str]:
        """Update kernel using update-kernel."""
        self.logger.info("Updating kernel...")
        stdout, stderr, rc = self._run_command(
            ['update-kernel', '-f'],
            timeout=300
        )
        if rc != 0:
            return False, stderr
        return True, ""

    def _check_package(self, package_name: str) -> bool:
        """Check if package is installed."""
        stdout, _, rc = self._run_command(['rpm', '-q', package_name])
        return rc == 0

    def _check_package_available(self, package_name: str) -> bool:
        """Check if package is available in repositories."""
        stdout, _, rc = self._run_command(['apt-cache', 'show', package_name])
        return rc == 0

    def _install_packages(self, packages: List[str]) -> tuple[bool, str]:
        """Install required packages."""
        if not packages:
            return True, ""

        self.logger.info(f"Installing packages: {', '.join(packages)}")
        stdout, stderr, rc = self._run_command(
            ['apt-get', 'install', '-y'] + packages,
            timeout=600
        )
        if rc != 0:
            return False, stderr
        return True, ""

    def _mark_package_manual(self, package_name: str) -> None:
        """Mark package as manually installed."""
        self._run_command(['apt-mark', 'manual', package_name], timeout=30)

    def _fix_integrity(self) -> None:
        """Fix integrity alerts (ALT SP specific)."""
        self._run_command(['integalert', 'fix'], timeout=60)

    def execute(self) -> StepResult:
        """Execute system upgrade."""
        errors = []
        warnings = []

        self.logger.info("Starting system upgrade...")

        try:
            upgrade_log = []
            packages_to_install = []

            # Update APT lists
            if not self._update_apt_lists():
                warnings.append("Failed to update APT lists")

            # Try dist-upgrade with retries
            upgrade_success = False
            for attempt in range(1, 4):
                self.logger.info(f"Upgrade attempt {attempt}/3")

                dist_success, dist_err = self._dist_upgrade()
                kernel_success, kernel_err = self._update_kernel()

                if dist_success and kernel_success:
                    upgrade_success = True
                    upgrade_log.append("Upgrade completed successfully")
                    break
                else:
                    upgrade_log.append(f"Attempt {attempt} failed: {dist_err or kernel_err}")
                    if attempt < 3:
                        time.sleep(2)

            if not upgrade_success:
                warnings.append("System upgrade completed with errors")

            # ALT SP specific: mark update-kernel as manual
            if self._check_package('update-kernel'):
                self._mark_package_manual('update-kernel')

            # ALT SP specific: fix integrity
            if self._check_package('integalert'):
                self._fix_integrity()

            # Check required packages
            required_packages = ['inxi']

            # Check for GUI tools
            if os.environ.get('DISPLAY'):
                if self._check_package_available('yad') and not self._check_package('yad'):
                    packages_to_install.append('yad')
            else:
                if self._check_package_available('dialog') and not self._check_package('dialog'):
                    packages_to_install.append('dialog')

            # Install missing packages
            if packages_to_install:
                success, err = self._install_packages(packages_to_install)
                if not success:
                    warnings.append(f"Failed to install some packages: {err}")

            # Build summary
            summary = {
                'upgrade_success': upgrade_success,
                'upgrade_log': upgrade_log,
                'packages_installed': packages_to_install,
                'reboot_required': upgrade_success,
            }

            self.upgrade_info = summary

            # Determine status
            if errors:
                status = TestStatus.FAILED
                message = "System upgrade failed"
            elif warnings:
                status = TestStatus.WARNING
                message = "System upgrade completed with warnings"
            else:
                status = TestStatus.PASSED
                message = "System upgrade completed successfully. Reboot required."

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.exception(f"System upgrade failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"System upgrade failed: {str(e)}",
                errors=[str(e)]
            )


# Need to import os for DISPLAY check
import os
