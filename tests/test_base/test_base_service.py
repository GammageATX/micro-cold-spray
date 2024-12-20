"""Test base service module."""

import pytest
from fastapi import status

from tests.conftest import MockBaseService


@pytest.fixture
def service():
    """Create test service."""
    return MockBaseService()


class TestBaseService:
    """Test base service."""

    @pytest.mark.asyncio
    async def test_service_start(self, service):
        """Test service start."""
        await service.start()
        assert service.is_running

    @pytest.mark.asyncio
    async def test_service_stop(self, service):
        """Test service stop."""
        await service.start()
        await service.stop()
        assert not service.is_running

    @pytest.mark.asyncio
    async def test_service_health(self, service):
        """Test service health check."""
        await service.start()
        health = await service.health()
        assert health["is_healthy"] is True
        assert health["status"] == "running"
        assert health["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_service_health_not_running(self, service):
        """Test health check when service is not running."""
        health = await service.health()
        assert health["is_healthy"] is False
        assert health["status"] == "stopped"
        assert health["context"]["service"] == service.name

    @pytest.mark.asyncio
    async def test_start_already_running(self, service):
        """Test starting already running service."""
        await service.start()
        with pytest.raises(ValueError) as exc:
            await service.start()
        assert "already running" in str(exc.value)

    @pytest.mark.asyncio
    async def test_stop_not_running(self, service):
        """Test stopping not running service."""
        with pytest.raises(ValueError) as exc:
            await service.stop()
        assert "not running" in str(exc.value)

    def test_service_name(self):
        """Test service name."""
        service = MockBaseService("custom_name")
        assert service.name == "custom_name"

        service = MockBaseService()
        assert service.name == "test_service"
