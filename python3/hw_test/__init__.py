"""hw-test — автоматизация тестирования совместимости оборудования ALT Linux.

Пакет устанавливается в site-packages; данные — в /var/lib/hw-test и libexec.
Руководство разработчика: hw_test/README.md
"""

from hw_test.constants import (
    TEST_ALLOWED,
    TEST_BLOCKED,
    TEST_FAILED,
    TEST_PASSED,
    TEST_RUNNING,
    TEST_SKIPPED,
)

__all__ = [
    "TEST_ALLOWED",
    "TEST_BLOCKED",
    "TEST_FAILED",
    "TEST_PASSED",
    "TEST_RUNNING",
    "TEST_SKIPPED",
]
