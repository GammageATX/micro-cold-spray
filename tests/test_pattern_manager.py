# tests/test_pattern_manager.py

import pytest
from unittest.mock import MagicMock, AsyncMock
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    return ConfigManager(message_broker)

@pytest.fixture
def tag_manager(config_manager, message_broker):
    return TagManager(config_manager, message_broker)

@pytest.fixture
def process_validator(message_broker):
    return ProcessValidator(message_broker)

@pytest.fixture
def pattern_manager(config_manager, tag_manager, process_validator):
    return PatternManager(config_manager, tag_manager, process_validator)

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