"""Tests for config file service."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
import copy
import os
import shutil

from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.config.services.file_service import ConfigFileService
from .helpers import (
    load_test_config,
    load_yaml_file,
    create_test_config_data
)

TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_BACKUP_DIR = TEST_DATA_DIR / "backups"


def clean_backup_dir():
    """Clean up old backup files."""
    if TEST_BACKUP_DIR.exists():
        shutil.rmtree(TEST_BACKUP_DIR)
    TEST_BACKUP_DIR.mkdir(exist_ok=True)


@pytest.fixture(autouse=True)
def setup_backup_dir():
    """Setup and cleanup backup directory before each test."""
    clean_backup_dir()
    yield
    # Leave backups after tests for inspection


@pytest.fixture
def config_dir():
    """Use test data directory for configs."""
    return TEST_DATA_DIR


@pytest.fixture
def file_service(config_dir):
    """Create file service instance."""
    service = ConfigFileService(config_dir)
    service._backup_dir = TEST_BACKUP_DIR  # Ensure backup directory is set correctly
    return service


@pytest.mark.asyncio
async def test_create_backup(file_service):
    """Test creating config backup."""
    await file_service.start()
    
    # Create test config
    config_data = create_test_config_data("test_backup_create")
    
    try:
        await file_service.save_config(config_data)
        await file_service.create_backup("test_backup_create")
        
        # Verify backup was created
        backup_files = list(TEST_BACKUP_DIR.glob("test_backup_create_*.bak"))
        assert len(backup_files) > 0
        
        # Verify backup content
        backup_data = load_yaml_file(backup_files[-1])
        # Unwrap the backup data
        unwrapped_backup_data = backup_data.get(config_data.metadata.config_type, backup_data)
        assert unwrapped_backup_data == config_data.data
        
    finally:
        # Clean up test file but leave backup for inspection
        config_path = TEST_DATA_DIR / "test_backup_create.yaml"
        if config_path.exists():
            os.remove(config_path)


@pytest.mark.asyncio
async def test_save_config_with_backup(file_service):
    """Test saving configuration with backup."""
    await file_service.start()
    
    # Create and save initial config
    initial_data = load_test_config("test_config")
    config_data = create_test_config_data("test_backup", initial_data)
    
    try:
        # Save initial config
        await file_service.save_config(config_data)
        
        # Update config with deep copy
        updated_data = copy.deepcopy(initial_data)
        updated_data["application"]["info"]["version"] = "2.0.0"
        updated_config = create_test_config_data("test_backup", updated_data)
        
        # Save updated config
        await file_service.save_config(updated_config)
        
        # Verify backup was created
        backup_files = list(TEST_BACKUP_DIR.glob("test_backup_*.bak"))
        assert len(backup_files) > 0
        
        # Verify backup content matches original
        backup_data = load_yaml_file(backup_files[-1])
        # Unwrap the backup data
        unwrapped_backup_data = backup_data.get(config_data.metadata.config_type, backup_data)
        assert unwrapped_backup_data == initial_data
        
    finally:
        # Clean up test files but leave backups for inspection
        config_path = TEST_DATA_DIR / "test_backup.yaml"
        if config_path.exists():
            os.remove(config_path)


@pytest.mark.asyncio
async def test_config_exists(file_service):
    """Test checking config existence."""
    await file_service.start()
    
    assert await file_service.config_exists("test_config")
    assert not await file_service.config_exists("nonexistent")
    
    # Check backup existence after creating one
    config_data = create_test_config_data("test_exists")
    try:
        await file_service.save_config(config_data)
        await file_service.create_backup("test_exists")
        
        # Verify backup was created
        backup_files = list(TEST_BACKUP_DIR.glob("test_exists_*.bak"))
        assert len(backup_files) > 0
    finally:
        config_path = TEST_DATA_DIR / "test_exists.yaml"
        if config_path.exists():
            os.remove(config_path)


@pytest.mark.asyncio
async def test_create_backup_missing_config(file_service):
    """Test creating backup for non-existent config."""
    await file_service.start()
    
    with pytest.raises(ConfigurationError, match="Config file not found"):
        await file_service.create_backup("nonexistent")


@pytest.mark.asyncio
async def test_service_start(file_service):
    """Test service startup."""
    await file_service.start()
    assert file_service.is_running
    assert file_service._config_dir.exists()
    assert file_service._backup_dir.exists()


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
async def test_load_config_invalid_yaml(file_service):
    """Test loading invalid YAML config."""
    await file_service.start()
    
    invalid_config = TEST_DATA_DIR / "invalid_test.yaml"
    invalid_config.write_text("invalid: yaml: content: {")
    
    try:
        with pytest.raises(ConfigurationError, match="Failed to load config"):
            await file_service.load_config("invalid_test")
    finally:
        # Clean up test file
        if invalid_config.exists():
            os.remove(invalid_config)


@pytest.mark.asyncio
async def test_load_config_success(file_service):
    """Test loading valid config."""
    await file_service.start()
    
    config_data = await file_service.load_config("test_config")
    assert config_data.metadata.config_type == "test_config"
    
    # Load expected data for comparison
    test_config = load_test_config("test_config")
    assert config_data.data == test_config


@pytest.mark.asyncio
async def test_save_config(file_service):
    """Test saving configuration."""
    await file_service.start()
    
    # Create test config data
    config_data = create_test_config_data("test_save")
    
    try:
        await file_service.save_config(config_data)
        config_path = TEST_DATA_DIR / "test_save.yaml"
        assert config_path.exists()

        # Verify content - Update this line to expect wrapped data
        saved_data = load_yaml_file(config_path)
        # The data is wrapped in config_type, so we need to unwrap it
        assert saved_data[config_data.metadata.config_type] == config_data.data
    finally:
        # Clean up test file
        config_path = TEST_DATA_DIR / "test_save.yaml"
        if config_path.exists():
            os.remove(config_path)
