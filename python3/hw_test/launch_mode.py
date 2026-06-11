"""Определение режима запуска и подготовка нового прогона тестирования."""

from __future__ import annotations

import os
import re
import shutil
import time
from datetime import date
from pathlib import Path

from hw_test.constants import TEST_PASSED
from hw_test.context import RuntimeContext
from hw_test.resume_autorun import setup_resume_autorun
from hw_test.steps import create_step
from hw_test.terminal import read_key


def workdir_has_retest_data(workdir: Path) -> bool:
    """Есть ли сохранённые результаты для повторного прохождения теста."""
    return (workdir / "RESULTS").is_file() or (workdir / "STATE" / "RESULTS").is_file()


def workdir_has_retest_settings(workdir: Path) -> bool:
    """Есть ли settings.ini для повторного прохождения теста."""
    return (workdir / "settings.ini").is_file() or (workdir / "STATE" / "settings.ini").is_file()


def resolve_launch_mode(ctx: RuntimeContext) -> None:
    """Установить ctx.launchmode и ctx.workdir по CLI и состоянию ~/HW-TEST."""
    home = ctx.homedir or os.environ.get("HOME", "")
    lastdir = Path(home) / "HW-TEST"

    if ctx.launchmode == "auto":
        if (
            lastdir.is_symlink()
            and (lastdir / f"{ctx.progname}.log").is_file()
            and (lastdir / "STATE" / "start.txt").is_file()
        ):
            wd = lastdir.resolve()
            step_path = lastdir / "STATE" / "STEP"
            if step_path.is_file() and step_path.stat().st_size:
                ctx.workdir = str(wd)
                ctx.launchmode = "continue"
            elif (
                not step_path.exists()
                and not (lastdir / "STATE" / "start.txt").read_text().strip()
                and not (lastdir / "STATE" / "finish.txt").exists()
            ):
                ctx.workdir = str(wd)
                ctx.launchmode = "finish"
            else:
                ctx.launchmode = "start"
        else:
            ctx.launchmode = "start"
        return

    if ctx.launchmode == "continue":
        if (
            lastdir.is_symlink()
            and (lastdir / f"{ctx.progname}.log").is_file()
            and (lastdir / "STATE" / "start.txt").is_file()
        ):
            step_path = lastdir / "STATE" / "STEP"
            start_empty = not (lastdir / "STATE" / "start.txt").read_text().strip()
            finish_staged = (lastdir / "STATE" / "finish.txt").exists()
            if step_path.is_file() and step_path.stat().st_size:
                ctx.workdir = str(lastdir.resolve())
            elif start_empty and not finish_staged:
                ctx.workdir = str(lastdir.resolve())
            else:
                ctx.usertype = "continue"
                ctx.launchmode = "start"
        else:
            ctx.usertype = "continue"
            ctx.launchmode = "start"
        return

    if ctx.launchmode == "finish":
        start = lastdir / "STATE" / "start.txt" if lastdir.is_symlink() else None
        if (
            lastdir.is_symlink()
            and (lastdir / f"{ctx.progname}.log").is_file()
            and start
            and start.is_file()
            and not start.read_text().strip()
        ):
            ctx.workdir = str(lastdir.resolve())
        elif lastdir.is_symlink() and start and start.is_file() and start.read_text().strip():
            ctx.fatal(
                "F18",
                "The first test plan is not complete yet. Use '%s --continue' to resume.",
                ctx.progname,
            )
        else:
            ctx.usertype = "finish"
            ctx.launchmode = "start"
        return

    if ctx.launchmode == "retest":
        numbers = Path(f"/var/lib/{ctx.progname}/numbers.txt")
        wd = lastdir.resolve() if lastdir.is_symlink() else None
        if (
            wd
            and (wd / f"{ctx.progname}.log").is_file()
            and numbers.is_file()
            and re.search(rf"^{re.escape(ctx.retestno)}\s", numbers.read_text(), re.M)
            and workdir_has_retest_data(wd)
            and workdir_has_retest_settings(wd)
        ):
            ctx.workdir = str(wd)
        else:
            ctx.fatal(
                "F18", "The specified test '%s' cannot be retaken at this time.", ctx.retestno
            )


def start_new_run(ctx: RuntimeContext, argv: list[str]) -> None:
    """Создать рабочий каталог, симлинк HW-TEST и первый шаг плана."""
    home = ctx.homedir or os.environ.get("HOME", "")
    lastdir = Path(home) / "HW-TEST"
    workdir = Path(
        ctx.workdir
        or (
            Path(home) / ".local/share" / ctx.progname / (ctx.repodate or date.today().isoformat())
        )
    )
    ctx.workdir = str(workdir)

    if getattr(ctx, "usertype", None):
        msg = ctx.L("L001", "The launch mode '%s' has been changed, testing will begin again!")
        print(f"{ctx.CLR_WARN}{msg % ctx.usertype}{ctx.CLR_NORM}")

    if ctx.dist_upgrade or ctx.update_kernel:
        msg = ctx.L("L002", "Before testing, the system and kernel will be updated!")
        print(f"{ctx.CLR_ERR}{msg}{ctx.CLR_NORM}")
        if not ctx.batchmode:
            step = ctx.L("L003", "Press Ctrl-C to abort or any other key to continue...")
            print(step, flush=True)
            if not read_key(abort_on_ctrl_c=True):
                ctx.fatal("F20", "Testing canceled.")
        print(flush=True)

    if workdir.exists():
        shutil.rmtree(workdir)
    if lastdir.exists() or lastdir.is_symlink():
        lastdir.unlink(missing_ok=True)
    (workdir / "STATE").mkdir(parents=True)
    lastdir.symlink_to(workdir)
    shutil.copy(f"/var/lib/{ctx.progname}/start.txt", workdir / "STATE" / "start.txt")
    first = (workdir / "STATE" / "start.txt").read_text(encoding="utf-8").splitlines()[0]
    (workdir / "STATE" / "STEP").write_text(first.split("\t")[-1] + "\n", encoding="utf-8")
    (workdir / "STATE" / "RESULTS").write_text("", encoding="utf-8")
    ctx.logfile = str(workdir / f"{ctx.progname}.log")
    ctx.xorglog = str(workdir / "xorg.log")
    title = f"{ctx.progname} {' '.join(argv)}"
    with open(ctx.logfile, "w", encoding="utf-8") as lf:
        print(f"[{time.strftime('%H:%M:%S')}] {title}", file=lf)
        Path(ctx.xorglog).write_text("", encoding="utf-8")
    step = create_step((workdir / "STATE" / "STEP").read_text().strip(), ctx)
    ctx.draw_title_line(TEST_PASSED, step.number, step.title())
    setup_resume_autorun(ctx)
    ctx.write_config()
