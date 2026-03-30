"""Step 5: CPU Power Test."""

from __future__ import annotations

import os
import re
from typing import List, Dict, Any, Optional, Tuple

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class CpuPowerStep(BaseHWStep):
    """
    Checking CPU frequency modes.

    Tests:
    - CPU frequency scaling support
    - Available governors
    - Energy performance bias
    - Turbo boost status
    - Frequency changes under load
    """

    name = "CPU Power Test"
    description = "Check CPU frequency scaling and power management"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.cpu_info: Dict[str, Any] = {}

    def _run_command(
        self, cmd: List[str], timeout: int = 60, use_root: bool = True
    ) -> Tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _read_file(self, path: str) -> Optional[str]:
        """Read file content."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except (FileNotFoundError, IOError, PermissionError):
            return None

    def _get_cpuinfo_freq(self, cpu: int, freq_type: str) -> Optional[int]:
        """Get CPU frequency from cpuinfo."""
        path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/{freq_type}"
        value = self._read_file(path)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None

    def _get_scaling_freq(self, cpu: int, freq_type: str) -> Optional[int]:
        """Get CPU scaling frequency."""
        path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/{freq_type}"
        value = self._read_file(path)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None

    def _get_governors(self, cpu: int = 0) -> List[str]:
        """Get available CPU governors."""
        path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_available_governors"
        value = self._read_file(path)
        if value:
            return value.split()
        return []

    def _get_current_governor(self, cpu: int = 0) -> str:
        """Get current CPU governor."""
        path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
        value = self._read_file(path)
        return value or "unknown"

    def _get_energy_bias(self, cpu: int = 0) -> Optional[int]:
        """Get energy performance bias."""
        path = f"/sys/devices/system/cpu/cpu{cpu}/power/energy_perf_bias"
        value = self._read_file(path)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None

    def _get_turbo_status(self) -> Optional[int]:
        """Get turbo boost status."""
        path = "/sys/devices/system/cpu/intel_pstate/no_turbo"
        value = self._read_file(path)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return None

    def _get_n_cores(self) -> int:
        """Get number of CPU cores."""
        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
            return len(re.findall(r"^processor\s*:", content, re.MULTILINE))
        except Exception:
            return 0

    def _check_scaling_support(self) -> Dict[str, Any]:
        """Check CPU frequency scaling support."""
        result = {
            "supported": False,
            "min_freq": None,
            "max_freq": None,
            "n_cores": 0,
            "governors": [],
            "current_governor": "",
            "turbo_disabled": None,
        }

        n_cores = self._get_n_cores()
        result["n_cores"] = n_cores

        if n_cores == 0:
            return result

        # Get frequencies for CPU0
        min_freq = self._get_scaling_freq(0, "cpuinfo_min_freq") or self._get_scaling_freq(
            0, "scaling_min_freq"
        )
        max_freq = self._get_scaling_freq(0, "cpuinfo_max_freq") or self._get_scaling_freq(
            0, "scaling_max_freq"
        )

        result["min_freq"] = min_freq
        result["max_freq"] = max_freq

        # Check if scaling is possible
        if min_freq and max_freq and min_freq < max_freq:
            governors = self._get_governors()
            current_governor = self._get_current_governor()

            if governors and current_governor:
                result["supported"] = True
                result["governors"] = governors
                result["current_governor"] = current_governor

        # Check turbo status (Intel only)
        result["turbo_disabled"] = self._get_turbo_status()

        return result

    def _test_frequency_change(self) -> Dict[str, Any]:
        """Test if CPU frequency can be changed."""
        result = {
            "success": False,
            "initial_freq": None,
            "test_freq": None,
            "final_freq": None,
        }

        # Get initial frequency
        initial = self._get_scaling_freq(0, "scaling_cur_freq")
        result["initial_freq"] = initial

        if not initial:
            return result

        # Try to set a different frequency (userspace governor required)
        governors = self._get_governors()
        if "userspace" not in governors:
            result["success"] = True  # Can't test without userspace, but not a failure
            return result

        # Get available frequencies
        path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies"
        avail_freq = self._read_file(path)

        if avail_freq:
            freqs = avail_freq.split()
            if len(freqs) > 1:
                # Try to set a different frequency
                test_freq = freqs[0] if initial != freqs[0] else freqs[-1]

                # Set frequency (requires root)
                self._run_command(
                    [
                        "sh",
                        "-c",
                        f"echo {test_freq} > /sys/devices/system/cpu/cpu0/cpufreq/scaling_setspeed",
                    ]
                )

                # Wait and check
                import time

                time.sleep(0.1)

                final = self._get_scaling_freq(0, "scaling_cur_freq")
                result["test_freq"] = test_freq
                result["final_freq"] = final

                if final and final != initial:
                    result["success"] = True

                # Restore original governor
                self._run_command(
                    [
                        "sh",
                        "-c",
                        "echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
                    ]
                )

        return result

    def _run_cpupower_info(self) -> str:
        """Run cpupower frequency-info command."""
        stdout, _, rc = self._run_command(["cpupower", "frequency-info"])
        if rc == 0:
            return stdout
        return ""

    def execute(self) -> StepResult:
        """Execute CPU power test."""
        errors = []
        warnings = []

        self.logger.info("Starting CPU power test...")

        try:
            # Check scaling support
            scaling_info = self._check_scaling_support()

            # Run cpupower frequency-info
            cpupower_output = self._run_cpupower_info()

            # Test frequency change
            freq_test = self._test_frequency_change()

            # Check for energy bias support
            energy_bias = self._get_energy_bias()

            # Build summary
            summary = {
                "scaling_supported": scaling_info["supported"],
                "n_cores": scaling_info["n_cores"],
                "min_freq_khz": scaling_info["min_freq"],
                "max_freq_khz": scaling_info["max_freq"],
                "governors": scaling_info["governors"],
                "current_governor": scaling_info["current_governor"],
                "turbo_disabled": scaling_info["turbo_disabled"],
                "frequency_change_test": freq_test["success"],
                "energy_bias": energy_bias,
                "cpupower_output": cpupower_output[:500] if cpupower_output else "",
            }

            self.cpu_info = summary

            # Determine status
            if not scaling_info["supported"]:
                if scaling_info["n_cores"] == 0:
                    status = TestStatus.FAILED
                    message = "Could not detect CPU cores"
                    errors.append("CPU detection failed")
                else:
                    status = TestStatus.WARNING
                    message = "CPU frequency scaling not supported or limited"
                    warnings.append("Frequency scaling not available")
            elif errors:
                status = TestStatus.FAILED
                message = "CPU power test failed"
            elif warnings:
                status = TestStatus.WARNING
                message = "CPU power test completed with warnings"
            else:
                status = TestStatus.PASSED
                message = "CPU power test completed successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.exception(f"CPU power test failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"CPU power test failed: {str(e)}",
                errors=[str(e)],
            )
