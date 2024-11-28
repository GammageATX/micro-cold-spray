# tests/test_pattern_manager.py

"""Pattern Manager test suite.

Tests pattern management according to process.yaml:
- Pattern validation using process rules
- Pattern parameter validation
- Pattern preview generation
- Message pattern compliance
- Error handling

Pattern Types (from process.yaml):
- serpentine: Linear raster patterns
- spiral: Circular spiral patterns
- custom: Custom path patterns

Run with:
    pytest tests/test_pattern_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
import yaml
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager
from micro_cold_spray.core.exceptions import OperationError

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = {
        # Pattern topics from messaging.yaml
        "patterns/created": set(),
        "patterns/updated": set(),
        "patterns/deleted": set(),
        "patterns/error": set(),
        
        # Required topics
        "validation/request": set(),
        "validation/response": set(),
        "error": set()
    }
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance."""
    config = ConfigManager(message_broker)
    
    # Use in-memory configs only
    config._configs = {
        'process': {
            'patterns': {
                'types': {
                    'serpentine': {
                        'parameters': [
                            {'name': "length", 'type': "float"},
                            {'name': "spacing", 'type': "float"},
                            {'name': "direction", 'type': "string"}
                        ]
                    }
                }
            }
        },
        'hardware': {
            'motion': {
                'limits': {
                    'x': {'min': 0, 'max': 500},
                    'y': {'min': 0, 'max': 500}
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

@TestOrder.PROCESS
class TestPatternManager:
    """Pattern management tests run after parameter manager."""
    
    @pytest.mark.asyncio
    async def test_pattern_manager_initialization(self, pattern_manager):
        """Test pattern manager initialization."""
        assert pattern_manager._is_initialized
        process_config = pattern_manager._config_manager.get_config('process')
        assert 'patterns' in process_config['parameters']

@pytest.mark.asyncio
async def test_pattern_manager_create_serpentine(pattern_manager):
    """Test serpentine pattern creation using process.yaml definition."""
    pattern_data = {
        "type": "serpentine",
        "parameters": {
            "length": 10.0,
            "spacing": 1.0,
            "direction": "x_first",
            "speed": 20.0,  # From common_parameters
            "layers": 1     # From common_parameters
        }
    }
    
    result = await pattern_manager.create_pattern("test_pattern", pattern_data)
    assert result["valid"]
    assert len(result["errors"]) == 0

@pytest.mark.asyncio
async def test_pattern_manager_validate_limits(pattern_manager):
    """Test pattern validation against hardware limits."""
    # Test pattern exceeding sprayable area
    pattern_data = {
        "type": "serpentine",
        "parameters": {
            "length": 1000.0,  # Too large
            "spacing": 1.0,
            "direction": "x_first",
            "speed": 20.0,
            "layers": 1
        }
    }
    
    result = await pattern_manager.create_pattern("invalid_pattern", pattern_data)
    assert not result["valid"]
    assert "Pattern exceeds sprayable area" in str(result["errors"])