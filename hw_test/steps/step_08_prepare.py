"""Step 1: System Preparation."""

import os
import re
import subprocess
from typing import List, Dict, Any, Optional

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class PrepareStep(BaseHWStep):
    """
    Preparing for a system update.
    
    Checks:
    - IMA/EVM status
    - AppArmor status
    - SELinux status
    - Kernel error messages
    - Hardware platform detection
    - ALT Linux distro detection
    - Desktop environment detection
    """

    name = "System Preparation"
    description = "Check system readiness for updates and testing"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.system_info: Dict[str, Any] = {}

    def _run_command(self, cmd: List[str], timeout: int = 60, use_root: bool = True) -> tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _check_ima_evm(self) -> Optional[str]:
        """Check IMA/EVM status."""
        try:
            with open('/sys/kernel/security/evm', 'r') as f:
                if f.read().strip() == '1':
                    return "IMA/EVM is enabled. Please disable it first."
        except (FileNotFoundError, IOError):
            pass
        return None

    def _check_apparmor(self) -> Optional[str]:
        """Check AppArmor status."""
        if os.path.exists('/sys/kernel/security/apparmor'):
            stdout, _, rc = self._run_command(['aa-enabled'])
            if rc == 0 and 'Yes' in stdout:
                return "AppArmor is enabled. Please disable it first."
        return None

    def _check_selinux(self) -> Optional[str]:
        """Check SELinux status."""
        if os.path.exists('/sys/kernel/security/selinux') or os.path.exists('/sys/fs/selinux'):
            # Try getenforce
            stdout, _, rc = self._run_command(['getenforce'])
            if rc == 0:
                if 'enforcing' in stdout.lower():
                    return "SELinux is enforcing. Please disable it first."
            else:
                # Try sestatus
                stdout, _, rc = self._run_command(['sestatus'])
                if rc == 0 and 'current mode: enforcing' in stdout.lower():
                    return "SELinux is enforcing. Please disable it first."
        return None

    def _check_kernel_errors(self) -> Optional[str]:
        """Check for non-informative kernel messages."""
        stdout, _, rc = self._run_command(['dmesg'])
        if rc == 0:
            pattern = r'AER: \(Corrected error message|Multiple Corrected error\) received'
            matches = re.findall(pattern, stdout, re.IGNORECASE)
            if len(matches) > 9:
                return "Too many AER errors. Use pcie_aspm=off, pci=nomsi or pci=noaer boot options."
        return None

    def _detect_distro(self) -> Dict[str, str]:
        """Detect ALT Linux distribution and repository."""
        result = {
            'distro': '',
            'distro_name': '',
            'repo': '',
            'have_altsp': False,
            'have_systemd': False,
            'have_xorg': False,
            'have_kde5': False,
            'have_mate': False,
            'have_xfce': False,
            'have_gnome': False,
        }

        # Read /etc/os-release
        os_release_path = '/etc/os-release'
        if not os.path.exists(os_release_path):
            return result

        try:
            with open(os_release_path, 'r') as f:
                content = f.read()

            distro_id = ''
            distro_name = ''
            pretty_name = ''
            version_id = ''

            for line in content.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"')
                    if key == 'ID':
                        distro_id = value
                    elif key == 'NAME':
                        distro_name = value
                    elif key == 'PRETTY_NAME':
                        pretty_name = value
                    elif key == 'VERSION_ID':
                        version_id = value

            if 'altlinux' not in distro_id:
                return result

            result['distro_name'] = distro_name
            distro_name_lower = distro_name.lower()
            pretty_name_lower = pretty_name.lower()

            # Detect distro type
            if 'myoffice plus' in distro_name_lower:
                result['distro'] = 'WS'
                result['repo'] = 'p10'
            elif 'alt tonk' in distro_name_lower:
                result['distro'] = 'WS'
            elif 'sisyphus' in distro_name_lower or 'regular' in pretty_name_lower:
                result['distro'] = 'REG'
                result['repo'] = 'Sisyphus'
            elif 'starter' in distro_name_lower or 'starterkit' in pretty_name_lower:
                result['distro'] = 'SKIT'
            elif 'simply' in distro_name_lower or 'simply' in pretty_name_lower:
                result['distro'] = 'SL'
            elif 'workstation k' in pretty_name_lower or 'k workstation' in pretty_name_lower:
                result['distro'] = 'KWS'
            elif 'workstation' in distro_name_lower or 'workstation' in pretty_name_lower:
                result['distro'] = 'WS'
            elif 'education' in distro_name_lower or 'education' in pretty_name_lower:
                result['distro'] = 'EDU'
            elif 'server-v' in distro_name_lower or 'virtualization server' in pretty_name_lower:
                result['distro'] = 'ASV'
            elif 'server' in distro_name_lower or 'server' in pretty_name_lower:
                result['distro'] = 'SRV'

            # Check for ALT SP
            if ('alt 8 sp' in distro_name_lower or 'alt sp' in distro_name_lower or
                'alt 8 sp' in pretty_name_lower or 'alt sp' in pretty_name_lower or
                '(cliff)' in distro_name_lower or '(cliff)' in pretty_name_lower):
                if result['distro'] in ['WS', 'SRV']:
                    result['have_altsp'] = True

            # Detect repo for ALT SP
            if result['have_altsp'] and not result['repo']:
                if version_id == '8.2':
                    result['repo'] = 'c9f1'
                elif version_id == '8.4':
                    result['repo'] = 'c9f2'
                elif version_id in ['10', '10.0']:
                    result['repo'] = 'c10f1'
                elif version_id in ['10.2', '10.2.1']:
                    result['repo'] = 'c10f2'

            # Detect repo for regular distros
            if not result['repo']:
                if version_id.startswith('9') or version_id.startswith('p9'):
                    result['repo'] = 'p9'
                elif version_id.startswith('10') or version_id.startswith('p10'):
                    result['repo'] = 'p10'
                elif version_id.startswith('11') or version_id.startswith('p11'):
                    result['repo'] = 'p11'

            # Check systemd
            if os.path.exists('/run/systemd/system'):
                result['have_systemd'] = True

            # Check desktop environments
            if os.path.exists('/usr/bin/Xorg') or os.path.exists('/usr/bin/Xwayland'):
                result['have_xorg'] = True

            # Check installed DE packages
            stdout, _, rc = self._run_command(['rpm', '-q', 'gnome-shell'])
            if rc == 0:
                result['have_gnome'] = True
                result['have_xorg'] = True

            stdout, _, rc = self._run_command(['rpm', '-q', 'kde5'])
            if rc == 0:
                result['have_kde5'] = True
                result['have_xorg'] = True

            stdout, _, rc = self._run_command(['rpm', '-q', 'mate-minimal'])
            if rc == 0:
                result['have_mate'] = True
                result['have_xorg'] = True

            stdout, _, rc = self._run_command(['rpm', '-q', 'xfce4-minimal'])
            if rc == 0:
                result['have_xfce'] = True
                result['have_xorg'] = True

        except Exception as e:
            self.logger.warning(f"Distro detection failed: {e}")

        return result

    def execute(self) -> StepResult:
        """Execute system preparation checks."""
        errors = []
        warnings = []

        self.logger.info("Starting system preparation checks...")

        try:
            # Check security modules
            ima_evm_error = self._check_ima_evm()
            if ima_evm_error:
                errors.append(ima_evm_error)

            apparmor_error = self._check_apparmor()
            if apparmor_error:
                errors.append(apparmor_error)

            selinux_error = self._check_selinux()
            if selinux_error:
                errors.append(selinux_error)

            kernel_error = self._check_kernel_errors()
            if kernel_error:
                warnings.append(kernel_error)

            # Detect distribution
            distro_info = self._detect_distro()
            self.system_info.update(distro_info)

            # Check if ALT Linux
            if not distro_info.get('distro'):
                errors.append("ALT Linux or compatible distro is required")

            # Build summary
            summary = {
                'distro': distro_info.get('distro', 'unknown'),
                'distro_name': distro_info.get('distro_name', 'unknown'),
                'repo': distro_info.get('repo', 'unknown'),
                'have_altsp': distro_info.get('have_altsp', False),
                'have_systemd': distro_info.get('have_systemd', False),
                'have_xorg': distro_info.get('have_xorg', False),
                'desktop': 'unknown',
            }

            # Determine desktop
            if distro_info.get('have_gnome'):
                summary['desktop'] = 'GNOME'
            elif distro_info.get('have_kde5'):
                summary['desktop'] = 'KDE'
            elif distro_info.get('have_mate'):
                summary['desktop'] = 'MATE'
            elif distro_info.get('have_xfce'):
                summary['desktop'] = 'XFCE'
            elif not distro_info.get('have_xorg'):
                summary['desktop'] = 'None (text mode)'

            # Determine status
            if errors:
                status = TestStatus.FAILED
                message = "System preparation failed"
            elif warnings:
                status = TestStatus.WARNING
                message = "System preparation completed with warnings"
            else:
                status = TestStatus.PASSED
                message = "System preparation completed successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.exception(f"System preparation failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"System preparation failed: {str(e)}",
                errors=[str(e)]
            )
