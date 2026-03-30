"""Test state management for hw-test.

Provides state persistence to allow test continuation after reboot.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from hw_test.types import TestConfig, TestStatus, StepResult


STATE_FILE = "test_state.json"
STATE_DIR = "/var/lib/hw-test"


class TestState:
    """Manages test state persistence for recovery after reboot."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.state_dir = config.data_dir
        self.state_file = os.path.join(self.state_dir, STATE_FILE)
        self.state: Dict[str, Any] = {}

    def load(self) -> bool:
        """
        Load state from disk.

        Returns:
            True if state was loaded successfully
        """
        if not os.path.exists(self.state_file):
            return False

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠ Не удалось загрузить состояние: {e}")
            return False

    def save(self) -> bool:
        """
        Save current state to disk.

        Returns:
            True if state was saved successfully
        """
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"⚠ Не удалось сохранить состояние: {e}")
            return False

    def initialize(self, test_name: str, steps_to_run: List[str]) -> None:
        """
        Initialize new test state.

        Args:
            test_name: Name of the test session
            steps_to_run: List of step names to execute
        """
        self.state = {
            "test_name": test_name,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "status": "running",
            "current_step": None,
            "completed_steps": [],
            "failed_steps": [],
            "skipped_steps": [],
            "steps_to_run": steps_to_run,
            "results": {},
            "hardware_info": {},
            "reboot_count": 0,
            "requires_reboot": False,
            "reboot_reason": None,
        }

    def mark_step_started(self, step_name: str) -> None:
        """Mark a step as currently running."""
        self.state["current_step"] = step_name
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def mark_step_completed(self, step_name: str, result: StepResult) -> None:
        """
        Mark a step as completed.

        Args:
            step_name: Name of the completed step
            result: Step result
        """
        if step_name in self.state["current_step"]:
            self.state["current_step"] = None

        self.state["completed_steps"].append(step_name)
        self.state["results"][step_name] = {
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def mark_step_failed(self, step_name: str, error: str) -> None:
        """Mark a step as failed."""
        self.state["failed_steps"].append(step_name)
        self.state["results"][step_name] = {
            "status": "failed",
            "message": error,
            "details": {},
            "duration_seconds": 0,
            "errors": [error],
            "warnings": [],
        }
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def mark_step_skipped(self, step_name: str, reason: str = "") -> None:
        """Mark a step as skipped."""
        self.state["skipped_steps"].append(step_name)
        self.state["results"][step_name] = {
            "status": "skipped",
            "message": reason,
            "details": {},
            "duration_seconds": 0,
            "errors": [],
            "warnings": [],
        }
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def set_hardware_info(self, hardware_info: Dict[str, Any]) -> None:
        """Store hardware information."""
        self.state["hardware_info"] = hardware_info
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def mark_reboot_required(self, reason: str) -> None:
        """
        Mark that a reboot is required.

        Args:
            reason: Reason for reboot
        """
        self.state["requires_reboot"] = True
        self.state["reboot_reason"] = reason
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def clear_reboot_flag(self) -> None:
        """Clear reboot requirement after reboot."""
        self.state["requires_reboot"] = False
        self.state["reboot_reason"] = None
        self.state["reboot_count"] = self.state.get("reboot_count", 0) + 1
        self.state["last_update"] = datetime.now().isoformat()
        self.save()

    def finalize(self, status: str = "completed") -> None:
        """
        Finalize the test.

        Args:
            status: Final status ("completed", "failed", "interrupted")
        """
        self.state["status"] = status
        self.state["end_time"] = datetime.now().isoformat()
        self.state["current_step"] = None
        self.save()

    def get_next_step(self) -> Optional[str]:
        """
        Get the next step to execute.

        Returns:
            Name of next step or None if all steps completed
        """
        steps_to_run = self.state.get("steps_to_run", [])
        completed = set(self.state.get("completed_steps", []))
        failed = set(self.state.get("failed_steps", []))
        skipped = set(self.state.get("skipped_steps", []))

        for step in steps_to_run:
            if step not in completed and step not in failed and step not in skipped:
                return step

        return None

    def is_resumed_test(self) -> bool:
        """Check if this is a resumed test after reboot."""
        return (
            self.state.get("status") == "running"
            and self.state.get("current_step") is not None
        ) or (
            self.state.get("status") == "running"
            and len(self.state.get("completed_steps", [])) > 0
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        return {
            "test_name": self.state.get("test_name", "unknown"),
            "status": self.state.get("status", "unknown"),
            "start_time": self.state.get("start_time", "unknown"),
            "last_update": self.state.get("last_update", "unknown"),
            "completed_steps": len(self.state.get("completed_steps", [])),
            "failed_steps": len(self.state.get("failed_steps", [])),
            "skipped_steps": len(self.state.get("skipped_steps", [])),
            "total_steps": len(self.state.get("steps_to_run", [])),
            "reboot_count": self.state.get("reboot_count", 0),
            "requires_reboot": self.state.get("requires_reboot", False),
            "reboot_reason": self.state.get("reboot_reason"),
        }

    def cleanup(self) -> None:
        """Remove state file after successful completion."""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except IOError:
                pass


def get_test_state(config: TestConfig) -> TestState:
    """Create or load test state."""
    state = TestState(config)
    state.load()
    return state
