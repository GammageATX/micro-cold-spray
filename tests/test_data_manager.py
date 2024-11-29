"""Data Manager test suite.

Tests data management according to application.yaml paths:
- Run data collection
- Parameter history
- Pattern history
- Sequence history
- Data compression
- Auto backup

Data Paths (from application.yaml):
- data/runs/: Run data storage
- data/parameters/: Parameter storage
- data/patterns/: Pattern storage
- data/sequences/: Sequence storage

Run with:
    pytest tests/test_data_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from datetime import datetime
import os
from pathlib import Path
from tests.conftest import TestOrder, order
import json
import shutil

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.data.data_manager import DataManager

@pytest.fixture
async def data_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[DataManager, None]:
    """Provide a DataManager instance."""
    manager = DataManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@order(TestOrder.PROCESS)
class TestDataManager:
    """Data management tests run after process components."""
    
    @pytest.mark.asyncio
    async def test_data_manager_initialization(self, data_manager):
        """Test data manager initialization."""
        assert data_manager._is_initialized
        
        # Verify data paths from application config
        app_config = data_manager._config_manager.get_config('application')
        assert 'paths' in app_config
        assert 'data' in app_config['paths']
        
        # Verify directories exist
        assert data_manager._run_path.exists()
        assert data_manager._parameter_path.exists()
        assert data_manager._pattern_path.exists()
        assert data_manager._sequence_path.exists()
        
        # Verify subscription to tag updates
        assert any(
            "tag/update" in topic 
            for topic in data_manager._message_broker._subscribers.keys()
        )

    @pytest.mark.asyncio
    async def test_data_compression(self, data_manager, tmp_path):
        """Test data compression functionality."""
        # Use tmp_path instead of actual data directory
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        data_manager._run_path = test_dir
        
        # Create test run data
        run_id = "test_run"
        run_data = {
            "metadata": {
                "user": "test_user",
                "timestamp": datetime.now().isoformat()
            },
            "process_data": {
                "tag1": [
                    {"value": 1.0, "timestamp": "t1"},
                    {"value": 1.0, "timestamp": "t2"},  # Duplicate value
                    {"value": 2.0, "timestamp": "t3"}
                ]
            }
        }
        
        # Save test data
        run_path = test_dir / f"{run_id}.json"
        with open(run_path, 'w') as f:
            json.dump(run_data, f)
            
        # Track compression messages
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
        await data_manager._message_broker.subscribe(
            "data/compressed",
            collect_messages
        )
        
        # Compress data
        await data_manager.compress_data(run_id)
        await asyncio.sleep(0.1)
        
        # Verify compression
        compressed_path = test_dir / f"{run_id}_compressed.json"
        assert compressed_path.exists()
        
        # Cleanup test files
        run_path.unlink()
        compressed_path.unlink()

    @pytest.mark.asyncio
    async def test_data_backup(self, data_manager, tmp_path):
        """Test data backup functionality."""
        # Use tmp_path for both source and backup
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        data_manager._run_path = test_dir
        
        backup_dir = tmp_path / "backup"
        
        # Create test data in memory only
        test_data = {"test": "data"}
        
        # Track backup messages
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
        await data_manager._message_broker.subscribe(
            "data/backup/complete",
            collect_messages
        )
        
        # Create backup
        await data_manager.create_backup(backup_dir)
        await asyncio.sleep(0.1)
        
        # Verify backup message
        assert len(messages) > 0
        assert messages[0]["backup_path"] == str(backup_dir)

@pytest.mark.asyncio
async def test_data_manager_collect_run_data(data_manager):
    """Test run data collection."""
    # Mock file operations
    with patch('pathlib.Path.mkdir'), \
         patch('builtins.open', create=True):
        
        # Track data collection
        collections = []
        async def collect_data(data: Dict[str, Any]) -> None:
            collections.append(data)
        await data_manager._message_broker.subscribe(
            "process/status/data",
            collect_data
        )
        
        # Simulate process data
        await data_manager._message_broker.publish(
            "tag/update",
            {
                "tag": "chamber.pressure",
                "value": 2.5,
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)
        
        # Verify data collection
        assert len(collections) > 0
        assert "timestamp" in collections[0]
        assert collections[0]["data"]["chamber.pressure"] == 2.5

@pytest.mark.asyncio
async def test_data_manager_parameter_history(data_manager):
    """Test parameter history management."""
    # Mock file operations
    with patch('pathlib.Path.mkdir'), \
         patch('builtins.open', create=True):
        
        # Track parameter history
        history = []
        async def collect_history(data: Dict[str, Any]) -> None:
            history.append(data)
        await data_manager._message_broker.subscribe(
            "parameters/history",
            collect_history
        )
        
        # Save parameters
        parameters = {
            "gas": {
                "type": "helium",
                "main_flow": 50.0
            }
        }
        await data_manager.save_parameters("test_params", parameters)
        await asyncio.sleep(0.1)
        
        # Verify history update
        assert len(history) > 0
        assert "timestamp" in history[0]
        assert history[0]["name"] == "test_params"

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance."""
    config = ConfigManager(message_broker)
    
    # Use in-memory configs only
    config._configs = {
        'application': {
            'paths': {
                'data': {
                    'runs': 'data/runs',
                    'parameters': 'data/parameters',
                    'patterns': 'data/patterns',
                    'sequences': 'data/sequences'
                }
            }
        }
    }
    
    # Mock ALL file operations
    config._save_config = AsyncMock()
    config.update_config = AsyncMock()
    config._load_config = AsyncMock()
    config.save_backup = AsyncMock()
    
    try:
        yield config
    finally:
        # Clean shutdown without saving
        config.shutdown = AsyncMock()
        await config.shutdown()