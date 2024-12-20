"""Test registry module."""

import pytest
from fastapi import status

from micro_cold_spray.api.base.base_registry import (
    register_service,
    get_service,
    clear_services,
    _services
)
from tests.test_base.conftest import TestRegistryService


@pytest.fixture(autouse=True)
async def clear_registry():
    """Clear registry before and after each test."""
    _services.clear()  # Clear directly to avoid async
    yield
    await clear_services()


@pytest.mark.asyncio
async def test_register_service():
    """Test registering a service."""
    service = TestRegistryService()
    register_service(service)
    assert get_service(TestRegistryService) == service


@pytest.mark.asyncio
async def test_register_service_with_name():
    """Test registering a service with name."""
    service = TestRegistryService(name="test")
    register_service(service)
    assert get_service("test") == service
    assert service.name == "test"


@pytest.mark.asyncio
async def test_get_service_by_type():
    """Test getting service by type."""
    service = TestRegistryService()
    register_service(service)
    assert get_service(TestRegistryService) == service


@pytest.mark.asyncio
async def test_get_nonexistent_service():
    """Test getting nonexistent service."""
    with pytest.raises(Exception) as exc:
        get_service("nonexistent")
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in str(exc.value.detail["message"])


@pytest.mark.asyncio
async def test_get_nonexistent_service_type():
    """Test getting nonexistent service type."""
    class OtherService(TestRegistryService):
        pass
        
    with pytest.raises(Exception) as exc:
        get_service(OtherService)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in str(exc.value.detail["message"])


@pytest.mark.asyncio
async def test_register_duplicate_service():
    """Test registering duplicate service."""
    service1 = TestRegistryService()
    service2 = TestRegistryService()
    
    register_service(service1)
    with pytest.raises(Exception) as exc:
        register_service(service2)
    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in str(exc.value.detail["message"])


@pytest.mark.asyncio
async def test_clear_services():
    """Test clearing services."""
    service = TestRegistryService()
    await service.start()
    register_service(service)
    
    await clear_services()
    assert not service.is_running
    
    with pytest.raises(Exception) as exc:
        get_service(TestRegistryService)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_clear_services_error_handling():
    """Test error handling when clearing services."""
    service = TestRegistryService()
    await service.start()
    register_service(service)
    
    # Mock service.stop to raise error
    async def mock_stop():
        raise ValueError("Stop error")
    
    service.stop = mock_stop
    
    with pytest.raises(Exception) as exc:
        await clear_services()
    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert "Failed to stop" in str(exc.value.detail["message"])
