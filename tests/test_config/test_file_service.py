"""Tests for config file service."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
import shutil

from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.config.services.file_service import ConfigFileService
from .helpers import (
    get_test_data_dir,
    get_test_backup_dir,
    load_test_config,
    create_test_config_data
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def file_service(temp_config_dir):
    """Create file service instance."""
    return ConfigFileService(temp_config_dir)


@pytest.mark.asyncio
async def test_service_start(file_service):
    """Test service startup."""
    await file_service.start()
    assert file_service.is_running
    assert file_service._config_dir.exists()


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    mock_path = MagicMock(spec=Path)
    mock_path.mkdir.side_effect = Exception("Failed to create directory")
    service = ConfigFileService(mock_path)
    
    with pytest.raises(ConfigurationError, match="Failed to start file service"):
        await service.start()


@pytest.mark.asyncio
async def test_load_config_missing(file_service):
    """Test loading non-existent config."""
    await file_service.start()
    
    with pytest.raises(ConfigurationError, match="Config file not found"):
        await file_service.load_config("nonexistent")


@pytest.mark.asyncio
async def test_load_config_invalid_yaml(file_service, temp_config_dir):
    """Test loading invalid YAML config."""
    await file_service.start()
    
    config_path = temp_config_dir / "test.yaml"
    config_path.write_text("invalid: yaml: content: {")
    
    with pytest.raises(ConfigurationError, match="Failed to load config"):
        await file_service.load_config("test")


@pytest.mark.asyncio
async def test_load_config_success(file_service, temp_config_dir):
    """Test loading valid config."""
    await file_service.start()
    
    # Copy test config to temp directory
    test_config = load_test_config("test_config")
    config_path = temp_config_dir / "test_config.yaml"
    with open(config_path, "w") as f:
        shutil.copy2(get_test_data_dir() / "test_config.yaml", config_path)
    
    config_data = await file_service.load_config("test_config")
    assert config_data.metadata.config_type == "test_config"
    assert config_data.data == test_config


@pytest.mark.asyncio
async def test_save_config(file_service):
    """Test saving configuration."""
    await file_service.start()
    
    # Create test config data
    config_data = create_test_config_data("test_config")
    
    # Save config
    await file_service.save_config(config_data)
    
    # Verify file was created
    config_path = file_service._config_dir / "test_config.yaml"
    assert config_path.exists()
    
    # Verify content
    with open(config_path) as f:
        saved_data = load_test_config("test_config")
        assert saved_data == config_data.data


@pytest.mark.asyncio
async def test_save_config_with_backup(file_service):
    """Test saving configuration with backup."""
    await file_service.start()
    
    # Create initial config
    config_data = create_test_config_data("test_config")
    await file_service.save_config(config_data)
    
    # Update config
    updated_data = config_data.data.copy()
    updated_data["test_service"]["version"] = "2.0.0"
    updated_config = create_test_config_data("test_config", updated_data)
    
    # Save updated config
    await file_service.save_config(updated_config)
    
    # Verify backup was created
    backup_path = file_service._get_backup_path("test_config")
    assert backup_path.exists()
    
    # Verify backup content
    with open(backup_path) as f:
        backup_data = load_test_config("test_config")
        assert backup_data == config_data.data


@pytest.mark.asyncio
async def test_config_exists(file_service):
    """Test checking config existence."""
    await file_service.start()
    
    # Create test config
    config_data = create_test_config_data("test_config")
    await file_service.save_config(config_data)
    
    # Check existence
    assert await file_service.config_exists("test_config")
    assert not await file_service.config_exists("nonexistent")


@pytest.mark.asyncio
async def test_create_backup(file_service):
    """Test creating config backup."""
    await file_service.start()
    
    # Create test config
    config_data = create_test_config_data("test_config")
    await file_service.save_config(config_data)
    
    # Create backup
    await file_service.create_backup("test_config")
    
    # Verify backup
    backup_path = file_service._get_backup_path("test_config")
    assert backup_path.exists()
    
    # Verify backup content
    with open(backup_path) as f:
        backup_data = load_test_config("test_config")
        assert backup_data == config_data.data


@pytest.mark.asyncio
async def test_create_backup_missing_config(file_service):
    """Test creating backup for non-existent config."""
    await file_service.start()
    
    with pytest.raises(ConfigurationError, match="Config file not found"):
        await file_service.create_backup("nonexistent")
