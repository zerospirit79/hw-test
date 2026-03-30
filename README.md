# HW-Test

Hardware compatibility testing tool for ALT Linux (based on Basalt SPo methodology).

## Features

- **Hardware Detection**: Automatic detection of CPU, memory, storage, network, GPU, audio, USB devices, webcams, fingerprint readers, and more
- **Express Tests**: Quick verification of boot time, system responsiveness, I/O performance, and network connectivity
- **System Check**: OS version verification, package manager health, available updates, disk space monitoring
- **Performance Benchmarks**: CPU, memory, disk I/O, and context switching performance
- **Firmware Check**: BIOS/UEFI version detection, Secure Boot status, firmware updates via fwupd
- **Log Collection**: Comprehensive log gathering and archiving for troubleshooting
- **Reboot Support**: Automatic test continuation after system reboot

## Installation

### From source (development mode)

```bash
cd /workspace/hw_test
pip install -e .
```

### Build distribution

```bash
pip install build
python -m build
```

This creates source and wheel distributions in the `dist/` directory.

## Usage

### Basic usage

```bash
# Run all tests (will prompt for root password)
hw-test --start

# Run in batch mode (no interactive prompts)
hw-test --start --batch

# Run specific steps only
hw-test --start --steps hardware_detection,express_test

# Skip certain steps
hw-test --start --skip performance,firmware_check

# Set custom test name
hw-test --start --name "Workstation-001"

# Verbose output
hw-test --start -v

# Custom output directory
hw-test --start --output-dir /tmp/hw-results
```

### List available steps

```bash
hw-test --list-steps
```

### Show version

```bash
hw-test --version
```

## Authentication

HW-Test uses `su -c` for privilege escalation instead of `sudo`. When you start a test:

1. You will be prompted to enter the root password
2. The password is verified and cached for the duration of the test
3. All privileged commands are executed via `su -c`

This approach:
- Does not require sudo configuration
- Works in environments where sudo is not available
- Provides secure password handling with verification

## Test Continuation After Reboot

If a test step requires a reboot (e.g., after firmware update):

1. The test state is saved to `/var/lib/hw-test/test_state.json`
2. The system reboots
3. After reboot, run the same command: `hw-test --start --name <test_name>`
4. The test automatically resumes from where it left off

## Available Test Steps

| Step | Description | Requires Root | Corresponds to bash pc-test |
|------|-------------|---------------|----------------------------|
| `prepare` | System preparation (security checks, distro detection) | Yes | `prepare.sh` |
| `upgrade` | System and kernel update | Yes | `upgrade.sh` |
| `hardware_detection` | Detect all hardware components | Yes | `detect.sh` |
| `config` | Define test plan and configuration | No | `config.sh` |
| `firmware_check` | BIOS/UEFI and firmware updates | Yes | `fwupd.sh` |
| `syslogs` | Check system logs for errors | Yes | `syslogs.sh` |
| `express_test` | Quick functionality tests | No | `express.sh` |
| `cpupower` | CPU frequency scaling test | Yes | `cpupower.sh` |
| `diskperf` | Disk I/O performance test | Yes | `diskperf.sh` |
| `glmark` | 3D graphics performance test | No | `glmark.sh` |
| `system_check` | OS and package manager checks | Yes | - |
| `performance` | Performance benchmarks | No | - |
| `reboot_and_continue` | Reboot and continue testing | Yes | - |
| `log_collection` | Collect logs and create archive | Yes | `collect.sh` |
| `finalize` | Complete testing and create results | Yes | `finalize.sh` |

**Note:** Package dependencies are specified in the RPM spec file. No runtime package installation is performed.

## Architecture

```
hw_test/
├── __init__.py          # Package initialization, version
├── types.py             # Type definitions (TestConfig, HardwareInfo, StepResult)
├── auth.py              # Root authentication via su -c
├── state.py             # Test state management for reboot continuation
├── cli.py               # Command-line interface
└── steps/
    ├── __init__.py      # Step registry and exports
    ├── base.py          # BaseHWStep abstract class
    ├── step_01_hardware_detection.py
    ├── step_02_express_test.py
    ├── step_03_system_check.py
    ├── step_04_performance.py
    ├── step_05_firmware_check.py
    ├── step_06_log_collection.py
    └── step_07_reboot.py
```

### Adding Custom Steps

1. Create a new file in `hw_test/steps/` (e.g., `step_08_custom.py`)
2. Inherit from `BaseHWStep`:

```python
from hw_test.steps.base import BaseHWStep
from hw_test.types import StepResult, TestStatus

class CustomStep(BaseHWStep):
    name = "Custom Test"
    description = "My custom test step"
    requires_root = False

    def execute(self) -> StepResult:
        # Your test logic here
        return StepResult(
            step_name=self.name,
            status=TestStatus.PASSED,
            message="Custom test completed"
        )
```

3. Register in `hw_test/steps/__init__.py`

## Configuration

Default paths:
- Data directory: `/var/lib/hw-test`
- Log directory: `/var/lib/hw-test/logs`
- Config directory: `/etc/hw-test`
- State file: `/var/lib/hw-test/test_state.json`

Environment variables:
- `HWTEST_DATA_DIR`: Override data directory
- `HWTEST_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

## Output

Results are displayed in the console and logged. The `log_collection` step creates a compressed archive containing:
- System logs (syslog, messages, kern.log, etc.)
- Command outputs (dmesg, lspci, lsusb, etc.)
- Hardware information from sysfs
- Summary JSON file

Archive naming: `hw-test_<name>_<timestamp>.tar.gz`

## Requirements

- Python 3.8+
- psutil
- py-cpuinfo
- packaging

Optional dependencies (for full functionality):
- dmidecode
- fwupd
- ipmitool
- v4l2-ctl

## License

GPL-3.0

## Authors

Based on pc-test by Basalt SPo Team.
Rewritten in Python as hw-test.
