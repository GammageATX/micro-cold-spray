#pytest -v --asyncio-mode=auto

"""Common test fixtures and configuration."""
import pytest
import asyncio
from enum import IntEnum, auto
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock
import yaml
from pathlib import Path
from datetime import datetime

# Core infrastructure
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager

# Process components
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.process.data.data_manager import DataManager

# Operation components
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.components.operations.parameters.parameter_manager import ParameterManager
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager
from micro_cold_spray.core.components.operations.sequences.sequence_manager import SequenceManager

# UI components
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager

# Exceptions
from micro_cold_spray.core.exceptions import (
    ConfigurationError, StateError, ActionError, 
    TagOperationError, ValidationError
)

class TestOrder(IntEnum):
    """Test execution order."""
    INFRASTRUCTURE = 1
    PROCESS = 2
    UI = 3

def order(value: TestOrder):
    """Decorator to set test order."""
    def decorator(cls):
        cls.test_order = value
        return cls
    return decorator

def load_config(config_name: str) -> Dict[str, Any]:
    """Load config file without writing."""
    try:
        config_path = Path("config") / f"{config_name}.yaml"
        if not config_path.exists():
            pytest.skip(f"Config file {config_path} not found - check config path")
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        pytest.skip(f"Failed to load config {config_name}: {e}")

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[MagicMock, None]:
    """Provide mocked ConfigManager that uses real configs."""
    mock_config = MagicMock()
    
    # Load all real configs
    mock_config._configs = {
        'application': load_config('application'),
        'hardware': load_config('hardware'),
        'operation': load_config('operation'),
        'process': load_config('process'),
        'state': load_config('state'),
        'tags': load_config('tags')
    }
    
    # Configure mock to return configs directly
    async def get_config(name: str) -> Dict[str, Any]:
        return mock_config._configs.get(name, {})
    
    mock_config.get_config = AsyncMock(side_effect=get_config)
    mock_config.update_config = AsyncMock()
    mock_config.save_backup = AsyncMock()
    mock_config.shutdown = AsyncMock()
    
    mock_config._message_broker = message_broker
    
    try:
        yield mock_config
    finally:
        await mock_config.shutdown()

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide MessageBroker instance."""
    broker = MessageBroker()
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def process_validator(message_broker: MessageBroker, config_manager: ConfigManager) -> AsyncGenerator[ProcessValidator, None]:
    """Provide ProcessValidator instance."""
    validator = ProcessValidator(message_broker, config_manager)
    try:
        await validator.initialize()
        yield validator
    finally:
        await validator.shutdown()

@pytest.fixture
async def action_manager(message_broker: MessageBroker, config_manager: ConfigManager, process_validator: ProcessValidator) -> AsyncGenerator[ActionManager, None]:
    """Provide ActionManager instance."""
    manager = ActionManager(message_broker, config_manager, process_validator)
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture
async def ui_update_manager(message_broker: MessageBroker, config_manager: ConfigManager) -> AsyncGenerator[UIUpdateManager, None]:
    """Provide UIUpdateManager instance."""
    manager = UIUpdateManager(message_broker, config_manager)
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture
async def pattern_manager(message_broker: MessageBroker, config_manager: ConfigManager, process_validator: ProcessValidator) -> AsyncGenerator[PatternManager, None]:
    """Provide PatternManager instance."""
    manager = PatternManager(message_broker, config_manager, process_validator)
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()
  