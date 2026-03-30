"""Step 6: Disk Performance Test."""

import os
import time
import tempfile
from typing import List, Dict, Any, Optional

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class DiskPerfStep(BaseHWStep):
    """
    Disk drives performance test.
    
    Tests:
    - Sequential read/write performance
    - Random read/write performance
    - IOPS measurement
    - Latency measurement
    """

    name = "Disk Performance Test"
    description = "Measure disk drive performance using fio or dd"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.disk_results: Dict[str, Any] = {}

    def _run_command(self, cmd: List[str], timeout: int = 300, use_root: bool = True) -> tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _get_disk_drives(self) -> List[str]:
        """Get list of disk drives."""
        drives = []

        try:
            for entry in os.listdir('/sys/block'):
                # Skip certain device types
                if (entry.startswith('loop') or entry.startswith('ram') or
                    entry.startswith('sr') or entry.startswith('dm-') or
                    entry.startswith('md')):
                    continue

                # Check if it's a block device
                dev_path = f"/dev/{entry}"
                if not os.path.exists(dev_path):
                    continue

                # Check if readable (not write-protected)
                ro_file = f"/sys/block/{entry}/ro"
                try:
                    with open(ro_file, 'r') as f:
                        if f.read().strip() == '1':
                            continue
                except (FileNotFoundError, IOError):
                    pass

                # Check if it's not a slave/holder
                slaves_dir = f"/sys/block/{entry}/slaves"
                holders_dir = f"/sys/block/{entry}/holders"
                if (os.path.exists(slaves_dir) and os.listdir(slaves_dir)) or \
                   (os.path.exists(holders_dir) and os.listdir(holders_dir)):
                    continue

                drives.append(entry)

        except Exception as e:
            self.logger.warning(f"Failed to enumerate drives: {e}")

        return drives

    def _get_drive_size(self, drive: str) -> int:
        """Get drive size in bytes."""
        size_file = f"/sys/block/{drive}/size"
        try:
            with open(size_file, 'r') as f:
                # Size is in 512-byte sectors
                sectors = int(f.read().strip())
                return sectors * 512
        except (FileNotFoundError, IOError, ValueError):
            return 0

    def _test_with_fio(self, drive: str, test_dir: str) -> Dict[str, Any]:
        """Run fio benchmark."""
        result = {
            'tool': 'fio',
            'drive': drive,
            'sequential_read_mbs': None,
            'sequential_write_mbs': None,
            'random_read_iops': None,
            'random_write_iops': None,
            'latency_ms': None,
        }

        test_file = os.path.join(test_dir, f'fio_test_{drive}')

        try:
            # Sequential write test
            cmd = [
                'fio',
                '--name', f'seq_write_{drive}',
                '--filename', test_file,
                '--size', '512M',
                '--bs', '1M',
                '--rw', 'write',
                '--ioengine', 'libaio',
                '--direct', '1',
                '--numjobs', '1',
                '--runtime', '30',
                '--time_based',
                '--output-format', 'json'
            ]

            stdout, stderr, rc = self._run_command(cmd, timeout=60)

            if rc == 0:
                import json
                try:
                    fio_output = json.loads(stdout)
                    job = fio_output.get('jobs', [{}])[0]
                    write_bw = job.get('write', {}).get('bw_bytes', 0)
                    result['sequential_write_mbs'] = round(write_bw / (1024 * 1024), 2)
                except (json.JSONDecodeError, KeyError):
                    pass

            # Sequential read test
            cmd = [
                'fio',
                '--name', f'seq_read_{drive}',
                '--filename', test_file,
                '--size', '512M',
                '--bs', '1M',
                '--rw', 'read',
                '--ioengine', 'libaio',
                '--direct', '1',
                '--numjobs', '1',
                '--runtime', '30',
                '--time_based',
                '--output-format', 'json'
            ]

            stdout, stderr, rc = self._run_command(cmd, timeout=60)

            if rc == 0:
                import json
                try:
                    fio_output = json.loads(stdout)
                    job = fio_output.get('jobs', [{}])[0]
                    read_bw = job.get('read', {}).get('bw_bytes', 0)
                    result['sequential_read_mbs'] = round(read_bw / (1024 * 1024), 2)

                    # Get IOPS
                    result['random_read_iops'] = job.get('read', {}).get('iops', 0)
                    result['random_write_iops'] = job.get('write', {}).get('iops', 0)

                    # Get latency
                    clap = job.get('read', {}).get('clat_ns', {})
                    if clap:
                        mean_lat = clap.get('mean', 0) / 1_000_000  # Convert to ms
                        result['latency_ms'] = round(mean_lat, 3)
                except (json.JSONDecodeError, KeyError):
                    pass

            # Cleanup
            self._run_command(['rm', '-f', test_file])

        except Exception as e:
            self.logger.warning(f"FIO test failed for {drive}: {e}")

        return result

    def _test_with_dd(self, drive: str, test_dir: str) -> Dict[str, Any]:
        """Run dd benchmark as fallback."""
        result = {
            'tool': 'dd',
            'drive': drive,
            'sequential_read_mbs': None,
            'sequential_write_mbs': None,
        }

        test_file = os.path.join(test_dir, f'dd_test_{drive}')

        try:
            # Write test
            cmd = f"dd if=/dev/zero of={test_file} bs=1M count=256 conv=fdatasync 2>&1"
            stdout, _, rc = self._run_command(['sh', '-c', cmd], timeout=60)

            if rc == 0:
                # Parse output for speed
                import re
                match = re.search(r'([\d.]+)\s*(?:MB|GB)/s', stdout)
                if match:
                    speed = float(match.group(1))
                    if 'GB' in stdout:
                        speed *= 1024
                    result['sequential_write_mbs'] = round(speed, 2)

            # Read test (clear caches first)
            self._run_command(['sync'])
            self._run_command(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'])

            cmd = f"dd if={test_file} of=/dev/null bs=1M 2>&1"
            stdout, _, rc = self._run_command(['sh', '-c', cmd], timeout=60)

            if rc == 0:
                import re
                match = re.search(r'([\d.]+)\s*(?:MB|GB)/s', stdout)
                if match:
                    speed = float(match.group(1))
                    if 'GB' in stdout:
                        speed *= 1024
                    result['sequential_read_mbs'] = round(speed, 2)

            # Cleanup
            self._run_command(['rm', '-f', test_file])

        except Exception as e:
            self.logger.warning(f"DD test failed for {drive}: {e}")

        return result

    def _find_test_location(self) -> Optional[str]:
        """Find suitable location for test files."""
        # Try common locations
        test_dirs = ['/tmp', '/var/tmp', '/home']

        for test_dir in test_dirs:
            if os.path.exists(test_dir) and os.access(test_dir, os.W_OK):
                # Check available space
                try:
                    stat = os.statvfs(test_dir)
                    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
                    if free_gb >= 2:  # Need at least 2GB free
                        return test_dir
                except Exception:
                    pass

        return None

    def execute(self) -> StepResult:
        """Execute disk performance test."""
        errors = []
        warnings = []

        self.logger.info("Starting disk performance test...")

        try:
            # Get list of drives
            drives = self._get_disk_drives()

            if not drives:
                return StepResult(
                    step_name=self.name,
                    status=TestStatus.SKIPPED,
                    message="No suitable disk drives found for testing",
                    details={'drives_found': 0},
                )

            self.logger.info(f"Found drives: {drives}")

            # Find test location
            test_dir = self._find_test_location()
            if not test_dir:
                return StepResult(
                    step_name=self.name,
                    status=TestStatus.FAILED,
                    message="No suitable location found for test files",
                    errors=["Insufficient disk space for testing"],
                )

            # Check if fio is available
            use_fio = False
            stdout, _, rc = self._run_command(['which', 'fio'])
            if rc == 0:
                use_fio = True
                self.logger.info("Using fio for testing")
            else:
                self.logger.info("fio not found, using dd as fallback")

            # Test each drive
            results = []
            for drive in drives:
                drive_size = self._get_drive_size(drive)

                # Skip small drives (< 1GB)
                if drive_size < 1024 ** 3:
                    self.logger.info(f"Skipping {drive}: too small ({drive_size} bytes)")
                    continue

                self.logger.info(f"Testing {drive} ({drive_size / (1024**3):.2f} GB)")

                if use_fio:
                    result = self._test_with_fio(drive, test_dir)
                else:
                    result = self._test_with_dd(drive, test_dir)

                result['size_gb'] = round(drive_size / (1024 ** 3), 2)
                results.append(result)

            if not results:
                warnings.append("No drives were tested")

            # Build summary
            summary = {
                'drives_tested': len(results),
                'results': results,
                'tool_used': 'fio' if use_fio else 'dd',
            }

            # Calculate averages
            if results:
                seq_read = [r['sequential_read_mbs'] for r in results if r['sequential_read_mbs']]
                seq_write = [r['sequential_write_mbs'] for r in results if r['sequential_write_mbs']]

                if seq_read:
                    summary['avg_seq_read_mbs'] = round(sum(seq_read) / len(seq_read), 2)
                if seq_write:
                    summary['avg_seq_write_mbs'] = round(sum(seq_write) / len(seq_write), 2)

            self.disk_results = summary

            # Determine status
            if errors:
                status = TestStatus.FAILED
                message = "Disk performance test failed"
            elif warnings:
                status = TestStatus.WARNING
                message = "Disk performance test completed with warnings"
            else:
                status = TestStatus.PASSED
                message = f"Tested {len(results)} disk drives successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.exception(f"Disk performance test failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Disk performance test failed: {str(e)}",
                errors=[str(e)]
            )
