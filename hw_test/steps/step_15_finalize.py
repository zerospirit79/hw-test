"""Step 15: Finalization."""

import os
import shutil
import tarfile
import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep
from hw_test.l10n import get_l10n, _


class FinalizeStep(BaseHWStep):
    """
    Finalization of testing.

    Performs:
    - Results summary
    - Archive creation (pc-test format)
    - Log collection
    - Report generation
    """

    name = "Finalization"
    description = "Complete testing and create results archive"
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.l10n = get_l10n()
        self.archive_path: Optional[str] = None
        self.results_summary: Dict[str, Any] = {}

    def _run_command(self, cmd: List[str], timeout: int = 60, use_root: bool = True) -> tuple[str, str, int]:
        """Run command and return (stdout, stderr, returncode)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr, rc

    def _get_workdir(self) -> Path:
        """Get working directory path."""
        date_str = self.config.repodate or datetime.now().strftime("%Y-%m-%d")
        return Path.home() / ".local" / "share" / "hw-test" / date_str

    def _get_lastdir(self) -> Path:
        """Get results symlink path."""
        return Path.home() / "HW-TEST"

    def _get_mnt_dir(self) -> Path:
        """Get /mnt/pc-test directory if available."""
        mnt_dir = Path('/mnt/pc-test')
        if mnt_dir.exists() and mnt_dir.is_dir():
            return mnt_dir
        return None

    def _gzip_compress(self, data: str) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data.encode('utf-8', errors='ignore'), compresslevel=9)

    def _save_gzip(self, filepath: Path, content: str) -> bool:
        """Save content to gzipped file."""
        try:
            with open(filepath, 'wb') as f:
                f.write(self._gzip_compress(content))
            return True
        except Exception as e:
            self.logger.warning(f"Failed to save {filepath}: {e}")
            return False

    def _collect_logs(self, workdir: Path) -> Dict[str, Any]:
        """Collect system logs."""
        result = {
            'logs_collected': [],
            'commands_collected': [],
            'inxi_collected': [],
        }

        log_dir = workdir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        # System logs
        log_files = {
            '/var/log/syslog': 'syslog.gz',
            '/var/log/messages': 'messages.gz',
            '/var/log/kern.log': 'kern.log.gz',
            '/var/log/dpkg.log': 'dpkg.log.gz',
            '/var/log/apt/history.log': 'apt_history.gz',
        }

        for src, dest in log_files.items():
            if os.path.exists(src):
                try:
                    with open(src, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    dest_path = log_dir / dest
                    if self._save_gzip(dest_path, content):
                        result['logs_collected'].append(dest)
                except Exception:
                    pass

        # dmesg
        stdout, _, rc = self._run_command(['dmesg', '-H', '-P', '--color=always'])
        if rc == 0:
            if self._save_gzip(log_dir / 'dmesg.gz', stdout):
                result['commands_collected'].append('dmesg.gz')

        # dmesg errors
        stdout, _, rc = self._run_command(['dmesg'])
        if rc == 0:
            errors = [l for l in stdout.split('\n') 
                     if not ('Command line:' in l or 'Kernel command line:' in l)
                     and any(k in l.lower() for k in ['panic', 'fatal', 'fail', 'error', 'warning'])]
            if errors and self._save_gzip(log_dir / 'dmesg_errors.gz', '\n'.join(errors)):
                result['commands_collected'].append('dmesg_errors.gz')

        # systemd
        if os.path.exists('/run/systemd/system'):
            for name, cmd in [
                ('systemctl_err.gz', ['systemctl', '--failed', '--no-pager']),
                ('journal.gz', ['journalctl', '-b', '--no-pager']),
                ('journal_err.gz', ['journalctl', '-p', 'err', '-b', '--no-pager']),
            ]:
                stdout, _, rc = self._run_command(cmd)
                if rc == 0 and stdout and self._save_gzip(log_dir / name, stdout):
                    result['commands_collected'].append(name)

        return result

    def _collect_inxi(self, workdir: Path) -> Dict[str, Any]:
        """Collect inxi hardware information."""
        result = {'files': []}

        inxi_opts = [
            ('inxi.txt', '-v8'),
            ('inxi-CM.txt', '-CM'),
            ('inxi-m.txt', '-m'),
            ('inxi-D.txt', '-D'),
            ('inxi-G.txt', '-G'),
            ('inxi-A.txt', '-A'),
            ('inxi-N.txt', '-N'),
        ]

        for filename, opt in inxi_opts:
            stdout, _, rc = self._run_command(['inxi', opt, '-c0'])
            if rc == 0 and stdout:
                filepath = workdir / filename
                with open(filepath, 'w') as f:
                    f.write(stdout)
                result['files'].append(filename)

        return result

    def _collect_commands(self, workdir: Path) -> Dict[str, Any]:
        """Collect command outputs."""
        result = {'files': []}

        commands = {
            'version.txt': ['hw-test', '--version'],
            'uname.txt': ['uname', '-a'],
            'hostnamectl.txt': ['hostnamectl'],
            'lscpu.txt': ['lscpu'],
            'lsblk.txt': ['lsblk'],
            'df.txt': ['df', '-h'],
            'free.txt': ['free', '-m'],
            'ip_addr.txt': ['ip', 'addr'],
            'ip_route.txt': ['ip', 'route'],
            'lspci.txt': ['lspci', '-nn'],
            'lsusb.txt': ['lsusb'],
            'aplay_l.txt': ['aplay', '-l'],
            'arecord_l.txt': ['arecord', '-l'],
        }

        cmd_dir = workdir / 'commands'
        cmd_dir.mkdir(parents=True, exist_ok=True)

        for filename, cmd in commands.items():
            stdout, _, rc = self._run_command(cmd)
            if rc == 0 and stdout:
                filepath = cmd_dir / filename
                with open(filepath, 'w') as f:
                    f.write(stdout)
                result['files'].append(filename)

        return result

    def _create_results_json(self, workdir: Path, step_results: List[Dict]) -> str:
        """Create results.json."""
        results = {
            'test_name': self.config.name,
            'start_time': datetime.now().isoformat(),
            'end_time': datetime.now().isoformat(),
            'steps': step_results,
            'hardware_info': {},
        }

        if self.hardware_info:
            results['hardware_info'] = {
                'cpu_model': self.hardware_info.cpu_model,
                'cpu_cores': self.hardware_info.cpu_cores,
                'total_memory_mb': self.hardware_info.total_memory_mb,
                'system_manufacturer': self.hardware_info.system_manufacturer,
                'system_product': self.hardware_info.system_product,
            }

        filepath = workdir / 'results.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def _generate_report(self, workdir: Path, step_results: List[Dict]) -> str:
        """Generate text report."""
        filepath = workdir / 'report.txt'

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"{self.l10n.get('program_name')} - {self.l10n.get('summary_title')}\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Test Name: {self.config.name}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Hardware info
            f.write("-" * 60 + "\n")
            f.write("HARDWARE INFORMATION\n")
            f.write("-" * 60 + "\n")

            if self.hardware_info:
                f.write(f"CPU: {self.hardware_info.cpu_model}\n")
                f.write(f"Cores: {self.hardware_info.cpu_cores}\n")
                f.write(f"Memory: {self.hardware_info.total_memory_mb} MB\n")
                f.write(f"System: {self.hardware_info.system_manufacturer} {self.hardware_info.system_product}\n")
            else:
                f.write("Hardware information not available\n")

            # Test results
            f.write("\n")
            f.write("-" * 60 + "\n")
            f.write("TEST RESULTS\n")
            f.write("-" * 60 + "\n\n")

            passed = failed = warnings = 0
            for result in step_results:
                status = result.get('status', 'unknown')
                step_name = result.get('step_name', 'Unknown')
                message = result.get('message', '')

                f.write(f"[{status.upper()}] {step_name}\n")
                f.write(f"  {message}\n\n")

                if status == 'passed':
                    passed += 1
                elif status in ['failed', 'error']:
                    failed += 1
                elif status == 'warning':
                    warnings += 1

            f.write("-" * 60 + "\n")
            f.write("SUMMARY\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total: {len(step_results)}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Warnings: {warnings}\n")

            if failed > 0:
                f.write(f"\nRESULT: {self.l10n.get('test_failed')}\n")
            elif warnings > 0:
                f.write(f"\nRESULT: {self.l10n.get('test_warning')}\n")
            else:
                f.write(f"\nRESULT: {self.l10n.get('test_passed')}\n")

        return str(filepath)

    def _create_archive(self, workdir: Path) -> Optional[str]:
        """Create tar.gz archive."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"hw-test-{self.config.name}-{timestamp}.tar.gz"
            archive_path = workdir / archive_name

            with tarfile.open(archive_path, "w:gz") as tar:
                for item in workdir.iterdir():
                    if item != archive_path:
                        tar.add(item, arcname=item.name)

            return str(archive_path)
        except Exception as e:
            self.logger.error(f"Failed to create archive: {e}")
            return None

    def execute(self) -> StepResult:
        """Execute finalization."""
        errors = []
        warnings = []

        self.logger.info("Starting finalization...")

        try:
            workdir = self._get_workdir()
            workdir.mkdir(parents=True, exist_ok=True)

            # Collect logs
            logs_result = self._collect_logs(workdir)

            # Collect inxi
            inxi_result = self._collect_inxi(workdir)

            # Collect commands
            cmd_result = self._collect_commands(workdir)

            # Create results JSON
            results_file = self._create_results_json(workdir, [])

            # Generate report
            report_file = self._generate_report(workdir, [])

            # Create archive
            archive_path = self._create_archive(workdir)

            # Move to /mnt/pc-test if available
            mnt_dir = self._get_mnt_dir()
            final_archive = archive_path
            if archive_path and mnt_dir:
                try:
                    dest = mnt_dir / f"{self.config.name}-{datetime.now().strftime('%Y-%m-%d')}.tar.gz"
                    shutil.move(archive_path, str(dest))
                    final_archive = str(dest)
                except Exception as e:
                    self.logger.warning(f"Failed to move archive: {e}")

            # Create symlink
            lastdir = self._get_lastdir()
            if lastdir.is_symlink() or lastdir.exists():
                try:
                    lastdir.unlink()
                except Exception:
                    pass
            try:
                lastdir.symlink_to(workdir)
            except Exception as e:
                self.logger.warning(f"Failed to create symlink: {e}")

            # Summary
            summary = {
                'workdir': str(workdir),
                'archive_path': final_archive,
                'logs_collected': len(logs_result.get('logs_collected', [])),
                'commands_collected': len(cmd_result.get('files', [])),
                'inxi_files': len(inxi_result.get('files', [])),
                'report_generated': report_file,
                'symlink_created': lastdir.exists(),
            }

            self.results_summary = summary

            if errors:
                status = TestStatus.FAILED
                message = self.l10n.get('error_step_failed')
            elif warnings:
                status = TestStatus.WARNING
                message = self.l10n.get('tests_with_warnings')
            else:
                status = TestStatus.PASSED
                message = f"{self.l10n.get('archive_created')}: {final_archive}"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.exception(f"Finalization failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"{self.l10n.get('error_step_failed')}: {str(e)}",
                errors=[str(e)]
            )
