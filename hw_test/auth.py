"""Authentication module for hw-test.

Provides root authentication via 'su -' with password prompt.
Uses pexpect for interactive password input if available, falls back to subprocess.
"""

from __future__ import annotations

import getpass
import os
import sys
import subprocess
from typing import Optional, Tuple

try:
    import pexpect

    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False


class RootAuthenticator:
    """Handles root authentication via su -."""

    def __init__(self):
        self._authenticated = False
        self._password: Optional[str] = None

    def authenticate(self, max_attempts: int = 3) -> bool:
        """
        Authenticate as root using su -.

        Args:
            max_attempts: Maximum number of password attempts

        Returns:
            True if authentication succeeded, False otherwise
        """
        if self._authenticated:
            return True

        print("=" * 60)
        print("АУТЕНТИФИКАЦИЯ ROOT")
        print("=" * 60)
        print("Требуется аутентификация root для выполнения тестов оборудования.")
        print("Будет использован 'su -' для выполнения привилегированных команд.")
        print("Пароль будет запрошен один раз и использован для всех команд.\n")

        for attempt in range(1, max_attempts + 1):
            try:
                password = getpass.getpass(
                    f"Попытка {attempt}/{max_attempts}. Введите пароль root: "
                )
            except (EOFError, KeyboardInterrupt):
                print("\n✗ Аутентификация отменена пользователем.")
                return False

            if not password:
                print("✗ Пароль не может быть пустым.\n")
                continue

            if self._verify_password(password):
                self._authenticated = True
                self._password = password
                print("\n✓ Аутентификация успешна.\n")
                return True
            else:
                print("✗ Неверный пароль.\n")

        print("✗ Превышено максимальное количество попыток.")
        return False

    def _verify_password(self, password: str) -> bool:
        """Verify password by running a simple command as root."""
        if HAS_PEXPECT:
            try:
                child = pexpect.spawn("su - -c 'echo ROOT_AUTH_OK'", timeout=10, encoding="utf-8")
                child.expect(".*assword:")
                child.sendline(password)
                child.expect(pexpect.EOF)
                child.close()
                return child.exitstatus == 0 and "ROOT_AUTH_OK" in child.before
            except Exception:
                pass

        # Fallback to subprocess
        try:
            result = subprocess.run(
                ["su", "-", "-c", "echo ROOT_AUTH_OK"],
                input=password + "\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "ROOT_AUTH_OK" in result.stdout
        except Exception:
            return False

    def run_command(self, cmd: list, timeout: int = 300) -> Tuple[str, str, int]:
        """
        Run command as root using su -.

        Args:
            cmd: Command and arguments as list
            timeout: Command timeout in seconds

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        if not self._authenticated:
            return "", "Not authenticated", -1

        password = self._password
        if password is None:
            if not self.authenticate():
                return "", "Authentication required", -1
            password = self._password

        full_cmd = " ".join(cmd)

        if HAS_PEXPECT:
            try:
                child = pexpect.spawn(f"su - -c '{full_cmd}'", timeout=timeout, encoding="utf-8")
                child.expect(".*assword:")
                child.sendline(password)
                child.expect(pexpect.EOF)
                child.close()

                output = child.before
                if child.exitstatus == 0:
                    return output, "", child.exitstatus
                else:
                    return "", output, child.exitstatus
            except pexpect.TIMEOUT:
                try:
                    child.close()
                except:
                    pass
                return "", "Command timed out", -1
            except Exception as e:
                return "", str(e), -1

        # Fallback to subprocess
        try:
            result = subprocess.run(
                ["su", "-", "-c", full_cmd],
                input=password + "\n",
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1
        except Exception as e:
            return "", str(e), -1

    def is_authenticated(self) -> bool:
        """Check if currently authenticated as root."""
        return self._authenticated

    def logout(self):
        """Clear cached credentials."""
        self._authenticated = False
        if self._password:
            self._password = None


# Global authenticator instance
_authenticator: Optional[RootAuthenticator] = None


def get_authenticator() -> RootAuthenticator:
    """Get or create the global authenticator instance."""
    global _authenticator
    if _authenticator is None:
        _authenticator = RootAuthenticator()
    return _authenticator


def authenticate_root() -> bool:
    """Authenticate as root. Returns True if successful."""
    return get_authenticator().authenticate()


def run_as_root(cmd: list, timeout: int = 300) -> Tuple[str, str, int]:
    """Run command as root using 'su -'. Requires prior authentication."""
    return get_authenticator().run_command(cmd, timeout)


def is_root_authenticated() -> bool:
    """Check if root is authenticated."""
    return get_authenticator().is_authenticated()
