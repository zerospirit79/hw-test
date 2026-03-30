"""Step 4: Package Installation."""

import os
from typing import List, Dict, Any, Optional

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class InstallStep(BaseHWStep):
    """
    Installing additional software.
    
    Installs packages required for hardware testing:
    - Essential utilities (hdparm, smartmontools, etc.)
    - Network tools (iputils, iperf3)
    - Firmware update tools (fwupd)
    - Audio/video tools (alsa-utils, pulseaudio)
    - Development tools (optional)
    """

    name = "Package Installation"
    description = "Install additional packages required for testing"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.installed_packages: List[str] = []
        self.failed_packages: List[str] = []

    def _run_command(self, cmd: List[str], timeout: int = 300, use_root: bool = True) -> tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _is_pkg_installed(self, package_name: str) -> bool:
        """Check if package is installed."""
        stdout, _, rc = self._run_command(['rpm', '-q', package_name])
        return rc == 0

    def _is_pkg_available(self, package_name: str) -> bool:
        """Check if package is available in repositories."""
        stdout, _, rc = self._run_command(['apt-cache', 'show', package_name])
        return rc == 0

    def _install_packages(self, packages: List[str]) -> tuple[bool, str]:
        """Install packages."""
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

    def _get_required_packages(self, system_info: Dict[str, Any]) -> List[str]:
        """Get list of required packages based on system configuration."""
        packages = []

        # Essential packages (always required)
        essential = [
            'hdparm', 'system-report', 'rfkill', 'acpica', 'dmidecode',
            'lsblk', 'smartmontools', 'stress-ng', 'cpupower'
        ]

        for pkg in essential:
            if not self._is_pkg_installed(pkg) and self._is_pkg_available(pkg):
                packages.append(pkg)

        # Development tools (optional)
        if system_info.get('devel_test', False):
            devel = ['sos', 'eject']
            for pkg in devel:
                if not self._is_pkg_installed(pkg) and self._is_pkg_available(pkg):
                    packages.append(pkg)

        # Network tools (if network interfaces present)
        if system_info.get('ifaces', []):
            network = ['iputils', 'iperf3']
            for pkg in network:
                if not self._is_pkg_installed(pkg) and self._is_pkg_available(pkg):
                    packages.append(pkg)

        # Firmware update (fwupd - optional, UEFI only)
        if system_info.get('fwupd_test', False):
            if not self._is_pkg_installed('fwupd') and self._is_pkg_available('fwupd'):
                packages.append('fwupd')

        # SCSI/SATA utilities
        if not self._is_pkg_installed('lsscsi') and self._is_pkg_available('lsscsi'):
            packages.append('lsscsi')

        # Infiniband/RDMA tools
        if system_info.get('infb_test', False):
            if not self._is_pkg_installed('libibverbs-utils') and self._is_pkg_available('libibverbs-utils'):
                packages.append('libibverbs-utils')

        # Audio tools (if sound cards present)
        if system_info.get('sound_test', False) or system_info.get('webcam_test', False):
            audio = ['alsa-utils', 'aplay', 'pulseaudio-daemon', 'pulseaudio-utils']
            for pkg in audio:
                if not self._is_pkg_installed(pkg) and self._is_pkg_available(pkg):
                    packages.append(pkg)

        # Power management (if battery systems)
        if system_info.get('power_test', False):
            if not self._is_pkg_installed('upower') and self._is_pkg_available('upower'):
                packages.append('upower')

        # NUMA tools
        if system_info.get('numa_test', False):
            numa = ['htop', 'numactl', 'squashfs-tools']
            for pkg in numa:
                if not self._is_pkg_installed(pkg) and self._is_pkg_available(pkg):
                    packages.append(pkg)

        # IPMI tools (for servers)
        if system_info.get('ipmi_test', False):
            if not self._is_pkg_installed('ipmitool') and self._is_pkg_available('ipmitool'):
                packages.append('ipmitool')

        # FIO for disk testing
        if system_info.get('fio_test', False):
            if not self._is_pkg_installed('fio') and self._is_pkg_available('fio'):
                packages.append('fio')

        # Graphics benchmarks
        if system_info.get('v3d_test', False):
            if not self._is_pkg_installed('glmark2') and self._is_pkg_available('glmark2'):
                packages.append('glmark2')

        return packages

    def execute(self) -> StepResult:
        """Execute package installation."""
        errors = []
        warnings = []

        self.logger.info("Starting package installation...")

        try:
            # Collect system information for package selection
            system_info = {
                'devel_test': False,
                'ifaces': [],
                'fwupd_test': False,
                'infb_test': False,
                'sound_test': False,
                'webcam_test': False,
                'power_test': False,
                'numa_test': False,
                'ipmi_test': False,
                'fio_test': True,
                'v3d_test': False,
            }

            # Detect network interfaces
            stdout, _, rc = self._run_command(['ls', '/sys/class/net'])
            if rc == 0:
                ifaces = [i for i in stdout.split() if i != 'lo']
                system_info['ifaces'] = ifaces

            # Detect firmware update capability
            stdout, _, rc = self._run_command(['which', 'fwupdmgr'])
            if rc == 0:
                system_info['fwupd_test'] = True

            # Detect Infiniband
            stdout, _, rc = self._run_command(['lspci'])
            if rc == 0 and ('RDMA' in stdout or 'InfiniBand' in stdout):
                system_info['infb_test'] = True

            # Detect sound
            stdout, _, rc = self._run_command(['aplay', '-l'])
            if rc == 0 and 'card' in stdout:
                system_info['sound_test'] = True

            # Detect webcams
            stdout, _, rc = self._run_command(['ls', '/dev/video*'], use_root=False)
            if rc == 0 and '/dev/video' in stdout:
                system_info['webcam_test'] = True

            # Detect power management
            if os.path.exists('/sys/class/power_supply/BAT0'):
                system_info['power_test'] = True

            # Detect NUMA
            stdout, _, rc = self._run_command(['lscpu', '--parse=NODE'])
            if rc == 0:
                nodes = set()
                for line in stdout.split('\n'):
                    if line and not line.startswith('#'):
                        parts = line.split(',')
                        if len(parts) >= 1 and parts[0].isdigit():
                            nodes.add(parts[0])
                if len(nodes) > 1:
                    system_info['numa_test'] = True

            # Get required packages
            packages_to_install = self._get_required_packages(system_info)

            self.logger.info(f"Packages to install: {packages_to_install}")

            if packages_to_install:
                # Install packages
                success, err = self._install_packages(packages_to_install)
                if success:
                    self.installed_packages = packages_to_install
                else:
                    # Track failed packages
                    self.failed_packages = packages_to_install
                    warnings.append(f"Failed to install some packages: {err}")
            else:
                self.logger.info("All required packages are already installed")

            # Build summary
            summary = {
                'packages_installed': self.installed_packages,
                'packages_failed': self.failed_packages,
                'total_requested': len(packages_to_install),
                'total_installed': len(self.installed_packages),
                'total_failed': len(self.failed_packages),
            }

            # Determine status
            if errors:
                status = TestStatus.FAILED
                message = "Package installation failed"
            elif self.failed_packages:
                status = TestStatus.WARNING
                message = f"Package installation completed with {len(self.failed_packages)} failures"
            else:
                status = TestStatus.PASSED
                message = f"Installed {len(self.installed_packages)} packages successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.exception(f"Package installation failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Package installation failed: {str(e)}",
                errors=[str(e)]
            )
