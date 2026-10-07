"""Реестр шагов — импорт модулей регистрирует их в REGISTRY.

Порядок в плане (var/lib/hw-test/start.txt), не порядок импорта:
  prepare (5.1) → upgrade → detect (5.3) → config (5.4) → install →
  fwupd → syslogs (7) → collect (8) → express (9) → cpupower (10.1) →
  network (10.2) → numa (10.8) → ipmi (10.9) → sound (10.4) → webcam (10.10.3) →
  bluez (10.10.10) → fprnt (10.10.7) → scard (10.10.12) → power (10.6.2)

Финальная фаза (finish.txt): diskperf (11.1) → glmark (11.2) → finalize (10.11)
"""

# Импорт с побочным эффектом: @register_step заполняет REGISTRY
from hw_test.steps import (  # noqa: F401
    collect,
    config,
    cpupower,
    detect,
    diskperf,
    express,
    finalize,
    fwupd,
    glmark,
    install,
    ipmi,
    network,
    numa,
    peripherals,
    power,
    prepare,
    syslogs,
    upgrade,
)
from hw_test.steps.base import REGISTRY, create_step, get_step_class, list_steps, register_step

__all__ = [
    "REGISTRY",
    "create_step",
    "get_step_class",
    "list_steps",
    "register_step",
]
