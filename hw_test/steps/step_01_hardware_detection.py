"""Step 1: Hardware Detection."""

from __future__ import annotations

import subprocess
import re
from typing import List, Dict, Any, Optional, Tuple

from hw_test.types import StepResult, TestStatus, HardwareInfo, TestConfig
from hw_test.steps.base import BaseHWStep


class HardwareDetectionStep(BaseHWStep):
    """Detect and catalog all hardware components."""

    name = "Hardware Detection"
    description = (
        "Detect CPU, memory, storage, network, GPU, audio, USB devices, and other hardware"
    )
    requires_root = True

    def __init__(self, config: TestConfig, hardware_info: Optional[HardwareInfo] = None):
        super().__init__(config, hardware_info)
        self.detected_hardware = HardwareInfo()

    def _run_command(
        self, cmd: List[str], timeout: int = 30, use_root: bool = True
    ) -> Tuple[str, str]:
        """Run a command and return (stdout, stderr)."""
        stdout, stderr, rc = self.run_command(cmd, timeout=timeout, use_root=use_root)
        return stdout, stderr

    def _detect_cpu(self) -> None:
        """Detect CPU information."""
        try:
            import cpuinfo

            info = cpuinfo.get_cpu_info()
            self.detected_hardware.cpu_model = info.get("brand_raw", "Unknown")
            self.detected_hardware.cpu_cores = info.get("count", 0)

            # Get frequency
            stdout, _ = self._run_command(["lscpu"])
            for line in stdout.split("\n"):
                if "CPU MHz" in line or "MHz" in line:
                    match = re.search(r"([\d.]+)", line)
                    if match:
                        self.detected_hardware.cpu_freq_mhz = float(match.group(1))
                        break

            # Threads
            stdout, _ = self._run_command(["nproc", "--all"])
            if stdout.strip().isdigit():
                self.detected_hardware.cpu_threads = int(stdout.strip())

        except Exception as e:
            self.logger.warning(f"CPU detection failed: {e}")
            self.detected_hardware.cpu_model = "Unknown"

    def _detect_memory(self) -> None:
        """Detect memory information."""
        try:
            import psutil

            mem = psutil.virtual_memory()
            self.detected_hardware.total_memory_mb = int(mem.total / (1024 * 1024))
            self.detected_hardware.available_memory_mb = int(mem.available / (1024 * 1024))
        except Exception as e:
            self.logger.warning(f"Memory detection failed: {e}")

    def _detect_disks(self) -> None:
        """Detect disk information."""
        try:
            import psutil

            disks = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append(
                        {
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype,
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent_used": usage.percent,
                        }
                    )
                except PermissionError:
                    continue
            self.detected_hardware.disk_info = disks
        except Exception as e:
            self.logger.warning(f"Disk detection failed: {e}")

    def _detect_network(self) -> None:
        """Detect network interfaces."""
        try:
            import psutil

            interfaces = []
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for iface_name, addrs_list in addrs.items():
                if iface_name.startswith("lo"):
                    continue

                iface_info = {
                    "name": iface_name,
                    "is_up": stats.get(iface_name, {}).isup if iface_name in stats else False,
                    "speed": stats.get(iface_name, {}).speed if iface_name in stats else 0,
                    "addresses": [],
                }

                for addr in addrs_list:
                    addr_info = {"family": str(addr.family), "address": addr.address}
                    if addr.netmask:
                        addr_info["netmask"] = addr.netmask
                    iface_info["addresses"].append(addr_info)

                interfaces.append(iface_info)

            self.detected_hardware.network_interfaces = interfaces
        except Exception as e:
            self.logger.warning(f"Network detection failed: {e}")

    def _detect_gpu(self) -> None:
        """Detect GPU information."""
        gpus = []

        # Try lspci for VGA controllers
        stdout, _ = self._run_command(["lspci", "-nn"])
        for line in stdout.split("\n"):
            if "VGA" in line or "3D" in line or "Display" in line:
                gpus.append({"description": line.strip(), "source": "lspci"})

        # Try nvidia-smi if available
        stdout, _ = self._run_command(["nvidia-smi", "-L"])
        if stdout:
            for line in stdout.split("\n"):
                if line.strip():
                    gpus.append({"description": line.strip(), "source": "nvidia-smi"})

        self.detected_hardware.gpu_info = gpus

    def _detect_audio(self) -> None:
        """Detect audio devices."""
        audio = []
        stdout, _ = self._run_command(["aplay", "-l"])

        if stdout:
            current_card = {}
            for line in stdout.split("\n"):
                if line.startswith("card "):
                    if current_card:
                        audio.append(current_card)
                    match = re.match(r"card (\d+): (.+)", line)
                    if match:
                        current_card = {
                            "card": match.group(1),
                            "name": match.group(2),
                            "devices": [],
                        }
                elif line.strip() and current_card:
                    current_card.setdefault("devices", []).append(line.strip())

            if current_card:
                audio.append(current_card)

        self.detected_hardware.audio_devices = audio

    def _detect_usb(self) -> None:
        """Detect USB devices."""
        usb = []
        stdout, _ = self._run_command(["lsusb"])

        for line in stdout.split("\n"):
            if line.strip() and "Bus" in line:
                usb.append({"description": line.strip()})

        self.detected_hardware.usb_devices = usb

    def _detect_system_info(self) -> None:
        """Detect system information from DMI/SMBIOS."""
        # Manufacturer and product
        for file_path, attr in [
            ("/sys/class/dmi/id/sys_vendor", "system_manufacturer"),
            ("/sys/class/dmi/id/product_name", "system_product"),
            ("/sys/class/dmi/id/bios_vendor", "bios_vendor"),
            ("/sys/class/dmi/id/bios_version", "bios_version"),
        ]:
            try:
                with open(file_path, "r") as f:
                    value = f.read().strip()
                    setattr(self.detected_hardware, attr, value)
            except (FileNotFoundError, PermissionError):
                pass

        # NUMA nodes
        try:
            numa_nodes = 0
            for entry in subprocess.run(
                ["ls", "-d", "/sys/devices/system/node/node*"], capture_output=True, text=True
            ).stdout.split():
                if "node" in entry:
                    numa_nodes += 1
            self.detected_hardware.numa_nodes = max(1, numa_nodes)
        except Exception:
            self.detected_hardware.numa_nodes = 1

        # IPMI detection - use root
        stdout, _ = self._run_command(["ipmitool", "mc", "info"], use_root=True)
        self.detected_hardware.ipmi_detected = "Manufacturer" in stdout

    def _detect_webcams(self) -> None:
        """Detect webcams."""
        webcams = []
        stdout, _ = self._run_command(["v4l2-ctl", "--list-devices"])

        if stdout:
            current_device = {}
            for line in stdout.split("\n"):
                if line.strip() and not line.startswith(" "):
                    if current_device:
                        webcams.append(current_device)
                    current_device = {"name": line.strip(), "paths": []}
                elif line.strip():
                    current_device.setdefault("paths", []).append(line.strip())

            if current_device:
                webcams.append(current_device)

        # Also check via lsusb
        if not webcams:
            stdout, _ = self._run_command(["lsusb"])
            for line in stdout.split("\n"):
                if "Camera" in line or "Webcam" in line:
                    webcams.append({"name": line.strip(), "source": "lsusb"})

        self.detected_hardware.webcams = webcams

    def _detect_fingerprint_readers(self) -> None:
        """Detect fingerprint readers."""
        readers = []
        stdout, _ = self._run_command(["lsusb"])

        for line in stdout.split("\n"):
            if any(
                keyword in line.lower()
                for keyword in ["fingerprint", "goodix", "validity", "synaptics"]
            ):
                readers.append({"description": line.strip()})

        self.detected_hardware.fingerprint_readers = readers

    def _detect_bluetooth(self) -> None:
        """Detect Bluetooth adapters."""
        bluetooth_adapters = []

        # Check using bluetoothctl
        stdout, _, rc = self._run_command(["bluetoothctl", "list"])
        if rc == 0 and "Controller" in stdout:
            for line in stdout.split("\n"):
                if "Controller" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        bluetooth_adapters.append(
                            {
                                "mac": parts[1],
                                "name": " ".join(parts[2:]),
                            }
                        )

        # Alternative: check hciconfig
        if not bluetooth_adapters:
            stdout, _, rc = self._run_command(["hciconfig", "-a"])
            if rc == 0 and "hci" in stdout:
                bluetooth_adapters.append(
                    {"description": "Bluetooth adapter detected via hciconfig"}
                )

        # Alternative: check lsusb
        if not bluetooth_adapters:
            stdout, _ = self._run_command(["lsusb"])
            for line in stdout.split("\n"):
                if "bluetooth" in line.lower():
                    bluetooth_adapters.append({"description": line.strip()})

        self.detected_hardware.usb_devices.extend(
            [{"type": "bluetooth", **adapter} for adapter in bluetooth_adapters]
        )

    def _detect_smartcard_readers(self) -> None:
        """Detect smart card readers."""
        readers = []
        stdout, _ = self._run_command(["pcsc_scan", "-m"], timeout=5)

        if stdout:
            for line in stdout.split("\n"):
                if "Using" in line or "Reader" in line:
                    readers.append({"description": line.strip()})

        # Alternative: check lsusb
        if not readers:
            stdout, _ = self._run_command(["lsusb"])
            for line in stdout.split("\n"):
                if any(kw in line.lower() for kw in ["smart", "cac", "scr", "omnikey", "acr"]):
                    readers.append({"description": line.strip()})

        self.detected_hardware.usb_devices.extend(
            [{"type": "smartcard", **reader} for reader in readers]
        )

    def _detect_numa(self) -> None:
        """Detect NUMA topology."""
        try:
            stdout, _, rc = self._run_command(["numactl", "--hardware"])
            if rc == 0:
                for line in stdout.split("\n"):
                    if "available:" in line.lower():
                        match = re.search(r"(\d+)\s+nodes", line)
                        if match:
                            self.detected_hardware.numa_nodes = int(match.group(1))
                    elif "node" in line.lower() and "cpus" in line.lower():
                        # Parse CPU list for each node
                        pass
        except Exception as e:
            self.logger.debug(f"NUMA detection failed: {e}")
            self.detected_hardware.numa_nodes = 1

    def _detect_ipmi(self) -> None:
        """Detect IPMI/BMC management interface."""
        try:
            # Check for IPMI device
            if os.path.exists("/dev/ipmi0") or os.path.exists("/dev/ipmi/0"):
                self.detected_hardware.ipmi_detected = True

            # Check using ipmitool
            stdout, _, rc = self._run_command(["ipmitool", "mc", "info"], timeout=10)
            if rc == 0 and "Manufacturer" in stdout:
                self.detected_hardware.ipmi_detected = True
                # Parse BMC info
                for line in stdout.split("\n"):
                    if "Manufacturer" in line:
                        self.detected_hardware.system_manufacturer = line.split(":")[1].strip()
                    elif "Product Name" in line:
                        self.detected_hardware.system_product = line.split(":")[1].strip()

            # Check for IPMI kernel modules
            stdout, _, rc = self._run_command(["lsmod"])
            if rc == 0 and "ipmi" in stdout:
                self.detected_hardware.ipmi_detected = True

        except Exception as e:
            self.logger.debug(f"IPMI detection failed: {e}")
            self.detected_hardware.ipmi_detected = False

    def _collect_hardware_reports(self) -> None:
        """
        Collect detailed hardware reports using various system utilities.
        Saves output files to the data directory for inclusion in test reports.
        """
        import os
        from pathlib import Path

        # Determine output directory
        output_dir = Path(self.config.data_dir) / "hardware_reports"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback to temp directory
            output_dir = Path("/tmp") / "hw-test" / "hardware_reports"
            output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Collecting hardware reports to {output_dir}")

        # Helper to save command output
        def save_output(cmd: List[str], filename: str, timeout: int = 30) -> bool:
            try:
                stdout, stderr, rc = self._run_command(cmd, timeout=timeout)
                if rc == 0 or stdout:
                    filepath = output_dir / filename
                    with open(filepath, "w", encoding="utf-8", errors="replace") as f:
                        f.write(stdout)
                    self.logger.debug(f"Saved {filename}")
                    return True
            except Exception as e:
                self.logger.debug(f"Failed to collect {filename}: {e}")
            return False

        # 8.2.1 inxi
        save_output(["inxi", "-v8", "-c2"], "inxi.txt")

        # 8.2.4 acpidump
        save_output(["acpidump"], "acpi.dat", timeout=60)

        # 8.2.5 lspci
        save_output(["lspci", "-nnk"], "lspci.txt")

        # 8.2.6 dmidecode
        save_output(["dmidecode"], "dmidecode.txt", timeout=60)

        # 8.2.7 lsusb
        save_output(["lsusb"], "lsusb.txt")
        save_output(["lsusb", "-t"], "lsusb_hierarchy.txt")

        # 8.2.8 lscpu
        save_output(["lscpu"], "lscpu.txt")

        # 8.2.9 lsblk
        save_output(["lsblk", "-ft"], "lsblk.txt")

        # 8.2.10 lsscsi
        save_output(["lsscsi", "-v"], "lsscsi.txt")

        # 8.2.11 smartctl for each disk
        disks = self.detected_hardware.disk_info
        for disk in disks:
            device = disk.get("device", "")
            if device:
                # Extract disk name (e.g., /dev/sda -> sda)
                disk_name = device.split("/")[-1]
                save_output(["smartctl", "-a", device], f"smartctl_{disk_name}.txt", timeout=60)

        # 8.2.12 rfkill
        save_output(["rfkill", "--output-all"], "rfkill.txt")

        # 8.2.13 uname
        save_output(["uname", "-a"], "uname.txt")

        # 8.2.14 xrandr (only if X is running)
        display = os.environ.get("DISPLAY")
        if display:
            save_output(["xrandr"], "xrandr.txt")

        # 8.2.15 E2K cache (only on Elbrus)
        stdout, _, rc = self._run_command(["uname", "-m"])
        if rc == 0 and "e2k" in stdout.lower():
            save_output(["sh", "-c", "grep cache /proc/bootdata"], "e2k_cache.txt")

        # Additional useful reports
        save_output(["hostnamectl"], "hostnamectl.txt")
        save_output(["uptime"], "uptime.txt")
        save_output(["cat", "/proc/version"], "proc_version.txt")
        save_output(["cat", "/proc/meminfo"], "proc_meminfo.txt")
        save_output(["cat", "/proc/cpuinfo"], "proc_cpuinfo.txt")
        save_output(["free", "-h"], "free.txt")
        save_output(["df", "-h"], "df.txt")
        save_output(["mount"], "mount.txt")
        save_output(["ps", "auxf"], "ps.txt", timeout=10)
        save_output(["systemctl", "list-units", "--type=service"], "services.txt")
        save_output(["dmesg"], "dmesg.txt", timeout=30)

        self.logger.info(f"Hardware reports collection completed. Files saved to {output_dir}")

    def _collect_spec_verification(self) -> None:
        """
        Collect hardware verification data for comparison with specifications (section 8.3).
        Saves output files for inclusion in test protocol.
        """
        import os
        from pathlib import Path

        output_dir = Path(self.config.data_dir) / "spec_verification"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            output_dir = Path("/tmp") / "hw-test" / "spec_verification"
            output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Collecting spec verification data to {output_dir}")

        def save_output(cmd: List[str], filename: str, timeout: int = 30) -> bool:
            try:
                stdout, stderr, rc = self._run_command(cmd, timeout=timeout)
                if rc == 0 or stdout:
                    filepath = output_dir / filename
                    with open(filepath, "w", encoding="utf-8", errors="replace") as f:
                        f.write(stdout)
                    self.logger.debug(f"Saved {filename}")
                    return True
            except Exception as e:
                self.logger.debug(f"Failed to collect {filename}: {e}")
            return False

        # 8.3.1 CPU and motherboard
        save_output(["inxi", "-CM"], "cpu_motherboard.txt")

        # 8.3.2 Memory
        save_output(["inxi", "-m"], "memory.txt")
        save_output(["dmidecode", "--type", "19"], "memory_dmidecode.txt", timeout=60)

        # 8.3.3 Disk subsystem
        save_output(["inxi", "-D"], "disks.txt")

        # 8.3.4 Graphics
        save_output(["inxi", "-G"], "graphics.txt")

        # 8.3.5 3D acceleration (from user session)
        display = os.environ.get("DISPLAY")
        if display:
            save_output(["glxinfo"], "3d_acceleration.txt")

        # 8.3.6 CD/DVD/Blu-ray drive info
        if os.path.exists("/proc/sys/dev/cdrom/info"):
            save_output(["cat", "/proc/sys/dev/cdrom/info"], "cdrom_info.txt")

        # Additional verification data
        save_output(["lscpu"], "lscpu_full.txt")
        save_output(["free", "-h"], "memory_free.txt")
        save_output(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], "block_devices.txt")

        self.logger.info(
            f"Spec verification data collection completed. Files saved to {output_dir}"
        )

    def execute(self) -> StepResult:
        """Execute hardware detection."""
        errors = []
        warnings = []

        self.logger.info("Starting hardware detection...")

        try:
            self._detect_cpu()
            self._detect_memory()
            self._detect_disks()
            self._detect_network()
            self._detect_gpu()
            self._detect_audio()
            self._detect_usb()
            self._detect_system_info()
            self._detect_webcams()
            self._detect_fingerprint_readers()
            self._detect_bluetooth()
            self._detect_smartcard_readers()
            self._detect_numa()
            self._detect_ipmi()
            self._collect_hardware_reports()
            self._collect_spec_verification()

            # Update hardware info for subsequent steps
            self.hardware_info = self.detected_hardware

            # Build summary
            summary = {
                "cpu": f"{self.detected_hardware.cpu_model} ({self.detected_hardware.cpu_cores} cores)",
                "memory_mb": self.detected_hardware.total_memory_mb,
                "disks_count": len(self.detected_hardware.disk_info),
                "network_interfaces": len(self.detected_hardware.network_interfaces),
                "gpus": len(self.detected_hardware.gpu_info),
                "audio_devices": len(self.detected_hardware.audio_devices),
                "usb_devices": len(self.detected_hardware.usb_devices),
                "numa_nodes": self.detected_hardware.numa_nodes,
                "system": f"{self.detected_hardware.system_manufacturer} {self.detected_hardware.system_product}",
                "bios": f"{self.detected_hardware.bios_vendor} {self.detected_hardware.bios_version}",
                "ipmi": self.detected_hardware.ipmi_detected,
                "webcams": len(self.detected_hardware.webcams),
                "fingerprint_readers": len(self.detected_hardware.fingerprint_readers),
            }

            # Check for potential issues
            if (
                not self.detected_hardware.cpu_model
                or self.detected_hardware.cpu_model == "Unknown"
            ):
                warnings.append("CPU model could not be detected")

            if self.detected_hardware.total_memory_mb == 0:
                warnings.append("Memory size could not be detected")

            if len(self.detected_hardware.network_interfaces) == 0:
                warnings.append("No network interfaces detected")

            status = TestStatus.WARNING if warnings else TestStatus.PASSED
            message = "Hardware detection completed successfully"

            return StepResult(
                step_name=self.name,
                status=status,
                message=message,
                details=summary,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            self.logger.exception(f"Hardware detection failed: {e}")
            return StepResult(
                step_name=self.name,
                status=TestStatus.ERROR,
                message=f"Hardware detection failed: {str(e)}",
                errors=[str(e)],
            )
