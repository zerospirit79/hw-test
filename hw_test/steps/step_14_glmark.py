"""Step 7: Graphics Test."""

from __future__ import annotations

import os
import subprocess
from typing import List, Dict, Any, Optional, Tuple

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class GlmarkStep(BaseHWStep):
    """
    Graphics performance test using glmark2.

    Tests:
    - 3D rendering performance
    - OpenGL capabilities
    - Frame rate measurement
    - Graphics driver verification
    """

    name = "Graphics Test"
    description = "Test 3D graphics performance using glmark2"
    requires_root = False  # Can run as user or root

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.graphics_info: Dict[str, Any] = {}

    def _run_command(
        self, cmd: List[str], timeout: int = 120, use_root: bool = False
    ) -> Tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _check_glmark2(self) -> bool:
        """Check if glmark2 is installed."""
        stdout, _, rc = self.run_command(["which", "glmark2"])
        return rc == 0

    def _check_xorg(self) -> bool:
        """Check if X server is running."""
        display = os.environ.get("DISPLAY")
        if not display:
            return False

        stdout, _, rc = self.run_command(["xdpyinfo"])
        return rc == 0

    def _get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information."""
        gpu_info = {
            "vendor": "",
            "model": "",
            "driver": "",
            "opengl_version": "",
            "glx_vendor": "",
            "glx_version": "",
        }

        # Get GPU from lspci
        stdout, _, rc = self._run_command(["lspci", "-nn"])
        if rc == 0:
            for line in stdout.split("\n"):
                if "VGA" in line or "3D" in line or "Display" in line:
                    gpu_info["model"] = line.split(":")[-1].strip()
                    # Detect vendor
                    if "Intel" in line:
                        gpu_info["vendor"] = "Intel"
                    elif "AMD" in line or "ATI" in line:
                        gpu_info["vendor"] = "AMD"
                    elif "NVIDIA" in line or "nVIDIA" in line:
                        gpu_info["vendor"] = "NVIDIA"
                    break

        # Get OpenGL info from glxinfo
        stdout, _, rc = self._run_command(["glxinfo", "-B"])
        if rc == 0:
            for line in stdout.split("\n"):
                if "OpenGL version" in line:
                    gpu_info["opengl_version"] = line.split(":")[-1].strip()
                elif "OpenGL vendor" in line:
                    gpu_info["vendor"] = line.split(":")[-1].strip()
                elif "OpenGL renderer" in line:
                    gpu_info["model"] = line.split(":")[-1].strip()
                elif "GLX vendor" in line:
                    gpu_info["glx_vendor"] = line.split(":")[-1].strip()
                elif "GLX version" in line:
                    gpu_info["glx_version"] = line.split(":")[-1].strip()

        # Detect driver
        stdout, _, rc = self._run_command(["glxinfo"])
        if rc == 0:
            if "Mesa" in stdout:
                gpu_info["driver"] = "Mesa"
            elif "NVIDIA" in stdout:
                gpu_info["driver"] = "NVIDIA proprietary"

        return gpu_info

    def _run_glmark2(self) -> Dict[str, Any]:
        """Run glmark2 benchmark."""
        result = {
            "score": None,
            "passed": False,
            "output": "",
        }

        try:
            # Run glmark2
            stdout, stderr, rc = self._run_command(["glmark2"])

            result["output"] = stdout[:1000] if stdout else stderr[:1000]

            if rc == 0:
                # Parse score from output
                import re

                match = re.search(r"glmark2 Score: (\d+)", stdout)
                if match:
                    result["score"] = int(match.group(1))
                    result["passed"] = True
                else:
                    # Alternative pattern
                    match = re.search(r"Score: (\d+)", stdout)
                    if match:
                        result["score"] = int(match.group(1))
                        result["passed"] = True
            else:
                result["error"] = stderr[:200]

        except subprocess.TimeoutExpired:
            result["error"] = "Benchmark timed out"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _run_glmark2_es2(self) -> Dict[str, Any]:
        """Run glmark2-es2 benchmark (OpenGL ES 2.0)."""
        result = {
            "score": None,
            "passed": False,
            "output": "",
        }

        try:
            stdout, stderr, rc = self._run_command(["glmark2-es2"])

            result["output"] = stdout[:1000] if stdout else stderr[:1000]

            if rc == 0:
                import re

                match = re.search(r"glmark2 Score: (\d+)", stdout)
                if match:
                    result["score"] = int(match.group(1))
                    result["passed"] = True

        except Exception as e:
            result["error"] = str(e)

        return result

    def _check_direct_rendering(self) -> bool:
        """Check if direct rendering is enabled."""
        stdout, _, rc = self._run_command(["glxinfo"])
        if rc == 0 and "direct rendering: Yes" in stdout:
            return True
        return False

    def execute(self) -> StepResult:
        """Execute graphics test."""
        errors = []
        warnings = []

        self.logger.info("Starting graphics test...")

        try:
            # Check prerequisites
            has_glmark2 = self._check_glmark2()
            has_xorg = self._check_xorg()
            direct_rendering = self._check_direct_rendering()

            # Get GPU info
            gpu_info = self._get_gpu_info()

            if not has_xorg:
                return StepResult(
                    step_name=self.name,
                    status=TestStatus.SKIPPED,
                    message="X server is not running. Graphics test requires X11.",
                    details={"xorg_running": False},
                )

            if not has_glmark2:
                # Try to install glmark2
                self.logger.info("glmark2 not found, attempting to install...")
                stdout, stderr, rc = self._run_command(
                    ["apt-get", "install", "-y", "glmark2"], timeout=120, use_root=True
                )
                if rc != 0:
                    return StepResult(
                        step_name=self.name,
                        status=TestStatus.SKIPPED,
                        message="glmark2 is not installed and could not be installed",
                        details={"glmark2_available": False},
                        warnings=["glmark2 package not available"],
                    )
                has_glmark2 = True

            # Run benchmarks
            glmark2_result = None
            glmark2_es2_result = None

            if has_glmark2:
                self.logger.info("Running glmark2...")
                glmark2_result = self._run_glmark2()

                # Also try ES2 if available
                stdout, _, rc = self._run_command(["which", "glmark2-es2"])
                if rc == 0:
                    self.logger.info("Running glmark2-es2...")
                    glmark2_es2_result = self._run_glmark2_es2()

            # Build summary
            summary = {
                "gpu_info": gpu_info,
                "direct_rendering": direct_rendering,
                "glmark2_available": has_glmark2,
                "glmark2_result": glmark2_result,
                "glmark2_es2_result": glmark2_es2_result,
            }

            # Determine status
            if glmark2_result and glmark2_result.get("passed"):
                status = TestStatus.PASSED
                message = f"Graphics test passed. Score: {glmark2_result['score']}"
                summary["score"] = glmark2_result["score"]
            elif glmark2_result and glmark2_result.get("error"):
                status = TestStatus.WARNING
                message = f"Graphics test completed with issues: {glmark2_result['error']}"
                warnings.append(glmark2_result["error"])
            else:
                status = TestStatus.WARNING
                message = "Graphics test completed but no score obtained"
                warnings.append("Could not obtain glmark2 score")

            self.graphics_info = summary

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.exception(f"Graphics test failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Graphics test failed: {str(e)}",
                errors=[str(e)],
            )
