"""Tests for CLI module."""

import pytest
from unittest.mock import patch, MagicMock
from hw_test.cli import create_parser, list_steps


class TestCreateParser:
    """Test argument parser creation."""

    @pytest.fixture
    def parser(self):
        """Create argument parser."""
        return create_parser()

    def test_parser_creation(self, parser):
        """Test parser is created."""
        assert parser is not None

    def test_start_argument(self, parser):
        """Test --start argument."""
        args = parser.parse_args(["--start"])
        assert args.start is True

    def test_list_steps_argument(self, parser):
        """Test --list-steps argument."""
        args = parser.parse_args(["--list-steps"])
        assert args.list_steps is True

    def test_batch_argument(self, parser):
        """Test --batch argument."""
        args = parser.parse_args(["--start", "--batch"])
        assert args.batch is True

    def test_verbose_argument(self, parser):
        """Test --verbose argument."""
        args = parser.parse_args(["--start", "-v"])
        assert args.verbose is True

    def test_name_argument(self, parser):
        """Test --name argument."""
        args = parser.parse_args(["--start", "--name", "test-pc"])
        assert args.name == "test-pc"

    def test_steps_argument(self, parser):
        """Test --steps argument."""
        args = parser.parse_args(["--start", "--steps", "hardware_detection,express_test"])
        assert args.steps == "hardware_detection,express_test"

    def test_skip_argument(self, parser):
        """Test --skip argument."""
        args = parser.parse_args(["--start", "--skip", "performance"])
        assert args.skip == "performance"

    def test_output_dir_argument(self, parser):
        """Test --output-dir argument."""
        args = parser.parse_args(["--start", "--output-dir", "/tmp/test"])
        assert args.output_dir == "/tmp/test"

    def test_language_argument(self, parser):
        """Test --language argument."""
        args = parser.parse_args(["--start", "--language", "en"])
        assert args.language == "en"

    def test_mutually_exclusive_modes(self, parser):
        """Test that --start and --list-steps are mutually exclusive."""
        with pytest.raises(SystemExit):
            parser.parse_args(["--start", "--list-steps"])

    def test_version_argument(self, parser):
        """Test --version argument."""
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])


class TestListSteps:
    """Test list_steps function."""

    @patch("hw_test.cli.print")
    def test_list_steps_output(self, mock_print):
        """Test that list_steps prints steps."""
        list_steps()
        assert mock_print.called


class TestSteps:
    """Test step-related functionality."""

    def test_available_steps_count(self):
        """Test that we have expected number of steps."""
        from hw_test.steps import AVAILABLE_STEPS

        assert len(AVAILABLE_STEPS) >= 15

    def test_default_step_order(self):
        """Test default step order."""
        from hw_test.steps import DEFAULT_STEP_ORDER

        assert "prepare" in DEFAULT_STEP_ORDER
        assert "upgrade" in DEFAULT_STEP_ORDER
        assert "finalize" in DEFAULT_STEP_ORDER

    def test_get_step_class(self):
        """Test getting step class by name."""
        from hw_test.steps import get_step_class, PrepareStep

        step_class = get_step_class("prepare")
        assert step_class == PrepareStep

    def test_get_unknown_step(self):
        """Test getting unknown step class."""
        from hw_test.steps import get_step_class

        step_class = get_step_class("unknown_step")
        assert step_class is None
