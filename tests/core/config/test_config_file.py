"""Tests for file service."""

import pytest
import shutil
from fastapi import status, HTTPException

from micro_cold_spray.api.config.services.file_service import ConfigFileService
from .helpers import (
    create_test_config,
    get_config_dir,
    load_yaml_file
)


@pytest.fixture
def test_data():
    """Create test config data."""
    return {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }


@pytest.fixture
def file_service(tmp_path):
    """Create a file service instance for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    
    # Copy real config file for testing from root config directory
    real_config = get_config_dir() / "application.yaml"
    test_config = config_dir / "application.yaml"
    shutil.copy2(real_config, test_config)
    
    service = ConfigFileService(config_dir, backup_dir)
    service.backup_enabled = True
    return service


@pytest.fixture
def config_dir(tmp_path):
    """Create and return a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.mark.asyncio
async def test_service_start(file_service):
    """Test service startup."""
    await file_service.start()
    assert file_service.is_running
    
    # Check health
    health = await file_service._check_health()
    assert "config_dir" in health
    assert "backup_dir" in health
    assert "config_files" in health
    assert "backup_files" in health


@pytest.mark.asyncio
async def test_service_start_error(tmp_path):
    """Test service startup with error."""
    # Create a file where the config directory should be
    config_dir = tmp_path / "config"
    config_dir.touch()  # This will make mkdir fail
    
    service = ConfigFileService(config_dir)
    with pytest.raises(HTTPException) as exc_info:
        await service.start()
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Failed to start file service" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_backup(file_service, tmp_path, test_data):
    """Test creating a backup of a config file."""
    await file_service.start()
    
    # Create test config file
    _ = create_test_config(
        tmp_path / "config",
        "test_backup_create",
        test_data
    )
    
    # Create backup
    await file_service.create_backup("test_backup_create")
    
    # Verify backup was created
    backup_files = list(file_service._backup_dir.glob("test_backup_create_*.bak"))
    assert len(backup_files) > 0
    
    # Verify backup content
    backup_data = load_yaml_file(backup_files[0])
    assert backup_data == test_data


@pytest.mark.asyncio
async def test_create_backup_missing_file(file_service):
    """Test creating a backup of a non-existent file."""
    await file_service.start()
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service.create_backup("nonexistent")
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Config file not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_backup_error(file_service, tmp_path, test_data):
    """Test backup creation with error."""
    await file_service.start()
    
    # Create test config file
    _ = create_test_config(
        tmp_path / "config",
        "test_error",
        test_data
    )
    
    # Make backup directory read-only to cause error
    file_service._backup_dir.chmod(0o444)
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service.create_backup("test_error")
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to create backup" in str(exc_info.value.detail)
    
    # Restore permissions for cleanup
    file_service._backup_dir.chmod(0o777)


@pytest.mark.asyncio
async def test_load_config(file_service, tmp_path, test_data):
    """Test loading a config file."""
    await file_service.start()
    
    # Create test config file
    _ = create_test_config(
        tmp_path / "config",
        "test_load",
        test_data
    )
    
    # Load config
    config = await file_service.load_config("test_load")
    assert config.data == test_data


@pytest.mark.asyncio
async def test_load_config_missing(file_service):
    """Test loading a non-existent config file."""
    await file_service.start()
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service.load_config("nonexistent")
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Config file not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_load_invalid_yaml(file_service, tmp_path):
    """Test loading an invalid YAML file."""
    await file_service.start()
    
    # Create invalid config file
    config_path = tmp_path / "config" / "invalid.yaml"
    with open(config_path, "w") as f:
        f.write("invalid: yaml: content")
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service.load_config("invalid")
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid YAML format" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_save_config(file_service, tmp_path, test_data):
    """Test saving a config file."""
    await file_service.start()
    
    # Save config
    await file_service.save_config("test_save", test_data)
    
    # Verify saved data
    config_path = tmp_path / "config" / "test_save.yaml"
    assert config_path.exists()
    saved_data = load_yaml_file(config_path)
    assert saved_data == test_data


@pytest.mark.asyncio
async def test_save_config_error(file_service, tmp_path):
    """Test saving config with error."""
    await file_service.start()
    
    # Make config directory read-only to cause error
    file_service._config_dir.chmod(0o444)
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service.save_config("test_error", {"test": "data"})
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to save config" in str(exc_info.value.detail)
    
    # Restore permissions for cleanup
    file_service._config_dir.chmod(0o777)


@pytest.mark.asyncio
async def test_save_invalid_yaml(file_service):
    """Test saving invalid YAML data."""
    await file_service.start()
    
    # Create data that can't be serialized to YAML
    class UnserializableObject:
        pass
    
    invalid_data = {"test": UnserializableObject()}
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service.save_config("test_invalid", invalid_data)
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Failed to serialize config" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_save_config_with_backup(file_service, tmp_path, test_data):
    """Test saving a config file with backup creation."""
    await file_service.start()
    
    # Create initial file
    config_path = create_test_config(
        tmp_path / "config",
        "test_save",
        test_data
    )
    
    # Create updated data
    updated_data = {
        "test": {
            "key": "updated_value",
            "version": "2.0.0"
        }
    }
    
    # Save updated config
    await file_service.save_config("test_save", updated_data)
    
    # Verify backup was created
    backup_files = list(file_service._backup_dir.glob("test_save_*.bak"))
    assert len(backup_files) > 0
    
    # Verify backup contains original data
    backup_data = load_yaml_file(backup_files[0])
    assert backup_data == test_data
    
    # Verify config was updated
    saved_data = load_yaml_file(config_path)
    assert saved_data == updated_data
