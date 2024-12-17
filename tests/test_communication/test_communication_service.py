"""Tests for communication service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.communication.clients import PLCClient, SSHClient


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    config_service = AsyncMock(spec=ConfigService)
    config_service.get_config.return_value = MagicMock(
        data={
            "network": {
                "plc": {
                    "host": "192.168.1.100",
                    "port": 44818
                },
                "ssh": {
                    "host": "192.168.1.200",
                    "username": "admin",
                    "password": "secret"
                }
            }
        }
    )
    return config_service


@pytest.fixture
def mock_plc_client():
    """Create mock PLC client."""
    with patch('micro_cold_spray.api.communication.service.create_plc_client') as mock_create:
        client = AsyncMock(spec=PLCClient)
        client.check_connection = AsyncMock(return_value=True)
        mock_create.return_value = client
        yield client


@pytest.fixture
def mock_ssh_client():
    """Create mock SSH client."""
    with patch('micro_cold_spray.api.communication.service.create_ssh_client') as mock_create:
        client = AsyncMock(spec=SSHClient)
        client.check_connection = AsyncMock(return_value=True)
        mock_create.return_value = client
        yield client


@pytest.fixture
def mock_services():
    """Create mock service instances."""
    with patch('micro_cold_spray.api.communication.service.EquipmentService') as mock_equipment, \
         patch('micro_cold_spray.api.communication.service.FeederService') as mock_feeder, \
         patch('micro_cold_spray.api.communication.service.MotionService') as mock_motion, \
         patch('micro_cold_spray.api.communication.service.TagCacheService') as mock_tag_cache, \
         patch('micro_cold_spray.api.communication.service.TagMappingService') as mock_tag_mapping:
        
        # Create mock instances
        equipment = AsyncMock()
        feeder = AsyncMock()
        motion = AsyncMock()
        tag_cache = AsyncMock()
        tag_mapping = AsyncMock()
        
        # Configure is_running properties
        equipment.is_running = True
        feeder.is_running = True
        motion.is_running = True
        tag_cache.is_running = True
        tag_mapping.is_running = True
        
        # Configure constructors
        mock_equipment.return_value = equipment
        mock_feeder.return_value = feeder
        mock_motion.return_value = motion
        mock_tag_cache.return_value = tag_cache
        mock_tag_mapping.return_value = tag_mapping
        
        yield {
            'equipment': equipment,
            'feeder': feeder,
            'motion': motion,
            'tag_cache': tag_cache,
            'tag_mapping': tag_mapping
        }


class TestCommunicationService:
    """Test communication service functionality."""

    def test_initialization(self, mock_config_service):
        """Test service initialization."""
        service = CommunicationService(mock_config_service)
        assert service._config_service == mock_config_service
        assert service._plc_client is None
        assert service._ssh_client is None
        assert service._equipment is None
        assert service._feeder is None
        assert service._motion is None
        assert service._tag_cache is None
        assert service._tag_mapping is None

    @pytest.mark.asyncio
    async def test_start_success(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test successful service start."""
        service = CommunicationService(mock_config_service)
        await service.start()

        # Verify config loaded
        mock_config_service.get_config.assert_called_once_with("hardware")

        # Verify clients initialized
        assert service._plc_client == mock_plc_client
        assert service._ssh_client == mock_ssh_client
        mock_plc_client.connect.assert_called_once()
        mock_ssh_client.connect.assert_called_once()

        # Verify services started
        for mock_service in mock_services.values():
            mock_service.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_empty_config(self, mock_config_service):
        """Test start with empty config."""
        mock_config_service.get_config.return_value = MagicMock(data=None)
        service = CommunicationService(mock_config_service)

        with pytest.raises(ValidationError) as exc_info:
            await service.start()
        assert "Hardware configuration is empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_plc_client_fallback(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test PLC client fallback to mock."""
        mock_plc_client.connect.side_effect = Exception("Connection failed")
        service = CommunicationService(mock_config_service)
        await service.start()

        # Should create mock client after failure
        assert mock_plc_client.connect.call_count == 1
        assert service._plc_client is not None

    @pytest.mark.asyncio
    async def test_ssh_client_fallback(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test SSH client fallback to mock."""
        mock_ssh_client.connect.side_effect = Exception("Connection failed")
        service = CommunicationService(mock_config_service)
        await service.start()

        # Should create mock client after failure
        assert mock_ssh_client.connect.call_count == 1
        assert service._ssh_client is not None

    @pytest.mark.asyncio
    async def test_stop_success(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test successful service stop."""
        service = CommunicationService(mock_config_service)
        await service.start()
        await service.stop()

        # Verify services stopped in reverse order
        mock_services['tag_mapping'].stop.assert_called_once()
        mock_services['tag_cache'].stop.assert_called_once()
        mock_services['motion'].stop.assert_called_once()
        mock_services['feeder'].stop.assert_called_once()
        mock_services['equipment'].stop.assert_called_once()

        # Verify clients stopped
        mock_ssh_client.stop.assert_called_once()
        mock_plc_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test health check when all components healthy."""
        service = CommunicationService(mock_config_service)
        await service.start()

        health = await service.check_health()
        assert health["status"] == "healthy"
        assert all(health["components"].values())

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test health check when some components unhealthy."""
        mock_plc_client.check_connection.return_value = False
        mock_services['equipment'].is_running = False

        service = CommunicationService(mock_config_service)
        await service.start()

        health = await service.check_health()
        assert health["status"] == "degraded"
        assert not health["components"]["plc"]
        assert not health["components"]["equipment"]

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test health check failure."""
        mock_plc_client.check_connection.side_effect = Exception("Check failed")

        service = CommunicationService(mock_config_service)
        await service.start()

        with pytest.raises(ServiceError) as exc_info:
            await service.check_health()
        assert "Failed to check communication health" in str(exc_info.value)

    def test_service_properties(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test service property access."""
        service = CommunicationService(mock_config_service)

        # Properties should raise before initialization
        with pytest.raises(RuntimeError):
            _ = service.equipment
        with pytest.raises(RuntimeError):
            _ = service.feeder
        with pytest.raises(RuntimeError):
            _ = service.motion
        with pytest.raises(RuntimeError):
            _ = service.tag_cache
        with pytest.raises(RuntimeError):
            _ = service.tag_mapping

    @pytest.mark.asyncio
    async def test_service_properties_after_init(self, mock_config_service, mock_plc_client, mock_ssh_client, mock_services):
        """Test service property access after initialization."""
        service = CommunicationService(mock_config_service)
        await service.start()

        # Properties should return the correct services
        assert service.equipment == mock_services['equipment']
        assert service.feeder == mock_services['feeder']
        assert service.motion == mock_services['motion']
        assert service.tag_cache == mock_services['tag_cache']
        assert service.tag_mapping == mock_services['tag_mapping']
