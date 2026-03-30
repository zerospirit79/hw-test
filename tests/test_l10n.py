"""Tests for localization module."""

import pytest
from hw_test.l10n import Localization, get_l10n, _, set_language


class TestLocalization:
    """Test localization functionality."""

    def test_init_default(self):
        """Test default initialization."""
        l10n = Localization()
        assert l10n.lang_id in ["en", "ru"]

    def test_init_russian(self):
        """Test Russian initialization."""
        l10n = Localization("ru")
        assert l10n.lang_id == "ru"
        assert l10n.is_russian

    def test_init_english(self):
        """Test English initialization."""
        l10n = Localization("en")
        assert l10n.lang_id == "en"
        assert l10n.is_english

    def test_get_message_russian(self):
        """Test getting Russian messages."""
        l10n = Localization("ru")
        assert l10n.get("auth_title") == "АУТЕНТИФИКАЦИЯ ROOT"
        assert l10n.get("step_prepare") == "Подготовка системы"

    def test_get_message_english(self):
        """Test getting English messages."""
        l10n = Localization("en")
        assert l10n.get("auth_title") == "ROOT AUTHENTICATION"
        assert l10n.get("step_prepare") == "System Preparation"

    def test_get_unknown_key(self):
        """Test getting unknown key."""
        l10n = Localization("ru")
        assert l10n.get("unknown_key") == ""
        assert l10n.get("unknown_key", "default") == "default"

    def test_shorthand(self):
        """Test shorthand method."""
        l10n = Localization("ru")
        assert l10n._("testing_complete") == "Тестирование завершено!"

    def test_set_language(self):
        """Test changing language."""
        l10n = Localization("en")
        assert l10n.is_english
        l10n.set_language("ru")
        assert l10n.is_russian

    def test_global_instance(self):
        """Test global localization instance."""
        l10n = get_l10n()
        assert isinstance(l10n, Localization)

    def test_global_set_language(self):
        """Test global set_language function."""
        set_language("ru")
        assert _("program_name") == "HW-Test"


class TestLocalizationDetect:
    """Test locale detection."""

    def test_detect_ru_locale(self, monkeypatch):
        """Test Russian locale detection."""
        monkeypatch.setenv("LANG", "ru_RU.UTF-8")
        l10n = Localization()
        assert l10n.lang_id == "ru"

    def test_detect_en_locale(self, monkeypatch):
        """Test English locale detection."""
        monkeypatch.setenv("LANG", "en_US.UTF-8")
        l10n = Localization()
        assert l10n.lang_id == "en"

    def test_detect_unknown_locale(self, monkeypatch):
        """Test unknown locale defaults to Russian."""
        monkeypatch.setenv("LANG", "fr_FR.UTF-8")
        l10n = Localization()
        assert l10n.lang_id == "ru"

    def test_detect_no_locale(self, monkeypatch):
        """Test no locale defaults to Russian."""
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.delenv("LC_MESSAGES", raising=False)
        l10n = Localization()
        assert l10n.lang_id == "ru"
