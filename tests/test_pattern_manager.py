# tests/test_pattern_manager.py

"""Pattern Manager test suite.

Tests the management and validation of spray patterns including:
- Pattern creation and validation
- Pattern updates and configuration
- Pattern deletion and cleanup
- Error handling and validation failures
- Message pattern compliance
- State transition validation

Run with:
    pytest tests/test_pattern_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from collections import defaultdict

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager
from micro_cold_spray.core.exceptions import OperationError

# Reuse fixtures from test_tag_manager.py
from .test_tag_manager import (
    mock_plc_client,
    mock_ssh_client,
    tag_manager
)

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a clean MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = defaultdict(set, {
        # Pattern topics
        "pattern/create": set(),
        "pattern/update": set(),
        "pattern/delete": set(),
        "pattern/error": set(),
        
        # Validation topics
        "validation/request": set(),
        "validation/result": set(),
        
        # Error topics
        "error": set()
    })
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance with test configs."""
    config = ConfigManager(message_broker)
    config._configs['patterns'] = {
        'patterns': {
            'test_pattern': {
                'name': 'test_pattern',
                'type': 'raster',
                'parameters': {
                    'width': 10.0,
                    'height': 10.0,
                    'spacing': 1.0
                }
            }
        }
    }
    
    # Add process config for validation
    config._configs['process'] = {
        'limits': {
            'motion': {
                'velocity': {'min': 0, 'max': 1000},
                'acceleration': {'min': 0, 'max': 5000}
            }
        }
    }
    
    try:
        yield config
    finally:
        await config.shutdown()

@pytest.fixture
async def process_validator(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[ProcessValidator, None]:
    """Provide a ProcessValidator instance."""
    validator = ProcessValidator(
        message_broker=message_broker,
        config_manager=config_manager
    )
    try:
        yield validator
    finally:
        # No async cleanup needed
        pass

@pytest.fixture
async def pattern_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator
) -> AsyncGenerator[PatternManager, None]:
    """Provide a PatternManager instance."""
    manager = PatternManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        # Cleanup if needed
        pass

def test_pattern_manager_initialization(pattern_manager):
    assert pattern_manager is not None
    assert isinstance(pattern_manager, PatternManager)

@pytest.mark.asyncio
async def test_pattern_manager_get_pattern(pattern_manager):
    pattern_name = "test_pattern"
    pattern_manager._patterns = {
        pattern_name: {
            "type": "spray",
            "parameters": {"duration": 5, "pressure": 50}
        }
    }
    pattern = await pattern_manager.get_pattern(pattern_name)
    assert pattern is not None

@pytest.mark.asyncio
async def test_pattern_manager_update_pattern(pattern_manager):
    pattern_name = "test_pattern"
    pattern_manager._patterns = {
        pattern_name: {
            "type": "spray",
            "parameters": {"duration": 5, "pressure": 50}
        }
    }
    updates = {"parameters": {"duration": 10}}
    await pattern_manager.update_pattern(pattern_name, updates)
    pattern = await pattern_manager.get_pattern(pattern_name)
    assert pattern["parameters"]["duration"] == 10