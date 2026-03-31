"""System utilities for hw-test.

Provides system-level utilities ported from pc-test bash scripts:
- Package checking (RPM, apt)
- Binary detection
- Network connectivity check
- PC type detection
- Disk drive detection
- Network interface detection
- Desktop environment detection
- Command logging/spawn
"""

from __future__ import annotations

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

logger = logging.getLogger("hw_test.system_utils")


# ==================== Package Management ====================


def is_pkg_installed(package_name: str) -> bool:
    """Check if specified package is installed (RPM)."""
    try:
        result = subprocess.run(
            ["rpm", "-q", "--", package_name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_pkg_available(package_name: str) -> bool:
    """Check if specified package is available to install (apt-cache)."""
    try:
        result = subprocess.run(
            ["apt-cache", "show", "--", package_name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def has_binary(binary_name: str) -> bool:
    """Check if specified binary is in PATH."""
    return (
        subprocess.run(
            ["which", "--", binary_name],
            capture_output=True,
        ).returncode
        == 0
    )


# ==================== Network ====================


def check_internet(ping_server: str = "ya.ru") -> bool:
    """Check Internet connection by pinging specified server."""
    try:
        result = subprocess.run(
            ["ping", "-c4", "-W10", "--", ping_server],
            capture_output=True,
            text=True,
        )
        return ", 0% packet loss," in result.stdout
    except Exception:
        return False


def get_network_interfaces() -> List[str]:
    """Get list of network interfaces (excluding loopback)."""
    ifaces = []
    try:
        result = subprocess.run(
            ["ip", "-o", "link", "show"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.strip():
                    parts = line.split(": ")
                    if len(parts) >= 2:
                        iface_name = parts[1].split("@")[0]
                        if iface_name != "lo":
                            ifaces.append(iface_name)
    except Exception:
        pass
    return ifaces


# ==================== PC Type Detection ====================


PC_TYPE_MAP = {
    "3": "Personal",
    "4": "Personal",
    "5": "Personal",
    "6": "Personal",
    "7": "Personal",
    "8": "Notebook",
    "9": "Notebook",
    "10": "Notebook",
    "14": "Notebook",
    "15": "Personal",
    "16": "Personal",
    "17": "Server",
    "22": "Server",
    "23": "Server",
    "24": "Personal",
    "28": "Server",
    "29": "Server",
    "30": "Tablet",
    "31": "Convertible",
    "36": "Personal",
}


def detect_pc_type() -> str:
    """Detect PC type from DMI/SMBIOS chassis type."""
    chassis_type_files = [
        "/sys/class/dmi/id/chassis_type",
        "/sys/devices/virtual/dmi/id/chassis_type",
    ]

    for chassis_file in chassis_type_files:
        try:
            if os.path.exists(chassis_file):
                with open(chassis_file, "r") as f:
                    chassis_type = f.read().strip()
                    return PC_TYPE_MAP.get(chassis_type, "Computer")
        except (IOError, PermissionError):
            continue

    # Fallback: check if running in VM
    try:
        result = subprocess.run(
            ["lscpu"],
            capture_output=True,
            text=True,
        )
        if "Hypervisor vendor:" in result.stdout:
            return "Virtual"
    except Exception:
        pass

    return "Computer"


def get_product_name() -> str:
    """Get product name from DMI/SMBIOS."""
    name_files = [
        "/sys/class/dmi/id/product_name",
        "/sys/class/dmi/id/board_name",
    ]

    for name_file in name_files:
        try:
            if os.path.exists(name_file):
                with open(name_file, "r") as f:
                    name = f.read().strip()
                    # Clean up name
                    name = name.replace("(", "").replace(")", "").split(",")[0]
                    if name:
                        return name
        except (IOError, PermissionError):
            continue

    return ""


# ==================== Disk Detection ====================


def get_disk_drives() -> List[str]:
    """Get list of block disk drives (excluding loops, RAM disks, optical)."""
    drives = []
    sys_block = Path("/sys/block")

    if not sys_block.exists():
        return drives

    exclude_prefixes = ("loop", "ram", "sr", "dm-", "md-")

    for block_dir in sys_block.iterdir():
        if not block_dir.is_dir():
            continue

        block_name = block_dir.name

        # Skip excluded devices
        if any(block_name.startswith(p) for p in exclude_prefixes):
            continue

        # Check if it's a holder/slave (partition, RAID member)
        holders_dir = block_dir / "holders"
        slaves_dir = block_dir / "slaves"

        if holders_dir.exists() and any(holders_dir.iterdir()):
            continue

        if slaves_dir.exists() and any(slaves_dir.iterdir()):
            continue

        # Check if writable
        ro_file = block_dir / "ro"
        if ro_file.exists():
            try:
                with open(ro_file, "r") as f:
                    if f.read().strip() == "1":
                        continue
            except (IOError, PermissionError):
                pass

        # Check if block device exists
        dev_path = Path(f"/dev/{block_name}")
        if dev_path.is_block_device():
            drives.append(block_name)

    # Also check MD RAID devices
    for block_dir in sys_block.iterdir():
        if block_dir.name.startswith("md"):
            dev_path = Path(f"/dev/{block_dir.name}")
            if dev_path.is_block_device():
                drives.append(block_dir.name)

    return drives


# ==================== Desktop Environment Detection ====================


def detect_desktop_environments() -> Dict[str, bool]:
    """Detect installed desktop environments."""
    return {
        "gnome": is_pkg_installed("gnome-shell"),
        "kde": (
            is_pkg_installed("kde")
            or is_pkg_installed("kde5")
            or is_pkg_installed("plasma6-plasma5support-common")
        ),
        "xfce": (is_pkg_installed("xfce4-minimal") or is_pkg_installed("xfce4-default")),
        "mate": (
            is_pkg_installed("mate-minimal")
            or is_pkg_installed("mate-default")
            or is_pkg_installed("mate-window-manager")
        ),
    }


def get_current_desktop() -> Optional[str]:
    """Get current desktop environment from XDG_CURRENT_DESKTOP."""
    xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")

    desktop_map = {
        "GNOME": "gnome",
        "KDE": "kde",
        "XFCE": "xfce",
        "MATE": "mate",
    }

    for key, value in desktop_map.items():
        if key in xdg_desktop.upper():
            return value

    return None


def get_terminal_for_desktop(desktop: Optional[str] = None) -> Optional[List[str]]:
    """Get terminal emulator command for specified desktop."""
    if desktop is None:
        desktop = get_current_desktop()

    terminal_commands = {
        "gnome": ["kgx"],
        "kde": ["konsole"],
        "mate": ["mate-terminal"],
        "xfce": ["xfce4-terminal"],
    }

    if desktop and desktop in terminal_commands:
        for cmd in terminal_commands[desktop]:
            if has_binary(cmd):
                return [cmd]

    return None


# ==================== Command Logging/Spawn ====================


class CommandLogger:
    """Logs and executes commands with timestamps."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.logger = logging.getLogger("hw_test.commands")

    def _cmd_title(self, cmd: List[str], is_comment: bool = False) -> str:
        """Create command title for logging."""
        import datetime

        timestamp = datetime.datetime.now().strftime("%T")
        uid = os.geteuid()

        if is_comment or (cmd and cmd[0] == ":"):
            prefix = ":" if uid == 0 else ":"
            cmd_text = " ".join(cmd[1:]) if cmd else ""
            return f"[{timestamp}] {prefix} {cmd_text}"
        else:
            prefix = "#" if uid == 0 else "$"
            cmd_text = " ".join(cmd)
            return f"[{timestamp}] {prefix} {cmd_text}"

    def spawn(self, cmd: List[str], timeout: int = 300) -> Tuple[str, str, int]:
        """Run command with logging."""
        # Log command
        title = self._cmd_title(cmd)
        self.logger.info(title)

        if self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(title + "\n")
            except Exception:
                pass

        # Execute command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Log output
            if result.stdout:
                self.logger.debug(f"stdout: {result.stdout[:500]}")
            if result.stderr:
                self.logger.debug(f"stderr: {result.stderr[:500]}")

            if self.log_file:
                try:
                    with open(self.log_file, "a") as f:
                        if result.stdout:
                            f.write(result.stdout)
                        if result.stderr:
                            f.write(result.stderr)
                except Exception:
                    pass

            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(cmd)}")
            return "", "Timeout", -1
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return "", str(e), -1

    def spawn2(self, cmd: List[str], timeout: int = 300) -> Tuple[str, str, int]:
        """Run command with logging (for commands with stderr output only)."""
        title = self._cmd_title(cmd)
        self.logger.info(title)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), -1


# ==================== System Information ====================


def get_system_info() -> Dict[str, Any]:
    """Gather comprehensive system information."""
    info: Dict[str, Any] = {
        "pc_type": detect_pc_type(),
        "product_name": get_product_name(),
        "drives": get_disk_drives(),
        "interfaces": get_network_interfaces(),
        "desktop_environments": detect_desktop_environments(),
        "current_desktop": get_current_desktop(),
        "has_xorg": has_binary("Xorg") or is_pkg_installed("xorg-server"),
        "has_systemd": os.path.exists("/run/systemd/system"),
    }

    # Check for ALT Linux SP (special certification)
    try:
        result = subprocess.run(
            ["rpm", "-q", "--", "altlinux-release"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            info["distro"] = "ALT Linux"
            info["have_altsp"] = "cert" in result.stdout.lower() or is_pkg_installed(
                "altlinux-release-cert"
            )
    except Exception:
        info["distro"] = "Unknown"
        info["have_altsp"] = False

    return info
