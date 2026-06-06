#!/usr/bin/python3
# Copyright (C) 2024-2026, ALT Linux Team
"""DE-independent terminal launcher for hw-test."""

from __future__ import annotations

import sys

from hw_test.de_terminal import launch_in_terminal


def main() -> int:
    try:
        launch_in_terminal(["hw-test", "--desktop-icon"], delay=0)
    except SystemExit:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
