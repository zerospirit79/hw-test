"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path
import pytest
from hw_test.config import HWTestConfig, ConfigLoader, load_config


class TestHWTestConfig:
    """Test HWTestConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HWTestConfig()
        assert config.update_apt_lists is True
        assert config.dist_upgrade is True
        assert config.update_kernel is True
        assert config.batch_mode is False
        assert config.lang_id == "ru"
        assert config.data_dir == "/var/lib/hw-test"

    def test_colors_enabled(self):
        """Test colors_enabled property."""
        config = HWTestConfig()
        config.color_mode = "always"
        assert config.colors_enabled is True

        config.color_mode = "never"
        assert config.colors_enabled is False


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_load_empty(self):
        """Test loading with no config files."""
        loader = ConfigLoader()
        config = loader.load()
        assert isinstance(config, HWTestConfig)

    def test_load_from_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "hw-test.conf"
        config_file.write_text(
            """
[settings]
batch_mode = true
lang_id = en
ping_server = 8.8.8.8
"""
        )

        loader = ConfigLoader()
        loader.SYSTEM_CONFIG = config_file
        loader.USER_CONFIG = tmp_path / "nonexistent.conf"

        config = loader.load()
        assert config.batch_mode is True
        assert config.lang_id == "en"
        assert config.ping_server == "8.8.8.8"

    def test_load_user_overrides_system(self, tmp_path):
        """Test that user config overrides system config."""
        system_config = tmp_path / "system.conf"
        system_config.write_text(
            """
[settings]
batch_mode = false
lang_id = ru
"""
        )

        user_config = tmp_path / "user.conf"
        user_config.write_text(
            """
[settings]
batch_mode = true
"""
        )

        loader = ConfigLoader()
        loader.SYSTEM_CONFIG = system_config
        loader.USER_CONFIG = user_config

        config = loader.load()
        assert config.batch_mode is True  # From user
        assert config.lang_id == "ru"  # From system

    def test_load_env_overrides_all(self, tmp_path, monkeypatch):
        """Test that environment variables override files."""
        config_file = tmp_path / "hw-test.conf"
        config_file.write_text(
            """
[settings]
batch_mode = false
lang_id = ru
"""
        )

        monkeypatch.setenv("HWTEST_BATCH", "true")
        monkeypatch.setenv("HWTEST_LANG", "en")

        loader = ConfigLoader()
        loader.SYSTEM_CONFIG = config_file
        loader.USER_CONFIG = tmp_path / "nonexistent.conf"

        config = loader.load()
        assert config.batch_mode is True  # From env
        assert config.lang_id == "en"  # From env


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_returns_config(self):
        """Test that load_config returns HWTestConfig."""
        config = load_config()
        assert isinstance(config, HWTestConfig)
