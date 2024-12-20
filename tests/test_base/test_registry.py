"""Test registry module."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_registry import register_service, get_service, clear_services
from tests.conftest import MockBaseService


@pytest.fixture(autouse=True)
async def cleanup():
    """Clean up registry after each test."""
    yield
    clear_services()


class TestRegistry:
    """Test service registry."""

    @pytest.mark.asyncio
    async def test_register_service(self, base_service):
        """Test service registration."""
        register_service(base_service)
        assert get_service(base_service.name) == base_service

    @pytest.mark.asyncio
    async def test_register_service_with_name(self):
        """Test service registration with custom name."""
        service = MockBaseService("custom_name")
        register_service(service)
        assert get_service("custom_name") == service

    @pytest.mark.asyncio
    async def test_get_service_by_type(self, base_service):
        """Test getting service by type."""
        register_service(base_service)
        assert get_service(MockBaseService) == base_service

    @pytest.mark.asyncio
    async def test_get_nonexistent_service(self):
        """Test getting nonexistent service."""
        with pytest.raises(Exception) as exc:
            get_service("nonexistent")
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_register_duplicate_service(self, base_service):
        """Test registering duplicate service."""
        register_service(base_service)
        with pytest.raises(Exception) as exc:
            register_service(base_service)
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_clear_services(self, base_service):
        """Test clearing services."""
        register_service(base_service)
        clear_services()
        with pytest.raises(Exception) as exc:
            get_service(base_service.name)
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_clear_services_error_handling(self, base_service, monkeypatch):
        """Test error handling in clear_services."""
        register_service(base_service)
        
        def mock_stop(*args, **kwargs):
            raise RuntimeError("Stop error")
            
        monkeypatch.setattr(base_service, "stop", mock_stop)
        
        # Should not raise an exception even if service.stop fails
        clear_services()
        
        # Verify services were cleared despite the error
        with pytest.raises(Exception) as exc:
            get_service(base_service.name)
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
