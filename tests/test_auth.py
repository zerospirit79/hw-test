"""Tests for authentication module."""

import pytest
from unittest.mock import patch, MagicMock
from hw_test.auth import RootAuthenticator, get_authenticator, authenticate_root, HAS_PEXPECT


class TestRootAuthenticator:
    """Test RootAuthenticator class."""

    @pytest.fixture
    def authenticator(self):
        """Create authenticator instance."""
        return RootAuthenticator()

    def test_init(self, authenticator):
        """Test initialization."""
        assert authenticator._authenticated is False
        assert authenticator._password is None

    def test_is_authenticated_initial(self, authenticator):
        """Test initial authentication state."""
        assert authenticator.is_authenticated() is False

    def test_logout(self, authenticator):
        """Test logout clears credentials."""
        authenticator._authenticated = True
        authenticator._password = "secret"

        authenticator.logout()

        assert authenticator._authenticated is False
        assert authenticator._password is None

    @patch("hw_test.auth.HAS_PEXPECT", False)
    @patch("hw_test.auth.subprocess.run")
    def test_verify_password_success(self, mock_run, authenticator):
        """Test password verification success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ROOT_AUTH_OK")

        result = authenticator._verify_password("correct_password")
        assert result is True

    @patch("hw_test.auth.HAS_PEXPECT", False)
    @patch("hw_test.auth.subprocess.run")
    def test_verify_password_failure(self, mock_run, authenticator):
        """Test password verification failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Authentication failure")

        result = authenticator._verify_password("wrong_password")
        assert result is False

    @patch("hw_test.auth.HAS_PEXPECT", False)
    @patch("hw_test.auth.getpass.getpass")
    @patch("hw_test.auth.subprocess.run")
    def test_authenticate_success(self, mock_run, mock_getpass, authenticator):
        """Test successful authentication."""
        mock_getpass.return_value = "correct_password"
        mock_run.return_value = MagicMock(returncode=0, stdout="ROOT_AUTH_OK")

        result = authenticator.authenticate(max_attempts=1)

        assert result is True
        assert authenticator.is_authenticated() is True

    @patch("hw_test.auth.HAS_PEXPECT", False)
    @patch("hw_test.auth.getpass.getpass")
    @patch("hw_test.auth.subprocess.run")
    def test_authenticate_wrong_password(self, mock_run, mock_getpass, authenticator):
        """Test authentication with wrong password."""
        mock_getpass.return_value = "wrong_password"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Authentication failure")

        result = authenticator.authenticate(max_attempts=1)

        assert result is False

    @patch("hw_test.auth.getpass.getpass")
    def test_authenticate_cancelled(self, mock_getpass, authenticator):
        """Test authentication cancelled by user."""
        mock_getpass.side_effect = EOFError()

        result = authenticator.authenticate()

        assert result is False

    @patch("hw_test.auth.HAS_PEXPECT", False)
    @patch("hw_test.auth.subprocess.run")
    def test_run_command_authenticated(self, mock_run, authenticator):
        """Test running command after authentication."""
        authenticator._authenticated = True
        authenticator._password = "secret"

        mock_run.return_value = MagicMock(returncode=0, stdout="command output", stderr="")

        stdout, stderr, rc = authenticator.run_command(["ls", "-la"])

        assert stdout == "command output"
        assert stderr == ""
        assert rc == 0

    def test_run_command_not_authenticated(self, authenticator):
        """Test running command without authentication."""
        stdout, stderr, rc = authenticator.run_command(["ls", "-la"])

        assert stdout == ""
        assert stderr == "Not authenticated"
        assert rc == -1


class TestGlobalFunctions:
    """Test global authentication functions."""

    @patch("hw_test.auth.RootAuthenticator")
    def test_get_authenticator(self, mock_class):
        """Test getting authenticator."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        result = get_authenticator()

        assert result is mock_instance

    @patch("hw_test.auth.RootAuthenticator")
    def test_get_authenticator_singleton(self, mock_class):
        """Test that get_authenticator returns same instance."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        result1 = get_authenticator()
        result2 = get_authenticator()

        assert result1 is result2

    @patch("hw_test.auth.get_authenticator")
    def test_authenticate_root(self, mock_get_auth):
        """Test authenticate_root function."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = True
        mock_get_auth.return_value = mock_auth

        result = authenticate_root()

        assert result is True
        mock_auth.authenticate.assert_called_once()
