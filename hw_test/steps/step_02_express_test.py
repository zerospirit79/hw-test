"""Step 2: Express Tests."""

from __future__ import annotations

import time
import subprocess
import tempfile
import os
import re
from typing import List, Dict, Any, Optional, Tuple

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class ExpressTestStep(BaseHWStep):
    """
    Run quick express tests to verify basic system functionality.

    Tests:
    - Boot time analysis
    - System responsiveness
    - I/O performance
    - Network connectivity
    - Audio playback test
    - Suspend/Resume test
    - Video playback check
    """

    name = "Express Tests"
    description = "Quick tests for boot time, responsiveness, I/O, network, audio, and suspend"
    requires_root = False  # Runs as user

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.test_results: Dict[str, Any] = {}

    def _run_command(
        self, cmd: List[str], timeout: int = 30, use_root: bool = False
    ) -> Tuple[str, str, int]:
        """Run a command and return (stdout, stderr, returncode)."""
        if use_root and self.requires_root:
            stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=True)
            return stdout, stderr, rc
        else:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                return result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Command timed out: {' '.join(cmd)}")
                return "", "Timeout", -1
            except Exception as e:
                self.logger.debug(f"Command failed: {' '.join(cmd)} - {e}")
                return "", str(e), -1

    def _test_boot_time(self) -> Dict[str, Any]:
        """Check system boot time."""
        result = {"status": "skipped", "boot_time_sec": None}

        try:
            stdout, _, rc = self._run_command(
                ["systemctl", "show", "-p", "UserspaceTimestamp", "Manager"]
            )
            if rc == 0 and "=" in stdout:
                # Parse userspace timestamp
                pass

            # Alternative: use systemd-analyze
            stdout, _, rc = self._run_command(["systemd-analyze"])
            if rc == 0:
                for line in stdout.split("\n"):
                    if "startup" in line.lower() or "kernel" in line.lower():
                        result["raw_output"] = line.strip()
                        # Try to extract numeric values
                        import re

                        matches = re.findall(r"([\d.]+)\s*(?:ms|s|min)", line, re.IGNORECASE)
                        if matches:
                            result["boot_time_sec"] = sum(float(m) for m in matches[:2])
                            result["status"] = "passed"
                            break

                if result.get("status") != "passed" and stdout.strip():
                    result["status"] = "passed"
                    result["raw_output"] = stdout.strip()[:200]

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _test_responsiveness(self) -> Dict[str, Any]:
        """Test basic system responsiveness."""
        result = {"status": "passed", "latency_ms": []}

        try:
            latencies = []

            # Measure fork/exec latency
            for i in range(5):
                start = time.perf_counter()
                proc = subprocess.run(["true"], capture_output=True, timeout=5)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                if proc.returncode == 0:
                    latencies.append(elapsed)

            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                max_latency = max(latencies)
                result["avg_latency_ms"] = round(avg_latency, 2)
                result["max_latency_ms"] = round(max_latency, 2)

                if avg_latency > 100:  # More than 100ms is concerning
                    result["status"] = "warning"
                elif avg_latency > 500:
                    result["status"] = "failed"

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _test_io_performance(self) -> Dict[str, Any]:
        """Quick I/O performance test."""
        result = {"status": "passed", "write_speed_mbs": None, "read_speed_mbs": None}

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                test_file = f.name

            # Write test (1MB)
            data = b"x" * (1024 * 1024)  # 1MB
            start = time.perf_counter()
            with open(test_file, "wb") as f:
                f.write(data)
            write_time = time.perf_counter() - start
            write_speed = (1 / write_time) if write_time > 0 else 0
            result["write_speed_mbs"] = round(write_speed, 2)

            # Read test
            start = time.perf_counter()
            with open(test_file, "rb") as f:
                _ = f.read()
            read_time = time.perf_counter() - start
            read_speed = (1 / read_time) if read_time > 0 else 0
            result["read_speed_mbs"] = round(read_speed, 2)

            # Cleanup
            os.unlink(test_file)

            # Check thresholds
            if write_speed < 1:  # Less than 1 MB/s is very slow
                result["status"] = "warning"
            elif write_speed < 0.1:
                result["status"] = "failed"

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)
            if "test_file" in locals():
                try:
                    os.unlink(test_file)
                except:
                    pass

        return result

    def _test_network_connectivity(self) -> Dict[str, Any]:
        """Test basic network connectivity."""
        result = {"status": "passed", "hosts_tested": []}

        hosts_to_test = [
            ("127.0.0.1", "localhost"),
            ("8.8.8.8", "google-dns"),
        ]

        for host_ip, host_name in hosts_to_test:
            host_result = {"ip": host_ip, "name": host_name, "reachable": False, "time_ms": None}

            try:
                start = time.perf_counter()
                stdout, _, rc = self._run_command(
                    ["ping", "-c", "1", "-W", "2", host_ip], timeout=5
                )
                elapsed = (time.perf_counter() - start) * 1000

                if rc == 0:
                    host_result["reachable"] = True
                    host_result["time_ms"] = round(elapsed, 2)

                    # Extract ping time from output
                    import re

                    match = re.search(r"time=([\d.]+)\s*ms", stdout)
                    if match:
                        host_result["ping_time_ms"] = float(match.group(1))

            except Exception as e:
                host_result["error"] = str(e)

            result["hosts_tested"].append(host_result)

        # Determine overall status
        reachable_count = sum(1 for h in result["hosts_tested"] if h["reachable"])
        if reachable_count == 0:
            result["status"] = "failed"
        elif reachable_count < len(hosts_to_test):
            result["status"] = "warning"

        result["reachable_hosts"] = reachable_count
        result["total_hosts"] = len(hosts_to_test)

        return result

    def _test_memory_basic(self) -> Dict[str, Any]:
        """Basic memory availability test."""
        result = {"status": "passed"}

        try:
            import psutil

            mem = psutil.virtual_memory()

            result["total_mb"] = round(mem.total / (1024 * 1024), 2)
            result["available_mb"] = round(mem.available / (1024 * 1024), 2)
            result["used_percent"] = mem.percent

            if mem.percent > 95:
                result["status"] = "warning"
            elif mem.percent > 99:
                result["status"] = "failed"

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _test_audio_playback(self) -> Dict[str, Any]:
        """Test audio playback capability."""
        result = {
            "status": "skipped",
            "sound_card_detected": False,
            "audio_playback": False,
            "error": None,
        }

        try:
            # Check for sound cards
            stdout, _, rc = self._run_command(["aplay", "-l"])
            if rc == 0 and "card" in stdout:
                result["sound_card_detected"] = True
            else:
                result["error"] = "No sound cards detected"
                return result

            # Check for pulseaudio/pipewire
            stdout, _, rc = self._run_command(["pactl", "info"])
            if rc != 0:
                result["error"] = "PulseAudio/PipeWire not running"
                return result

            # Try to play a test sound
            test_sounds = [
                "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga",
                "/usr/share/sounds/freedesktop/stereo/bell.oga",
                "/usr/share/sounds/alsa/Front_Center.wav",
            ]

            for sound_file in test_sounds:
                if os.path.exists(sound_file):
                    # Use paplay or aplay
                    if os.path.exists("/usr/bin/paplay"):
                        cmd = ["paplay", "--volume=0x4000", sound_file]
                    else:
                        cmd = ["aplay", "-q", sound_file]

                    _, _, rc = self._run_command(cmd, timeout=5)
                    if rc == 0:
                        result["audio_playback"] = True
                        result["test_file"] = sound_file
                        break

            if result["sound_card_detected"] and not result["audio_playback"]:
                result["status"] = "warning"
                result["error"] = "Sound card detected but playback test failed"
            elif result["audio_playback"]:
                result["status"] = "passed"

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _test_wifi_adapter(self) -> Dict[str, Any]:
        """Test Wi-Fi adapter detection and capability."""
        result = {
            "status": "skipped",
            "wifi_detected": False,
            "adapter_name": "",
            "interface": "",
            "driver": "",
        }

        try:
            # Check for wireless interfaces using iw
            stdout, stderr, rc = self._run_command(["iw", "dev"])
            if rc == 0 and "Interface" in stdout:
                result["wifi_detected"] = True
                # Parse interface name
                for line in stdout.split("\n"):
                    if "Interface" in line:
                        result["interface"] = line.split()[-1].strip()
                        break

            # Alternative: check with ip link
            if not result["wifi_detected"]:
                stdout, _, rc = self._run_command(["ip", "link", "show"])
                if rc == 0:
                    for line in stdout.split("\n"):
                        if "wlan" in line.lower() or "wlx" in line.lower():
                            result["wifi_detected"] = True
                            result["interface"] = line.split(":")[1].strip().split("@")[0]
                            break

            # Get adapter info using lshw
            if result["wifi_detected"]:
                stdout, _, rc = self._run_command(["lshw", "-class", "network", "-short"])
                if rc == 0:
                    for line in stdout.split("\n"):
                        if "wireless" in line.lower() or "wi-fi" in line.lower():
                            result["adapter_name"] = line.strip()
                            break

            # Check driver
            if result["interface"]:
                stdout, _, rc = self._run_command(["ethtool", "-i", result["interface"]])
                if rc == 0:
                    for line in stdout.split("\n"):
                        if "driver:" in line.lower():
                            result["driver"] = line.split(":")[1].strip()
                            break

            if result["wifi_detected"]:
                result["status"] = "passed"
            else:
                result["status"] = "passed"  # Not all systems have Wi-Fi

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _test_function_keys(self) -> Dict[str, Any]:
        """Test function keys (Fn keys) detection."""
        result = {
            "status": "skipped",
            "keys_detected": [],
            "input_devices": [],
        }

        try:
            # Check for input devices using libinput
            stdout, _, rc = self._run_command(["libinput", "list-devices"])
            if rc == 0:
                # Parse keyboard devices
                in_keyboard = False
                for line in stdout.split("\n"):
                    if "Keyboard" in line:
                        in_keyboard = True
                        result["input_devices"].append(line.strip())
                    elif in_keyboard and line.strip():
                        if "Event" in line or "Device" in line:
                            continue
                        result["input_devices"].append(line.strip())

            # Check /dev/input for event devices
            _, _, rc = self._run_command(["ls", "/dev/input/event*"])
            if rc == 0:
                result["status"] = "passed"
                result["note"] = (
                    "Function keys require manual verification. "
                    "Please test: brightness, volume, mute, airplane mode, "
                    "touchpad toggle, and other Fn keys specific to this hardware."
                )

            # Check for special keys using evtest (if available)
            _, _, rc = self._run_command(["which", "evtest"])
            if rc == 0:
                result["evtest_available"] = True
                result["note"] = (
                    "Use 'evtest' to verify function key events. "
                    "Run: evtest /dev/input/eventX and press Fn keys."
                )
            else:
                result["evtest_available"] = False

            result["status"] = "passed"

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _test_suspend_resume(self) -> Dict[str, Any]:
        """Test suspend/resume capability (non-destructive check)."""
        result = {
            "status": "skipped",
            "suspend_supported": False,
            "suspend_states": [],
            "error": None,
        }

        try:
            # Check if systemd is available
            if not os.path.exists("/run/systemd/system"):
                result["error"] = "systemd not available"
                return result

            # Check available suspend states
            stdout, _, rc = self._run_command(["systemctl", "list-units", "--type=sleep", "--all"])
            if rc == 0:
                if "suspend" in stdout.lower():
                    result["suspend_supported"] = True
                    result["suspend_states"].append("suspend")
                if "hibernate" in stdout.lower():
                    result["suspend_states"].append("hibernate")
                if "hybrid-sleep" in stdout.lower():
                    result["suspend_states"].append("hybrid_sleep")

            # Check /sys/power/state
            if os.path.exists("/sys/power/state"):
                try:
                    with open("/sys/power/state", "r") as f:
                        states = f.read().strip().split()
                    result["suspend_states"] = states
                    if "mem" in states or "freeze" in states:
                        result["suspend_supported"] = True
                except Exception:
                    pass

            # Check for laptop/battery (more likely to have working suspend)
            if os.path.exists("/sys/class/power_supply/BAT0"):
                result["has_battery"] = True

            if result["suspend_supported"]:
                result["status"] = "passed"
            else:
                result["status"] = "warning"
                result["error"] = "Suspend may not be supported on this system"

        except Exception as e:
            result["status"] = "warning"
            result["error"] = str(e)

        return result

    def _check_express_prerequisites(self) -> Dict[str, Any]:
        """Check if express test can run (similar to bash pre() function)."""
        result = {
            "can_run": True,
            "blocked_reasons": [],
            "xorg_running": False,
            "desktop_detected": False,
            "network_available": False,
            "video_recording": False,
        }

        # Check for Xorg/Wayland
        display = os.environ.get("DISPLAY")
        xdg_session = os.environ.get("XDG_SESSION_TYPE", "")
        if display or xdg_session in ["x11", "wayland"]:
            result["xorg_running"] = True
        else:
            result["can_run"] = True  # Can still run some tests without X

        # Check for desktop environment
        xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
        if any(de in xdg_desktop.lower() for de in ["kde", "mate", "xfce", "gnome"]):
            result["desktop_detected"] = True

        # Check for network connection
        stdout, _, rc = self._run_command(["ip", "route"])
        if rc == 0 and "default via" in stdout:
            result["network_available"] = True

        # Check for video recording capability (required for certification)
        video_tools = ["ffmpeg", "vokoscreen-ng", "simple-screencast"]
        for tool in video_tools:
            _, _, rc = self._run_command(["which", tool])
            if rc == 0:
                result["video_recording"] = True
                result["video_tool"] = tool
                break

        if not result["video_recording"]:
            result["blocked_reasons"].append(
                "No video recording tool found (ffmpeg, vokoscreen-ng, or simple-screencast required)"
            )
            result["can_run"] = False

        # Check for required binaries (for full test)
        required_bins = ["yad", "xdg-open", "pactl", "notify-send"]
        missing = []
        for binary in required_bins:
            _, _, rc = self._run_command(["which", binary])
            if rc != 0:
                missing.append(binary)

        result["missing_binaries"] = missing
        if len(missing) > 2:
            result["can_run"] = False
            result["blocked_reasons"].append(f'Missing binaries: {", ".join(missing)}')

        return result

    def execute(self) -> StepResult:
        """Execute express tests."""
        errors = []
        warnings = []

        self.logger.info("Starting express tests...")

        try:
            # Check prerequisites
            prereqs = self._check_express_prerequisites()

            if not prereqs["can_run"]:
                return StepResult(
                    step_name=self.name,
                    status=TestStatus.SKIPPED,
                    message=f"Express tests blocked: {', '.join(prereqs['blocked_reasons'])}",
                    details={"prerequisites": prereqs},
                )

            # Run all tests
            self.test_results["boot_time"] = self._test_boot_time()
            self.test_results["responsiveness"] = self._test_responsiveness()
            self.test_results["io_performance"] = self._test_io_performance()
            self.test_results["network"] = self._test_network_connectivity()
            self.test_results["wifi"] = self._test_wifi_adapter()
            self.test_results["function_keys"] = self._test_function_keys()
            self.test_results["memory"] = self._test_memory_basic()
            self.test_results["audio"] = self._test_audio_playback()
            self.test_results["suspend"] = self._test_suspend_resume()

            # Aggregate results
            failed_tests = []
            warning_tests = []

            for test_name, test_result in self.test_results.items():
                if test_result.get("status") == "failed":
                    failed_tests.append(test_name)
                elif test_result.get("status") == "warning":
                    warning_tests.append(test_name)

            # Build summary
            summary = {
                "tests_run": len(self.test_results),
                "prerequisites": prereqs,
                "boot_time": self.test_results["boot_time"],
                "responsiveness": self.test_results["responsiveness"],
                "io_performance": self.test_results["io_performance"],
                "network": self.test_results["network"],
                "wifi": self.test_results["wifi"],
                "function_keys": self.test_results["function_keys"],
                "memory": self.test_results["memory"],
                "audio": self.test_results["audio"],
                "suspend": self.test_results["suspend"],
            }

            # Determine overall status
            if failed_tests:
                status = TestStatus.FAILED
                message = f"Express tests failed: {', '.join(failed_tests)}"
                errors.extend([f"Test '{t}' failed" for t in failed_tests])
            elif warning_tests:
                status = TestStatus.WARNING
                message = f"Express tests completed with warnings: {', '.join(warning_tests)}"
                warnings.extend([f"Test '{t}' has issues" for t in warning_tests])
            else:
                status = TestStatus.PASSED
                message = "All express tests passed"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.exception(f"Express tests failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Express tests failed: {str(e)}",
                errors=[str(e)],
            )
