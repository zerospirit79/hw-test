"""Step: System Logs Check."""

from __future__ import annotations

import os
import gzip
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class SyslogsStep(BaseHWStep):
    """
    Checking and saving system logs.

    Collects:
    - dmesg output and errors
    - Failed systemd services
    - Journal errors
    - System log analysis
    """

    name = "System Logs Check"
    description = "Check and save system logs for analysis"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.logs_dir: Optional[Path] = None
        self.errors_found: List[str] = []

    def _run_command(
        self, cmd: List[str], timeout: int = 60, use_root: bool = True
    ) -> Tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _gzip_compress(self, data: str) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data.encode("utf-8", errors="ignore"), compresslevel=9)

    def _save_file(self, filename: str, content: str, compress: bool = False) -> str:
        """Save content to file."""
        filepath = self.logs_dir / filename
        try:
            if compress:
                with open(filepath, "wb") as f:
                    f.write(self._gzip_compress(content))
            else:
                with open(filepath, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(content)
            return str(filepath)
        except Exception as e:
            self.logger.warning(f"Failed to save {filename}: {e}")
            return ""

    def _check_dmesg(self) -> Dict[str, Any]:
        """Check dmesg for errors."""
        result = {
            "dmesg_saved": False,
            "dmesg_errors_saved": False,
            "error_count": 0,
            "warning_count": 0,
            "panic_count": 0,
            "fatal_count": 0,
        }

        try:
            # Get full dmesg
            stdout, _, rc = self._run_command(["dmesg", "-H", "-P", "--color=always"])
            if rc == 0 and stdout:
                self._save_file("dmesg.txt", stdout, compress=True)
                result["dmesg_saved"] = True

            # Get dmesg errors
            filter_pattern = r"(panic|fatal|fail|error|warning)"
            stdout, _, rc = self._run_command(["dmesg"])
            if rc == 0:
                errors = []
                for line in stdout.split("\n"):
                    if "Command line:" in line or "Kernel command line:" in line:
                        continue
                    if any(
                        kw in line.lower() for kw in ["panic", "fatal", "fail", "error", "warning"]
                    ):
                        errors.append(line)
                        if "panic" in line.lower():
                            result["panic_count"] += 1
                        elif "fatal" in line.lower():
                            result["fatal_count"] += 1
                        elif "fail" in line.lower():
                            result["error_count"] += 1
                        elif "error" in line.lower():
                            result["error_count"] += 1
                        elif "warning" in line.lower():
                            result["warning_count"] += 1

                if errors:
                    self._save_file("dmesg_errors.txt", "\n".join(errors), compress=True)
                    result["dmesg_errors_saved"] = True
                    self.errors_found.extend(errors[:10])  # First 10 errors

        except Exception as e:
            self.logger.warning(f"dmesg check failed: {e}")

        return result

    def _check_systemd(self) -> Dict[str, Any]:
        """Check systemd services and journal."""
        result = {
            "systemd_detected": False,
            "failed_services": [],
            "journal_saved": False,
            "journal_errors_saved": False,
            "failed_services_saved": False,
        }

        # Check if systemd is available
        if not os.path.exists("/run/systemd/system"):
            return result

        result["systemd_detected"] = True

        try:
            # Get failed services
            stdout, _, rc = self._run_command(["systemctl", "--failed", "--no-pager"])
            if rc == 0 and stdout:
                failed = []
                for line in stdout.split("\n"):
                    if "failed" in line.lower() and not line.startswith("●"):
                        failed.append(line)

                if failed:
                    result["failed_services"] = failed
                    self._save_file("failed_services.txt", "\n".join(failed), compress=True)
                    result["failed_services_saved"] = True
                    self.errors_found.extend(failed)

            # Get journal
            stdout, _, rc = self._run_command(["journalctl", "-b", "--no-pager"])
            if rc == 0 and stdout:
                self._save_file("journal.txt", stdout, compress=True)
                result["journal_saved"] = True

            # Get journal errors
            stdout, _, rc = self._run_command(["journalctl", "-p", "err", "-b", "--no-pager"])
            if rc == 0 and stdout:
                self._save_file("journal_errors.txt", stdout, compress=True)
                result["journal_errors_saved"] = True

            # Critical chain (if devel_test enabled)
            if self.config.verbose:
                stdout, _, rc = self._run_command(
                    ["systemd-analyze", "critical-chain", "--no-pager"]
                )
                if rc == 0 and stdout:
                    self._save_file("critical_chain.txt", stdout)

                stdout, _, rc = self._run_command(["systemd-analyze", "blame", "--no-pager"])
                if rc == 0 and stdout:
                    self._save_file("systemd_blame.txt", stdout)

        except Exception as e:
            self.logger.warning(f"systemd check failed: {e}")

        return result

    def _check_legacy_logs(self) -> Dict[str, Any]:
        """Check legacy log files."""
        result = {
            "syslog_saved": False,
            "messages_saved": False,
            "kern_saved": False,
            "apt_history_saved": False,
        }

        log_files = {
            "/var/log/syslog": "syslog.txt",
            "/var/log/messages": "messages.txt",
            "/var/log/kern.log": "kern.log",
            "/var/log/apt/history.log": "apt_history.txt",
        }

        for src, dest in log_files.items():
            if os.path.exists(src):
                try:
                    with open(src, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    self._save_file(dest, content, compress=True)
                    result[dest.replace(".txt", "").replace(".log", "") + "_saved"] = True
                except Exception as e:
                    self.logger.debug(f"Failed to read {src}: {e}")

        return result

    def execute(self) -> StepResult:
        """Execute system logs check."""
        errors = []
        warnings = []

        self.logger.info("Starting system logs check...")

        try:
            # Create logs directory
            self.logs_dir = Path(self.config.data_dir) / "logs"
            self.logs_dir.mkdir(parents=True, exist_ok=True)

            # Check dmesg
            dmesg_result = self._check_dmesg()

            # Check systemd
            systemd_result = self._check_systemd()

            # Check legacy logs
            legacy_result = self._check_legacy_logs()

            # Build summary
            summary = {
                "dmesg": dmesg_result,
                "systemd": systemd_result,
                "legacy_logs": legacy_result,
                "total_errors": len(self.errors_found),
                "logs_dir": str(self.logs_dir),
            }

            # Determine status
            critical_errors = dmesg_result.get("panic_count", 0) + dmesg_result.get(
                "fatal_count", 0
            )
            if critical_errors > 0:
                status = TestStatus.FAILED
                message = f"Critical errors found: {critical_errors} panic/fatal"
                errors.append(f"Found {critical_errors} critical kernel messages")
            elif self.errors_found:
                status = TestStatus.WARNING
                message = f"Logs check completed with {len(self.errors_found)} warnings/errors"
                warnings.extend(self.errors_found[:5])  # First 5
            else:
                status = TestStatus.PASSED
                message = "System logs check completed successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.exception(f"System logs check failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"System logs check failed: {str(e)}",
                errors=[str(e)],
            )
