"""Configuration module for hw-test.

Loads configuration from:
- /etc/hw-test.conf (system-wide)
- ~/.config/hw-test.conf (user-specific)
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class HWTestConfig:
    """Configuration settings for hw-test."""

    # APT sources
    update_apt_lists: bool = True
    dist_upgrade: bool = True
    update_kernel: bool = True

    # Local mirror
    local_url: str = ""
    local_mirror: str = ""
    mirror_subdir: str = ""
    local_media_base: str = ""
    local_media_labels: List[str] = field(default_factory=list)
    local_media_check: str = ""

    # Console colors
    color_mode: str = "auto"  # auto, always, never

    # Testing options
    unsafe_diskperf: bool = False
    disable_autorun: bool = False
    ping_server: str = "ya.ru"
    express_video_set: str = "vkvideo"
    local_video_sample: str = ""

    # Runtime settings
    batch_mode: bool = False
    lang_id: str = "ru"  # 'en' or 'ru'
    verbose: bool = False

    # Paths
    data_dir: str = "/var/lib/hw-test"
    log_dir: str = "/var/log/hw-test"
    config_dir: str = "/etc/hw-test"

    # Test selection
    selected_tests: List[str] = field(default_factory=list)
    skip_tests: List[str] = field(default_factory=list)

    # Computer name
    compname: str = ""
    repodate: str = ""

    @property
    def colors_enabled(self) -> bool:
        """Check if colors should be enabled."""
        return self.color_mode == "always" or (self.color_mode == "auto" and os.isatty(1))


class ConfigLoader:
    """Loads and merges configuration from multiple sources."""

    SYSTEM_CONFIG = Path("/etc/hw-test.conf")
    USER_CONFIG = Path.home() / ".config" / "hw-test.conf"

    def __init__(self):
        self.config = HWTestConfig()

    def load(self) -> HWTestConfig:
        """Load configuration from all sources."""
        # Load system config first
        if self.SYSTEM_CONFIG.exists():
            self._load_file(self.SYSTEM_CONFIG)

        # User config overrides system config
        if self.USER_CONFIG.exists():
            self._load_file(self.USER_CONFIG)

        # Environment variables override everything
        self._load_env()

        return self.config

    def _load_file(self, path: Path) -> None:
        """Load configuration from a single file."""
        try:
            config = configparser.ConfigParser()
            config.read(path)

            if "settings" in config:
                settings = config["settings"]

                # Boolean options
                self.config.update_apt_lists = settings.getboolean(
                    "update_apt_lists", self.config.update_apt_lists
                )
                self.config.dist_upgrade = settings.getboolean(
                    "dist_upgrade", self.config.dist_upgrade
                )
                self.config.update_kernel = settings.getboolean(
                    "update_kernel", self.config.update_kernel
                )
                self.config.unsafe_diskperf = settings.getboolean(
                    "unsafe_diskperf", self.config.unsafe_diskperf
                )
                self.config.disable_autorun = settings.getboolean(
                    "disable_autorun", self.config.disable_autorun
                )
                self.config.verbose = settings.getboolean("verbose", self.config.verbose)
                self.config.batch_mode = settings.getboolean("batch_mode", self.config.batch_mode)

                # String options
                self.config.local_url = settings.get("local_url", self.config.local_url)
                self.config.local_mirror = settings.get("local_mirror", self.config.local_mirror)
                self.config.mirror_subdir = settings.get("mirror_subdir", self.config.mirror_subdir)
                self.config.local_media_base = settings.get(
                    "local_media_base", self.config.local_media_base
                )
                self.config.local_media_check = settings.get(
                    "local_media_check", self.config.local_media_check
                )
                self.config.ping_server = settings.get("ping_server", self.config.ping_server)
                self.config.express_video_set = settings.get(
                    "express_video_set", self.config.express_video_set
                )
                self.config.local_video_sample = settings.get(
                    "local_video_sample", self.config.local_video_sample
                )
                self.config.color_mode = settings.get("color_mode", self.config.color_mode)
                self.config.lang_id = settings.get("lang_id", self.config.lang_id)
                self.config.compname = settings.get("compname", self.config.compname)
                self.config.repodate = settings.get("repodate", self.config.repodate)
                self.config.data_dir = settings.get("data_dir", self.config.data_dir)
                self.config.log_dir = settings.get("log_dir", self.config.log_dir)

                # List options
                if "local_media_labels" in settings:
                    self.config.local_media_labels = [
                        l.strip() for l in settings["local_media_labels"].split(",")
                    ]

                if "selected_tests" in settings:
                    self.config.selected_tests = [
                        t.strip() for t in settings["selected_tests"].split(",")
                    ]

                if "skip_tests" in settings:
                    self.config.skip_tests = [t.strip() for t in settings["skip_tests"].split(",")]

        except Exception as e:
            print(f"Warning: Failed to load config {path}: {e}")

    def _load_env(self) -> None:
        """Load configuration from environment variables."""
        env_map = {
            "HWTEST_DATA_DIR": "data_dir",
            "HWTEST_LOG_DIR": "log_dir",
            "HWTEST_LANG": "lang_id",
            "HWTEST_COLOR": "color_mode",
            "HWTEST_BATCH": "batch_mode",
            "HWTEST_VERBOSE": "verbose",
        }

        for env_var, attr in env_map.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                if attr in ["batch_mode", "verbose"]:
                    setattr(self.config, attr, value.lower() in ["1", "true", "yes"])
                else:
                    setattr(self.config, attr, value)


def load_config() -> HWTestConfig:
    """Load and return configuration."""
    loader = ConfigLoader()
    return loader.load()


def get_config() -> HWTestConfig:
    """Get configuration (singleton-like)."""
    if not hasattr(get_config, "_config"):
        get_config._config = load_config()
    return get_config._config
