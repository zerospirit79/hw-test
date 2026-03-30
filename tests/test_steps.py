"""Tests for hw-test steps."""

import pytest
from unittest.mock import patch, MagicMock
from hw_test.types import TestConfig, TestStatus, HardwareInfo


class TestPrepareStep:
    """Test PrepareStep."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TestConfig()

    @pytest.fixture
    def hardware_info(self):
        """Create hardware info."""
        return HardwareInfo()

    def test_step_initialization(self, config, hardware_info):
        """Test step initialization."""
        from hw_test.steps.step_08_prepare import PrepareStep

        step = PrepareStep(config, hardware_info)
        assert step.name == "System Preparation"
        assert step.requires_root is True

    @patch("hw_test.steps.step_08_prepare.PrepareStep._run_command")
    def test_check_ima_evm_disabled(self, mock_run, config):
        """Test IMA/EVM check when disabled."""
        from hw_test.steps.step_08_prepare import PrepareStep

        step = PrepareStep(config)
        mock_run.return_value = ("", "", 0)

        # Mock file read to return disabled state
        with patch("builtins.open", MagicMock(side_effect=FileNotFoundError())):
            result = step._check_ima_evm()
            assert result is None


class TestSyslogsStep:
    """Test SyslogsStep."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TestConfig()

    def test_step_initialization(self, config):
        """Test step initialization."""
        from hw_test.steps.step_11_syslogs import SyslogsStep

        step = SyslogsStep(config)
        assert step.name == "System Logs Check"
        assert step.requires_root is True

    def test_gzip_compress(self, config):
        """Test gzip compression."""
        from hw_test.steps.step_11_syslogs import SyslogsStep

        step = SyslogsStep(config)
        compressed = step._gzip_compress("test data")
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0


class TestFinalizeStep:
    """Test FinalizeStep."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TestConfig(name="test-pc")

    def test_step_initialization(self, config):
        """Test step initialization."""
        from hw_test.steps.step_15_finalize import FinalizeStep

        step = FinalizeStep(config)
        assert step.name == "Finalization"
        assert step.requires_root is True

    def test_archive_naming(self, config, tmp_path):
        """Test archive naming format."""
        from hw_test.steps.step_15_finalize import FinalizeStep
        from pathlib import Path

        step = FinalizeStep(config)
        step._get_workdir = lambda: tmp_path

        # Test archive name format
        archive_path = step._create_archive(tmp_path)
        if archive_path:
            assert "hw-test-test-pc-" in archive_path
            assert ".tar.gz" in archive_path


class TestStepOrder:
    """Test step execution order."""

    def test_prepare_before_upgrade(self):
        """Test that prepare comes before upgrade."""
        from hw_test.steps import DEFAULT_STEP_ORDER

        prepare_idx = DEFAULT_STEP_ORDER.index("prepare")
        upgrade_idx = DEFAULT_STEP_ORDER.index("upgrade")

        assert prepare_idx < upgrade_idx

    def test_finalize_last(self):
        """Test that finalize is last."""
        from hw_test.steps import DEFAULT_STEP_ORDER

        assert DEFAULT_STEP_ORDER[-1] == "finalize"

    def test_reboot_before_log_collection(self):
        """Test that reboot comes before log collection."""
        from hw_test.steps import DEFAULT_STEP_ORDER

        reboot_idx = DEFAULT_STEP_ORDER.index("reboot_and_continue")
        log_idx = DEFAULT_STEP_ORDER.index("log_collection")

        assert reboot_idx < log_idx


class TestStepResults:
    """Test step result types."""

    def test_test_status_enum(self):
        """Test TestStatus enum values."""
        assert TestStatus.PASSED.value == "passed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.WARNING.value == "warning"
        assert TestStatus.SKIPPED.value == "skipped"
        assert TestStatus.ERROR.value == "error"

    def test_hardware_info_defaults(self):
        """Test HardwareInfo default values."""
        hw = HardwareInfo()
        assert hw.cpu_model == ""
        assert hw.cpu_cores == 0
        assert hw.total_memory_mb == 0
