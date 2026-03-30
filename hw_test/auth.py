"""Authentication module for hw-test.

Provides root authentication via 'su -' with password prompt.
Uses a helper script for secure password handling.
"""

import getpass
import subprocess
import os
import sys
import tempfile
import stat
from typing import Optional, Tuple


# Helper script for running commands as root
# This avoids passing password on command line
SU_HELPER_SCRIPT = """
#!/bin/bash
# Read password from file descriptor 3 and run command
read -r -u 3 PASSWORD
exec su - -c "$*" bash <&3 2>&1
"""


class RootAuthenticator:
    """Handles root authentication via su -."""

    def __init__(self):
        self._authenticated = False
        self._password: Optional[str] = None
        self._use_expect = True  # Try using pexpect-style input first

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
                password = getpass.getpass(f"Попытка {attempt}/{max_attempts}. Введите пароль root: ")
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
        try:
            # Try using su - with password via stdin
            result = subprocess.run(
                ['su', '-', '-c', 'echo ROOT_AUTH_OK'],
                input=password + '\n',
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and 'ROOT_AUTH_OK' in result.stdout
        except Exception as e:
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
            # Password not cached, request it
            if not self.authenticate():
                return "", "Authentication required", -1
            password = self._password

        try:
            # Use su - with password via stdin
            # The '-' ensures we get a login shell with full environment
            full_cmd = ' '.join(cmd)
            result = subprocess.run(
                ['su', '-', '-c', full_cmd],
                input=password + '\n',
                capture_output=True,
                text=True,
                timeout=timeout
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
            # Clear password from memory
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
