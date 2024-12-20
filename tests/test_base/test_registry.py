"""Test registry module."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_registry import register_service, get_service, clear_services
from micro_cold_spray.api.base.base_service import BaseService


class TestService(BaseService):
    """Test service implementation."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


@pytest.fixture(autouse=True)
async def cleanup():
    """Clean up registry after each test."""
    yield
    await clear_services()


class TestRegistry:
    """Test service registry."""

    @pytest.mark.asyncio
    async def test_register_service(self):
        """Test service registration."""
        service = TestService()
        register_service(service)
        assert get_service(service.name) == service

    @pytest.mark.asyncio
    async def test_register_service_with_name(self):
        """Test service registration with custom name."""
        service = TestService("custom_name")
        register_service(service)
        assert get_service("custom_name") == service

    @pytest.mark.asyncio
    async def test_get_service_by_type(self):
        """Test getting service by type."""
        service = TestService()
        register_service(service)
        assert get_service(TestService) == service

    @pytest.mark.asyncio
    async def test_get_nonexistent_service(self):
        """Test getting nonexistent service."""
        with pytest.raises(Exception) as exc:
            get_service("nonexistent")
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_get_nonexistent_service_type(self):
        """Test getting nonexistent service type."""
        class OtherService(BaseService):
            pass

        service = TestService()
        register_service(service)
        with pytest.raises(Exception) as exc:
            get_service(OtherService)
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service_type"] == "OtherService"

    @pytest.mark.asyncio
    async def test_register_duplicate_service(self):
        """Test registering duplicate service."""
        service = TestService()
        register_service(service)
        with pytest.raises(Exception) as exc:
            register_service(service)
        assert exc.value.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in str(exc.value.detail["message"])
        assert exc.value.detail["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_clear_services(self):
        """Test clearing services."""
        service = TestService()
        await service.start()
        register_service(service)
        
        await clear_services()
        assert service.is_running is False
        
        with pytest.raises(Exception) as exc:
            get_service(service.name)
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_clear_services_error_handling(self, monkeypatch):
        """Test error handling in clear_services."""
        service = TestService()
        await service.start()
        register_service(service)
        
        def mock_stop(*args, **kwargs):
            raise RuntimeError("Stop error")
            
        monkeypatch.setattr(service, "stop", mock_stop)
        
        # Should not raise an exception even if service.stop fails
        await clear_services()
        
        # Verify services were cleared despite the error
        with pytest.raises(Exception) as exc:
            get_service(service.name)
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
