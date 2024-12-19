"""Tests for file service."""

import pytest
from pathlib import Path
import yaml
import shutil

from micro_cold_spray.api.config.services.config_file_service import ConfigFileService
from micro_cold_spray.api.base.base_exceptions import ConfigError


@pytest.fixture
def file_service(tmp_path):
    """Create a file service instance for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    
    # Copy real config file for testing from root config directory
    real_config = Path("config/application.yaml")
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
async def test_create_backup(file_service, tmp_path):
    """Test creating a backup of a config file."""
    # Create test config file
    config_path = tmp_path / "config" / "test_backup_create.yaml"
    test_data = {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_data, f)
    
    # Create backup
    backup_path = await file_service.create_backup(config_path)
    
    # Verify backup was created
    assert backup_path.exists()
    with open(backup_path) as f:
        backup_data = yaml.load(f, Loader=yaml.Loader)
        assert backup_data == test_data


@pytest.mark.asyncio
async def test_create_backup_with_existing_backup(file_service, tmp_path):
    """Test creating a backup when one already exists."""
    # Create test config file
    config_path = tmp_path / "config" / "test_backup.yaml"
    test_data = {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_data, f)
    
    # Create first backup
    backup_path1 = await file_service.create_backup(config_path)
    assert backup_path1.exists()
    
    # Create second backup
    backup_path2 = await file_service.create_backup(config_path)
    assert backup_path2.exists()
    assert backup_path1 != backup_path2


@pytest.mark.asyncio
async def test_exists(file_service, tmp_path):
    """Test checking if a config file exists."""
    # Create test config file
    config_path = tmp_path / "config" / "test_exists.yaml"
    test_data = {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_data, f)
    
    # Check existence
    assert await file_service.exists(config_path.name)
    assert not await file_service.exists("nonexistent.yaml")


@pytest.mark.asyncio
async def test_load_config(file_service, tmp_path):
    """Test loading a config file."""
    # Create test config file
    config_path = tmp_path / "config" / "test_load.yaml"
    test_data = {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_data, f)
    
    # Load config
    config = await file_service.load_config(config_path.name)
    assert config == test_data


@pytest.mark.asyncio
async def test_load_invalid_config(file_service, tmp_path):
    """Test loading an invalid config file."""
    # Create invalid config file
    invalid_config = tmp_path / "config" / "invalid_test.yaml"
    invalid_config.parent.mkdir(exist_ok=True)
    with open(invalid_config, "w") as f:
        f.write("invalid: yaml: content")
    
    # Attempt to load invalid config
    with pytest.raises(ConfigError):
        await file_service.load_config(invalid_config.name)


@pytest.mark.asyncio
async def test_save_config(file_service, tmp_path):
    """Test saving a config file."""
    config_path = tmp_path / "config" / "test_save.yaml"
    test_data = {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }
    
    # Save config
    await file_service.save_config(config_path.name, test_data)
    
    # Verify saved data
    assert config_path.exists()
    with open(config_path) as f:
        saved_data = yaml.load(f, Loader=yaml.Loader)
        assert saved_data == test_data


@pytest.mark.asyncio
async def test_save_config_with_backup(file_service, tmp_path):
    """Test saving a config file with backup creation."""
    config_path = tmp_path / "config" / "test_save.yaml"
    test_data = {
        "test": {
            "key": "value",
            "version": "1.0.0"
        }
    }
    
    # Create initial file
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump({"original": "data"}, f)
    
    # Save new config
    await file_service.save_config(config_path.name, test_data)
    
    # Verify backup was created
    backup_files = list(file_service._backup_dir.glob("test_save_*.bak"))
    assert len(backup_files) == 1
    
    # Verify saved data
    with open(config_path) as f:
        saved_data = yaml.load(f, Loader=yaml.Loader)
        assert saved_data == test_data
