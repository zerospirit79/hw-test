"""Step 3: Configuration."""

import os
from typing import List, Dict, Any, Optional

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class ConfigStep(BaseHWStep):
    """
    Defining a test plan.
    
    Allows configuration of:
    - Test selection
    - Test parameters
    - Desktop environment options
    """

    name = "Configuration"
    description = "Define test plan and configuration options"
    requires_root = False

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.config_options: Dict[str, Any] = {}

    def _check_gui_available(self) -> bool:
        """Check if GUI configuration is available."""
        display = os.environ.get('DISPLAY')
        if not display:
            return False

        # Check for yad (preferred GUI tool)
        stdout, _, rc = self.run_command(['which', 'yad'])
        if rc == 0:
            return True

        # Check for dialog as fallback
        stdout, _, rc = self.run_command(['which', 'dialog'])
        return rc == 0

    def _detect_test_capabilities(self) -> Dict[str, bool]:
        """Detect available test capabilities."""
        capabilities = {
            'fwupd_test': False,
            'devel_test': False,
            'xprss_test': False,
            'infb_test': False,
            'sound_test': False,
            'numa_test': False,
            'ipmi_test': False,
            'webcam_test': False,
            'power_test': False,
            'fprnt_test': False,
            'bluez_test': False,
            'scard_test': False,
            'fio_test': False,
            'v3d_test': False,
        }

        # Check for fwupd (firmware updates)
        stdout, _, rc = self.run_command(['which', 'fwupdmgr'])
        if rc == 0:
            capabilities['fwupd_test'] = True

        # Check for Infiniband/RDMA
        stdout, _, rc = self.run_command(['lspci'])
        if rc == 0:
            if 'RDMA' in stdout or 'InfiniBand' in stdout:
                capabilities['infb_test'] = True

        # Check for sound cards
        stdout, _, rc = self.run_command(['aplay', '-l'])
        if rc == 0 and 'card' in stdout:
            capabilities['sound_test'] = True

        # Check for NUMA
        stdout, _, rc = self.run_command(['lscpu', '--parse=NODE'])
        if rc == 0:
            nodes = set()
            for line in stdout.split('\n'):
                if line and not line.startswith('#'):
                    parts = line.split(',')
                    if len(parts) >= 1 and parts[0].isdigit():
                        nodes.add(parts[0])
            if len(nodes) > 1:
                capabilities['numa_test'] = True

        # Check for webcams
        stdout, _, rc = self.run_command(['ls /dev/video* 2>/dev/null || true'], use_root=False)
        if rc == 0 and '/dev/video' in stdout:
            capabilities['webcam_test'] = True

        # Check for fingerprint readers
        stdout, _, rc = self.run_command(['lsusb'])
        if rc == 0:
            fp_keywords = ['Fingerprint', '298d:1010', '1c7a:', 'U.are.U', 'TouchChip',
                          'TouchStrip', 'Elan MOC', 'Veridicom', 'Synaptics',
                          'AuthenTec', 'Validity VFS']
            for keyword in fp_keywords:
                if keyword in stdout:
                    capabilities['fprnt_test'] = True
                    break

        # Check for Bluetooth
        stdout, _, rc = self.run_command(['hciconfig', '-a'])
        if rc == 0 and 'hci' in stdout:
            capabilities['bluez_test'] = True

        # Check for smart card readers
        stdout, _, rc = self.run_command(['opensc-tool', '--list-readers'])
        if rc == 0 and 'No smart card' not in stdout:
            capabilities['scard_test'] = True

        return capabilities

    def _get_default_tests(self, capabilities: Dict[str, bool]) -> List[str]:
        """Get default test selection based on capabilities."""
        tests = []

        # Always include basic tests
        tests.extend([
            'hardware_detection',
            'system_check',
            'log_collection',
        ])

        # Add capability-based tests
        if capabilities.get('fwupd_test'):
            tests.append('firmware_check')

        if capabilities.get('sound_test'):
            tests.append('express_test')

        if capabilities.get('numa_test'):
            tests.append('performance')

        return tests

    def execute(self) -> StepResult:
        """Execute configuration step."""
        errors = []
        warnings = []

        self.logger.info("Starting configuration...")

        try:
            # Check if GUI is available
            gui_available = self._check_gui_available()

            # Detect test capabilities
            capabilities = self._detect_test_capabilities()

            # Get default test selection
            default_tests = self._get_default_tests(capabilities)

            # Build configuration
            self.config_options = {
                'gui_available': gui_available,
                'capabilities': capabilities,
                'default_tests': default_tests,
                'batch_mode': self.config.batch_mode,
                'selected_tests': default_tests if self.config.batch_mode else [],
            }

            # In interactive mode, we would show a configuration dialog
            # For now, just log the configuration
            self.logger.info(f"GUI available: {gui_available}")
            self.logger.info(f"Capabilities: {capabilities}")
            self.logger.info(f"Default tests: {default_tests}")

            # Build summary
            summary = {
                'gui_available': gui_available,
                'tests_available': sum(1 for v in capabilities.values() if v),
                'tests_selected': len(default_tests),
                'batch_mode': self.config.batch_mode,
            }

            # Determine status
            if errors:
                status = TestStatus.FAILED
                message = "Configuration failed"
            elif warnings:
                status = TestStatus.WARNING
                message = "Configuration completed with warnings"
            else:
                status = TestStatus.PASSED
                message = "Configuration completed successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.exception(f"Configuration failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Configuration failed: {str(e)}",
                errors=[str(e)]
            )
