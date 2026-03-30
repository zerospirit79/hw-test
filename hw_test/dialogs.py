"""Dialog module for hw-test.

Provides GUI (yad) and TUI (dialog) interfaces for configuration.
"""

from __future__ import annotations

import os
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from hw_test.l10n import get_l10n, _


class DialogManager:
    """Manages GUI and TUI dialogs for hw-test."""

    def __init__(self):
        self.l10n = get_l10n()
        self.gui_available = self._check_gui()
        self.tui_available = self._check_tui()

    def _check_gui(self) -> bool:
        """Check if GUI (yad) is available."""
        if not os.environ.get("DISPLAY"):
            return False

        result = subprocess.run(["which", "yad"], capture_output=True)
        return result.returncode == 0

    def _check_tui(self) -> bool:
        """Check if TUI (dialog) is available."""
        result = subprocess.run(["which", "dialog"], capture_output=True)
        return result.returncode == 0

    def run_command(self, cmd: List[str]) -> Tuple[int, str]:
        """Run dialog command and return (returncode, output)."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode, result.stdout.strip()
        except Exception as e:
            return -1, str(e)

    def msgbox(self, text: str, title: str = "", width: int = 60, height: int = 10) -> int:
        """Show message box."""
        if self.gui_available:
            cmd = [
                "yad",
                "--width",
                str(width),
                "--title",
                title or self.l10n.get("program_name"),
                "--text",
                text,
                "--button",
                "gtk-ok:0",
                "--image",
                "dialog-information",
            ]
            rc, _ = self.run_command(cmd)
            return rc
        elif self.tui_available:
            cmd = [
                "dialog",
                "--stdout",
                "--title",
                title or self.l10n.get("program_name"),
                "--msgbox",
                text,
                str(height),
                str(width),
            ]
            rc, _ = self.run_command(cmd)
            return rc
        else:
            print(f"[{title}] {text}")
            return 0

    def yesno(self, text: str, title: str = "", width: int = 60, height: int = 10) -> bool:
        """Show yes/no dialog. Returns True if yes."""
        if self.gui_available:
            cmd = [
                "yad",
                "--width",
                str(width),
                "--title",
                title or self.l10n.get("program_name"),
                "--text",
                text,
                "--button",
                "gtk-no:1",
                "--button",
                "gtk-yes:0",
                "--image",
                "dialog-question",
            ]
            rc, _ = self.run_command(cmd)
            return rc == 0
        elif self.tui_available:
            cmd = [
                "dialog",
                "--stdout",
                "--title",
                title or self.l10n.get("program_name"),
                "--yesno",
                text,
                str(height),
                str(width),
            ]
            rc, _ = self.run_command(cmd)
            return rc == 0
        else:
            response = input(f"{text} (y/n): ")
            return response.lower() in ["y", "yes", "да"]

    def entry(
        self,
        text: str,
        title: str = "",
        entry_label: str = "",
        entry_text: str = "",
        width: int = 60,
        height: int = 10,
    ) -> Optional[str]:
        """Show entry dialog. Returns entered text or None if cancelled."""
        if self.gui_available:
            cmd = [
                "yad",
                "--width",
                str(width),
                "--title",
                title or self.l10n.get("program_name"),
                "--text",
                text,
                "--entry",
                "--entry-label",
                entry_label,
                "--entry-text",
                entry_text,
                "--button",
                "gtk-cancel:1",
                "--button",
                "gtk-ok:0",
            ]
            rc, output = self.run_command(cmd)
            return output if rc == 0 else None
        elif self.tui_available:
            cmd = [
                "dialog",
                "--stdout",
                "--title",
                title or self.l10n.get("program_name"),
                "--inputbox",
                text,
                str(height),
                str(width),
                entry_text,
            ]
            rc, output = self.run_command(cmd)
            return output if rc == 0 else None
        else:
            response = input(f"{entry_label}: ")
            return response or None

    def checklist(
        self,
        title: str,
        text: str,
        items: List[Tuple[str, str, bool]],
        width: int = 80,
        height: int = 20,
    ) -> List[str]:
        """
        Show checklist dialog.

        Args:
            title: Dialog title
            text: Dialog text
            items: List of (tag, label, initial_state) tuples
            width: Dialog width
            height: Dialog height

        Returns:
            List of selected tags
        """
        if self.gui_available:
            cmd = [
                "yad",
                "--width",
                str(width),
                "--height",
                str(height),
                "--title",
                title,
                "--text",
                text,
                "--checklist",
            ]

            for tag, label, state in items:
                cmd.extend([tag, label, str(state).lower()])

            rc, output = self.run_command(cmd)
            if rc == 0 and output:
                return output.split("|")
            return []

        elif self.tui_available:
            cmd = [
                "dialog",
                "--stdout",
                "--title",
                title,
                "--checklist",
                text,
                str(height),
                str(width),
                str(len(items)),
            ]

            for tag, label, state in items:
                cmd.extend([tag, label, "ON" if state else "OFF"])

            rc, output = self.run_command(cmd)
            if rc == 0 and output:
                # Dialog returns space-separated tags with quotes
                return [t.strip('"') for t in output.split()]
            return []
        else:
            # Fallback to text-based selection
            print(f"\n{title}")
            print(f"{text}\n")
            selected = []
            for tag, label, state in items:
                default = "[X]" if state else "[ ]"
                response = input(f"  {default} {label}: ").lower()
                if response in ["y", "yes", "да", "on"] or (state and response in ["", "n", "no"]):
                    selected.append(tag)
            return selected

    def radiolist(
        self,
        title: str,
        text: str,
        items: List[Tuple[str, str, bool]],
        width: int = 60,
        height: int = 10,
    ) -> Optional[str]:
        """
        Show radiolist dialog (single selection).

        Args:
            title: Dialog title
            text: Dialog text
            items: List of (tag, label, initial_state) tuples
            width: Dialog width
            height: Dialog height

        Returns:
            Selected tag or None if cancelled
        """
        if self.gui_available:
            cmd = [
                "yad",
                "--width",
                str(width),
                "--height",
                str(height),
                "--title",
                title,
                "--text",
                text,
                "--radiolist",
            ]

            for tag, label, state in items:
                cmd.extend([tag, label, str(state).lower()])

            rc, output = self.run_command(cmd)
            return output if rc == 0 and output else None

        elif self.tui_available:
            cmd = [
                "dialog",
                "--stdout",
                "--title",
                title,
                "--radiolist",
                text,
                str(height),
                str(width),
                str(len(items)),
            ]

            for tag, label, state in items:
                cmd.extend([tag, label, "ON" if state else "OFF"])

            rc, output = self.run_command(cmd)
            return output.strip('"') if rc == 0 and output else None
        else:
            # Fallback to text-based selection
            print(f"\n{title}")
            print(f"{text}\n")
            for i, (tag, label, _) in enumerate(items, 1):
                print(f"  {i}. {label}")
            try:
                choice = input("Select (number): ")
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    return items[idx][0]
            except (ValueError, IndexError):
                pass
            return None

    def progress(
        self, title: str, text: str, percentage: int, width: int = 400, height: int = 100
    ) -> bool:
        """
        Show progress bar.

        Args:
            title: Dialog title
            text: Progress text
            percentage: Progress percentage (0-100)
            width: Window width
            height: Window height

        Returns:
            True if should continue, False if cancelled
        """
        if self.gui_available:
            # For GUI, we use a simple progress window
            cmd = [
                "yad",
                "--progress",
                "--width",
                str(width),
                "--title",
                title,
                "--text",
                text,
                "--percentage",
                str(percentage),
                "--no-buttons",
            ]
            # Run without waiting
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            # Text-based progress
            bar_length = 40
            filled = int(bar_length * percentage / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\r[{bar}] {percentage}%", end="", flush=True)
            return True

    def config_form(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Show configuration form.

        Args:
            config: Current configuration

        Returns:
            Updated configuration
        """
        title = self.l10n.get("step_config")

        # Build test selection items
        test_items = [
            ("prepare", self.l10n.get("step_prepare"), True),
            ("upgrade", self.l10n.get("step_upgrade"), True),
            ("hardware_detection", self.l10n.get("step_hardware_detection"), True),
            (
                "firmware_check",
                self.l10n.get("step_firmware_check"),
                config.get("fwupd_available", False),
            ),
            ("syslogs", self.l10n.get("step_syslogs"), True),
            (
                "express_test",
                self.l10n.get("step_express_test"),
                config.get("express_available", False),
            ),
            ("cpupower", self.l10n.get("step_cpupower"), True),
            ("diskperf", self.l10n.get("step_diskperf"), True),
            ("glmark", self.l10n.get("step_glmark"), config.get("graphics_available", False)),
            ("system_check", self.l10n.get("step_system_check"), True),
            ("performance", self.l10n.get("step_performance"), True),
            ("log_collection", self.l10n.get("step_log_collection"), True),
            ("finalize", self.l10n.get("step_finalize"), True),
        ]

        # Show checklist
        selected = self.checklist(
            title=title, text="Select tests to run:", items=test_items, width=90, height=25
        )

        if not selected:
            # User cancelled, return current config
            return config

        # Update configuration
        config["selected_tests"] = selected

        # Ask for test name
        test_name = self.entry(
            text="Enter test session name:",
            title=title,
            entry_label="Test name",
            entry_text=config.get("name", "default"),
        )
        if test_name:
            config["name"] = test_name

        return config


def show_config_dialog(config: Dict[str, Any]) -> Dict[str, Any]:
    """Show configuration dialog using available backend."""
    manager = DialogManager()
    return manager.config_form(config)


def check_gui_available() -> bool:
    """Check if GUI is available."""
    manager = DialogManager()
    return manager.gui_available


def check_tui_available() -> bool:
    """Check if TUI is available."""
    manager = DialogManager()
    return manager.tui_available
