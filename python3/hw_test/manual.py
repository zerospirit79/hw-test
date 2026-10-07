"""Results of methodology sub-items and manual verdicts of the tester.

Steps may cover several methodology items (10.2.1, 10.2.3, 10.6.2.x...).
Each such item is written to ``results-<step>.txt`` (``number<TAB>STATUS``)
in the current directory; the protocol picks these files up.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hw_test.constants import TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.context import RuntimeContext, graphical_session

STATUS_NAMES = {
    TEST_PASSED: "PASSED",
    TEST_FAILED: "FAILED",
    TEST_SKIPPED: "SKIPPED",
    TEST_BLOCKED: "BLOCKED",
}
_TTY_KEYS = {"p": TEST_PASSED, "f": TEST_FAILED, "s": TEST_SKIPPED, "b": TEST_BLOCKED}


def record_subresult(step_id: str, number: str, rc: int) -> None:
    """Store (or replace) the status of one methodology item."""
    path = Path(f"results-{step_id}.txt")
    lines = []
    if path.is_file():
        lines = [
            ln
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln and not ln.startswith(f"{number}\t")
        ]
    lines.append(f"{number}\t{STATUS_NAMES.get(rc, str(rc))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def overall_status(statuses: list[int]) -> int:
    """FAILED wins, then PASSED; nothing performed gives SKIPPED/BLOCKED."""
    if TEST_FAILED in statuses:
        return TEST_FAILED
    if TEST_PASSED in statuses:
        return TEST_PASSED
    if TEST_BLOCKED in statuses:
        return TEST_BLOCKED
    return TEST_SKIPPED


def _ask_tty(ctx: RuntimeContext, number: str, title: str) -> int:
    ru = ctx.langid == "ru"
    prompt = (
        f"\n{number}. {title}\n"
        + (
            f"Выполните проверку по разделу {number} методики и укажите результат:\n"
            "  p — PASSED, f — FAILED, s — SKIPPED, b — BLOCKED\n> "
            if ru
            else f"Perform section {number} of the methodology and enter the result:\n"
            "  p — PASSED, f — FAILED, s — SKIPPED, b — BLOCKED\n> "
        )
    )
    try:
        out = open("/dev/tty", "w", encoding="utf-8", buffering=1)
        inp = open("/dev/tty", encoding="utf-8")
    except OSError:
        return TEST_BLOCKED
    try:
        while True:
            out.write(prompt)
            answer = inp.readline()
            if answer == "":
                return TEST_BLOCKED
            key = answer.strip().lower()[:1]
            if key in _TTY_KEYS:
                break
        out.write("Комментарий (Enter — без комментария): " if ru else "Comment (Enter to skip): ")
        comment = inp.readline().strip()
    finally:
        out.close()
        inp.close()
    if comment:
        Path(f"comments-{number}.txt").write_text(comment + "\n", encoding="utf-8")
    return _TTY_KEYS[key]


def ask_result(ctx: RuntimeContext, number: str, title: str, fragment: str = "") -> int:
    """Ask the tester for a verdict: yad form, console prompt, or SKIPPED in batch mode."""
    if ctx.batchmode:
        return TEST_SKIPPED
    if graphical_session() and ctx.has_binary("yad"):
        from hw_test.gui import forms

        saved = ctx.number
        ctx.number = number
        try:
            return forms.form_gui(ctx, fragment, f"{number}. {title}")
        finally:
            ctx.number = saved
    if sys.stdin.isatty() or Path("/dev/tty").exists():
        return _ask_tty(ctx, number, title)
    return TEST_BLOCKED
