"""Tests for state management module."""

import json
import os
import tempfile
from pathlib import Path
import pytest
from hw_test.state import TestState, TestConfig, get_test_state


class TestTestState:
    """Test TestState class."""

    @pytest.fixture
    def temp_state(self, tmp_path):
        """Create a temporary state instance."""
        config = TestConfig(data_dir=str(tmp_path))
        state = TestState(config)
        return state

    def test_initialize(self, temp_state):
        """Test state initialization."""
        temp_state.initialize("test-name", ["step1", "step2"])

        assert temp_state.state["test_name"] == "test-name"
        assert temp_state.state["status"] == "running"
        assert temp_state.state["steps_to_run"] == ["step1", "step2"]
        assert temp_state.state["completed_steps"] == []
        assert temp_state.state["requires_reboot"] is False

    def test_save_and_load(self, temp_state):
        """Test saving and loading state."""
        temp_state.initialize("test-name", ["step1"])
        temp_state.save()

        # Create new state and load
        new_state = TestState(temp_state.config)
        assert new_state.load()
        assert new_state.state["test_name"] == "test-name"

    def test_mark_step_started(self, temp_state):
        """Test marking step as started."""
        temp_state.initialize("test", ["step1"])
        temp_state.mark_step_started("step1")

        assert temp_state.state["current_step"] == "step1"

    def test_mark_step_completed(self, temp_state):
        """Test marking step as completed."""
        from hw_test.types import StepResult, TestStatus

        temp_state.initialize("test", ["step1"])
        result = StepResult(step_name="step1", status=TestStatus.PASSED, message="OK")
        assert temp_state.mark_step_completed("step1", result) is True

        assert "step1" in temp_state.state["completed_steps"]
        assert temp_state.state["results"]["step1"]["status"] == "passed"

    def test_mark_step_failed(self, temp_state):
        """Test marking step as failed."""
        temp_state.initialize("test", ["step1"])
        temp_state.mark_step_failed("step1", "Error message")

        assert "step1" in temp_state.state["failed_steps"]
        assert temp_state.state["results"]["step1"]["status"] == "failed"

    def test_mark_step_skipped(self, temp_state):
        """Test marking step as skipped."""
        temp_state.initialize("test", ["step1"])
        temp_state.mark_step_skipped("step1", "Not applicable")

        assert "step1" in temp_state.state["skipped_steps"]

    def test_get_next_step(self, temp_state):
        """Test getting next step."""
        temp_state.initialize("test", ["step1", "step2", "step3"])

        assert temp_state.get_next_step() == "step1"

        assert (
            temp_state.mark_step_completed(
                "step1",
                type(
                    "obj",
                    (object,),
                    {
                        "status": type("obj", (object,), {"value": "passed"}),
                        "message": "",
                        "details": {},
                        "duration_seconds": 0,
                        "errors": [],
                        "warnings": [],
                    },
                )(),
            )
            is True
        )

        assert temp_state.get_next_step() == "step2"

    def test_is_resumed_test(self, temp_state):
        """Test is_resumed_test method."""
        temp_state.initialize("test", ["step1", "step2"])
        assert (
            temp_state.mark_step_completed(
                "step1",
                type(
                    "obj",
                    (object,),
                    {
                        "status": type("obj", (object,), {"value": "passed"}),
                        "message": "",
                        "details": {},
                        "duration_seconds": 0,
                        "errors": [],
                        "warnings": [],
                    },
                )(),
            )
            is True
        )

        assert temp_state.is_resumed_test() is True

    def test_mark_reboot_required(self, temp_state):
        """Test marking reboot as required."""
        temp_state.initialize("test", ["step1"])
        assert temp_state.mark_reboot_required("Kernel update") is True

        assert temp_state.state["requires_reboot"] is True
        assert temp_state.state["reboot_reason"] == "Kernel update"

    def test_clear_reboot_flag(self, temp_state):
        """Test clearing reboot flag."""
        temp_state.initialize("test", ["step1"])
        temp_state.mark_reboot_required("Test")
        assert temp_state.clear_reboot_flag() is True

        assert temp_state.state["requires_reboot"] is False
        assert temp_state.state["reboot_count"] == 1

    def test_finalize(self, temp_state):
        """Test finalizing test."""
        temp_state.initialize("test", ["step1"])
        temp_state.finalize("completed")

        assert temp_state.state["status"] == "completed"
        assert "end_time" in temp_state.state

    def test_get_summary(self, temp_state):
        """Test getting summary."""
        temp_state.initialize("test", ["step1", "step2"])
        summary = temp_state.get_summary()

        assert summary["test_name"] == "test"
        assert summary["total_steps"] == 2
        assert summary["status"] == "running"

    def test_cleanup(self, temp_state):
        """Test cleanup removes state file."""
        temp_state.initialize("test", ["step1"])
        temp_state.save()

        assert os.path.exists(temp_state.state_file)

        temp_state.cleanup()

        assert not os.path.exists(temp_state.state_file)


class TestGetTestState:
    """Test get_test_state function."""

    def test_get_test_state_returns_state(self, tmp_path):
        """Test that get_test_state returns TestState."""
        config = TestConfig(data_dir=str(tmp_path))
        state = get_test_state(config)
        assert isinstance(state, TestState)
