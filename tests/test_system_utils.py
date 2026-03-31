"""Tests for system_utils module."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from hw_test.system_utils import (
    is_pkg_installed,
    is_pkg_available,
    has_binary,
    check_internet,
    get_network_interfaces,
    detect_pc_type,
    get_product_name,
    get_disk_drives,
    detect_desktop_environments,
    get_current_desktop,
    get_terminal_for_desktop,
    CommandLogger,
    get_system_info,
)


class TestPackageManagement:
    """Test package management functions."""

    @patch("hw_test.system_utils.subprocess.run")
    def test_is_pkg_installed_true(self, mock_run):
        """Test package installed check - success."""
        mock_run.return_value = MagicMock(returncode=0)
        assert is_pkg_installed("test-pkg") is True
        mock_run.assert_called_once_with(
            ["rpm", "-q", "--", "test-pkg"],
            capture_output=True,
            text=True,
        )

    @patch("hw_test.system_utils.subprocess.run")
    def test_is_pkg_installed_false(self, mock_run):
        """Test package installed check - not installed."""
        mock_run.return_value = MagicMock(returncode=1)
        assert is_pkg_installed("test-pkg") is False

    @patch("hw_test.system_utils.subprocess.run")
    def test_is_pkg_available_true(self, mock_run):
        """Test package available check - success."""
        mock_run.return_value = MagicMock(returncode=0)
        assert is_pkg_available("test-pkg") is True
        mock_run.assert_called_once_with(
            ["apt-cache", "show", "--", "test-pkg"],
            capture_output=True,
            text=True,
        )

    @patch("hw_test.system_utils.subprocess.run")
    def test_is_pkg_available_false(self, mock_run):
        """Test package available check - not available."""
        mock_run.return_value = MagicMock(returncode=1)
        assert is_pkg_available("test-pkg") is False

    @patch("hw_test.system_utils.subprocess.run")
    def test_has_binary_true(self, mock_run):
        """Test binary check - found."""
        mock_run.return_value = MagicMock(returncode=0)
        assert has_binary("ls") is True
        mock_run.assert_called_once_with(
            ["which", "--", "ls"],
            capture_output=True,
        )

    @patch("hw_test.system_utils.subprocess.run")
    def test_has_binary_false(self, mock_run):
        """Test binary check - not found."""
        mock_run.return_value = MagicMock(returncode=1)
        assert has_binary("nonexistent-binary") is False


class TestNetwork:
    """Test network functions."""

    @patch("hw_test.system_utils.subprocess.run")
    def test_check_internet_success(self, mock_run):
        """Test internet check - success."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ping statistics ..., 0% packet loss, ...",
        )
        assert check_internet("ya.ru") is True
        mock_run.assert_called_once_with(
            ["ping", "-c4", "-W10", "--", "ya.ru"],
            capture_output=True,
            text=True,
        )

    @patch("hw_test.system_utils.subprocess.run")
    def test_check_internet_packet_loss(self, mock_run):
        """Test internet check - packet loss."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ping statistics ..., 50% packet loss, ...",
        )
        assert check_internet() is False

    @patch("hw_test.system_utils.subprocess.run")
    def test_get_network_interfaces(self, mock_run):
        """Test network interfaces detection."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1: eth0: <BROADCAST> ...\n2: lo: <LOOPBACK> ...\n3: wlan0: <BROADCAST> ...",
        )
        ifaces = get_network_interfaces()
        assert "eth0" in ifaces
        assert "lo" not in ifaces  # Excluded
        assert "wlan0" in ifaces


class TestPCTypeDetection:
    """Test PC type detection."""

    @patch("hw_test.system_utils.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="3")
    def test_detect_pc_type_personal(self, mock_file, mock_exists):
        """Test PC type detection - Personal."""
        mock_exists.return_value = True
        assert detect_pc_type() == "Personal"

    @patch("hw_test.system_utils.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="8")
    def test_detect_pc_type_notebook(self, mock_file, mock_exists):
        """Test PC type detection - Notebook."""
        mock_exists.return_value = True
        assert detect_pc_type() == "Notebook"

    @patch("hw_test.system_utils.os.path.exists")
    @patch("hw_test.system_utils.subprocess.run")
    def test_detect_pc_type_virtual(self, mock_run, mock_exists):
        """Test PC type detection - Virtual."""
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(
            stdout="Hypervisor vendor: KVM\n",
        )
        assert detect_pc_type() == "Virtual"

    @patch("hw_test.system_utils.os.path.exists")
    def test_detect_pc_type_unknown(self, mock_exists):
        """Test PC type detection - unknown type."""
        mock_exists.return_value = False
        with patch("hw_test.system_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            assert detect_pc_type() == "Computer"


class TestDiskDetection:
    """Test disk drive detection."""

    def test_get_disk_drives_empty(self):
        """Test disk drives detection - empty when no drives."""
        # This test just ensures the function doesn't crash
        drives = get_disk_drives()
        assert isinstance(drives, list)


class TestDesktopEnvironment:
    """Test desktop environment detection."""

    @patch("hw_test.system_utils.is_pkg_installed")
    def test_detect_desktop_environments(self, mock_installed):
        """Test DE detection."""
        mock_installed.side_effect = lambda pkg: pkg == "gnome-shell"

        des = detect_desktop_environments()
        assert des["gnome"] is True
        assert des["kde"] is False

    @patch("hw_test.system_utils.os.environ.get")
    def test_get_current_desktop_gnome(self, mock_getenv):
        """Test current desktop detection - GNOME."""
        mock_getenv.return_value = "GNOME"
        assert get_current_desktop() == "gnome"

    @patch("hw_test.system_utils.os.environ.get")
    def test_get_current_desktop_unknown(self, mock_getenv):
        """Test current desktop detection - unknown."""
        mock_getenv.return_value = "UNKNOWN"
        assert get_current_desktop() is None

    @patch("hw_test.system_utils.has_binary")
    @patch("hw_test.system_utils.get_current_desktop")
    def test_get_terminal_for_desktop(self, mock_current, mock_has):
        """Test terminal detection."""
        mock_current.return_value = "gnome"
        mock_has.return_value = True

        terminal = get_terminal_for_desktop()
        assert terminal == ["kgx"]


class TestCommandLogger:
    """Test command logging."""

    @patch("hw_test.system_utils.subprocess.run")
    def test_spawn_success(self, mock_run):
        """Test command execution with logging."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        logger = CommandLogger()
        stdout, stderr, rc = logger.spawn(["ls", "-la"])

        assert stdout == "output"
        assert stderr == ""
        assert rc == 0

    @patch("hw_test.system_utils.subprocess.run")
    def test_spawn_timeout(self, mock_run):
        """Test command timeout."""
        mock_run.side_effect = Exception("Timeout")

        logger = CommandLogger()
        stdout, stderr, rc = logger.spawn(["long-command"])

        assert rc == -1


class TestSystemInfo:
    """Test system information gathering."""

    @patch("hw_test.system_utils.detect_pc_type")
    @patch("hw_test.system_utils.get_product_name")
    @patch("hw_test.system_utils.get_disk_drives")
    @patch("hw_test.system_utils.get_network_interfaces")
    @patch("hw_test.system_utils.detect_desktop_environments")
    @patch("hw_test.system_utils.get_current_desktop")
    @patch("hw_test.system_utils.has_binary")
    @patch("hw_test.system_utils.is_pkg_installed")
    @patch("hw_test.system_utils.subprocess.run")
    @patch("hw_test.system_utils.os.path.exists")
    def test_get_system_info(
        self,
        mock_exists,
        mock_run,
        mock_pkg,
        mock_bin,
        mock_current,
        mock_de,
        mock_ifaces,
        mock_drives,
        mock_product,
        mock_type,
    ):
        """Test system info gathering."""
        mock_type.return_value = "Personal"
        mock_product.return_value = "Test Product"
        mock_drives.return_value = ["sda"]
        mock_ifaces.return_value = ["eth0"]
        mock_de.return_value = {"gnome": True}
        mock_current.return_value = "gnome"
        mock_bin.return_value = True
        mock_pkg.return_value = False
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        mock_exists.return_value = True  # For systemd check

        info = get_system_info()

        assert info["pc_type"] == "Personal"
        assert info["product_name"] == "Test Product"
        assert info["drives"] == ["sda"]
        assert info["interfaces"] == ["eth0"]
        assert info["has_xorg"] is True
        assert info["has_systemd"] is True
