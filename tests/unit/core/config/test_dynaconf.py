"""Unit tests for Dynaconf configuration functionality."""

import pytest
import os
from pathlib import Path
from dynaconf import Dynaconf
from tests.base import BaseConfigTest


@pytest.mark.unit
@pytest.mark.dynaconf
class TestDynaconf(BaseConfigTest):
    """Test Dynaconf configuration functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Dynaconf(
            envvar_prefix="MICROCOLDSPRAY",
            settings_files=["settings.yaml", ".secrets.yaml"],
            environments=True,
            env="test"
        )

    def test_dynaconf_loading(self, config):
        """Test Dynaconf configuration loading."""
        self.assert_config_loaded(config)
        assert isinstance(config, Dynaconf)

    def test_dynaconf_environment(self, config):
        """Test Dynaconf environment handling."""
        self.assert_config_value(config, "current_env", "test")
        assert config.current_env == "test"

    def test_dynaconf_env_vars(self, config):
        """Test Dynaconf environment variable handling."""
        os.environ["MICROCOLDSPRAY_TEST_VAR"] = "test_value"
        config.reload()
        assert config.get("test_var") == "test_value"
        del os.environ["MICROCOLDSPRAY_TEST_VAR"]

    def test_dynaconf_nested_settings(self, config):
        """Test Dynaconf nested settings access."""
        config.set("parent.child.value", 123)
        assert config.parent.child.value == 123
        assert config["parent"]["child"]["value"] == 123

    def test_dynaconf_type_casting(self, config):
        """Test Dynaconf type casting."""
        os.environ["MICROCOLDSPRAY_INT_VAR"] = "42"
        os.environ["MICROCOLDSPRAY_BOOL_VAR"] = "true"
        os.environ["MICROCOLDSPRAY_LIST_VAR"] = '["a", "b", "c"]'
        config.reload()
        
        assert isinstance(config.int_var, int)
        assert isinstance(config.bool_var, bool)
        assert isinstance(config.list_var, list)
        
        del os.environ["MICROCOLDSPRAY_INT_VAR"]
        del os.environ["MICROCOLDSPRAY_BOOL_VAR"]
        del os.environ["MICROCOLDSPRAY_LIST_VAR"]

    def test_dynaconf_validators(self, config):
        """Test Dynaconf validation rules."""
        from dynaconf.validator import Validator

        config.validators.register(
            Validator("database.port", must_exist=True, is_type_of=int),
            Validator("database.host", must_exist=True, is_type_of=str)
        )
        
        config.set("database.port", 5432)
        config.set("database.host", "localhost")
        
        assert config.validators.validate() is True

    def test_dynaconf_secrets(self, config):
        """Test Dynaconf secrets handling."""
        if Path(".secrets.yaml").exists():
            # Test that secrets are loaded but not exposed in __str__
            assert "api_key" not in str(config)
            # Test that secrets can be accessed normally
            if hasattr(config, "api_key"):
                assert isinstance(config.api_key, str)

    def test_dynaconf_merge(self, config):
        """Test Dynaconf settings merging."""
        default_settings = {
            "app": {
                "name": "test",
                "version": "1.0.0"
            }
        }
        config.update(default_settings)
        
        override_settings = {
            "app": {
                "version": "1.0.1"
            }
        }
        config.update(override_settings)
        
        assert config.app.name == "test"
        assert config.app.version == "1.0.1"

    def test_dynaconf_environments(self, config):
        """Test Dynaconf environment switching."""
        # Test environment-specific settings
        config.set("key", "default_value")
        config.set("key", "test_value", env="test")
        config.set("key", "prod_value", env="production")
        
        assert config.key == "test_value"  # We're in test env
        
        # Switch environment
        with config.using_env("production"):
            assert config.key == "prod_value"
