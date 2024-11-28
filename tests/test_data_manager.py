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
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
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

@TestOrder.PROCESS
class TestDataManager:
    """Data management tests run after process components."""
    
    @pytest.mark.asyncio
    async def test_data_manager_initialization(self, data_manager):
        """Test data manager initialization."""
        assert data_manager._is_initialized
        app_config = data_manager._config_manager.get_config('application')
        assert 'paths' in app_config
        assert 'data' in app_config['paths']

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