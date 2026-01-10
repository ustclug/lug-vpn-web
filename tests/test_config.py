"""
Tests for app.config module.
"""

import os
import pytest


class TestConfigHelpers:
    """Test configuration helper functions."""

    def test_get_bool_true_values(self):
        """Test boolean parsing for true values."""
        from app.config import _get_bool
        
        for val in ("1", "true", "yes", "on", "True", "YES", "ON"):
            os.environ["TEST_BOOL"] = val
            assert _get_bool("TEST_BOOL", False) is True
        
        if "TEST_BOOL" in os.environ:
            del os.environ["TEST_BOOL"]

    def test_get_bool_false_values(self):
        """Test boolean parsing for false values."""
        from app.config import _get_bool
        
        for val in ("0", "false", "no", "off", "False", "NO", "OFF"):
            os.environ["TEST_BOOL"] = val
            assert _get_bool("TEST_BOOL", True) is False
        
        if "TEST_BOOL" in os.environ:
            del os.environ["TEST_BOOL"]

    def test_get_bool_default(self):
        """Test boolean parsing falls back to default."""
        from app.config import _get_bool
        
        # Ensure env var is not set
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]
        
        assert _get_bool("NONEXISTENT_VAR", True) is True
        assert _get_bool("NONEXISTENT_VAR", False) is False

    def test_get_int_valid(self):
        """Test integer parsing."""
        from app.config import _get_int
        
        os.environ["TEST_INT"] = "42"
        assert _get_int("TEST_INT", 0) == 42
        
        del os.environ["TEST_INT"]

    def test_get_int_default(self):
        """Test integer parsing falls back to default."""
        from app.config import _get_int
        
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]
        
        assert _get_int("NONEXISTENT_VAR", 100) == 100

    def test_get_int_invalid(self):
        """Test integer parsing with invalid value falls back to default."""
        from app.config import _get_int
        
        os.environ["TEST_INT"] = "not-a-number"
        assert _get_int("TEST_INT", 50) == 50
        
        del os.environ["TEST_INT"]


class TestConfig:
    """Test Config class attributes."""

    def test_config_has_required_attributes(self):
        """Test that Config has all required Flask attributes."""
        from app.config import Config
        
        assert hasattr(Config, "SQLALCHEMY_DATABASE_URI")
        assert hasattr(Config, "SECRET_KEY")
        assert hasattr(Config, "DEBUG")
        assert hasattr(Config, "MAIL_ENABLE")

    def test_config_sqlalchemy_track_modifications_false(self):
        """Test that SQLALCHEMY_TRACK_MODIFICATIONS is False."""
        from app.config import Config
        
        assert Config.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_config_bootstrap_serve_local_true(self):
        """Test that BOOTSTRAP_SERVE_LOCAL is True."""
        from app.config import Config
        
        assert Config.BOOTSTRAP_SERVE_LOCAL is True
