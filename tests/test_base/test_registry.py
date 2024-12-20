"""Test registry module."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_registry import register_service, get_service, clear_services
from tests.conftest import MockBaseService


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up registry after each test."""
    yield
    clear_services()


class TestRegistry:
    """Test service registry."""

    def test_register_service(self):
        """Test service registration."""
        service = MockBaseService()
        register_service(service)
        assert get_service(service.name) == service

    def test_register_service_with_name(self):
        """Test service registration with custom name."""
        service = MockBaseService("custom_name")
        register_service(service)
        assert get_service("custom_name") == service

    def test_get_service_by_type(self):
        """Test getting service by type."""
        service = MockBaseService()
        register_service(service)
        assert get_service(MockBaseService) == service

    def test_get_nonexistent_service(self):
        """Test getting nonexistent service."""
        with pytest.raises(ValueError) as exc:
            get_service("nonexistent")
        assert "not found" in str(exc.value)

    def test_register_duplicate_service(self):
        """Test registering duplicate service."""
        service = MockBaseService()
        register_service(service)
        with pytest.raises(ValueError) as exc:
            register_service(service)
        assert "already registered" in str(exc.value)

    def test_clear_services(self):
        """Test clearing services."""
        service = MockBaseService()
        register_service(service)
        clear_services()
        with pytest.raises(ValueError):
            get_service(service.name)

    def test_clear_services_error_handling(self, monkeypatch):
        """Test error handling in clear_services."""
        service = MockBaseService()
        register_service(service)
        
        def mock_stop(*args, **kwargs):
            raise RuntimeError("Stop error")
            
        monkeypatch.setattr(service, "stop", mock_stop)
        
        # Should not raise an exception even if service.stop fails
        clear_services()
        
        # Verify services were cleared despite the error
        with pytest.raises(ValueError):
            get_service(service.name)
