"""Parameter Manager test suite.

Tests parameter management according to process.yaml:
- Parameter validation using process rules
- Parameter loading and saving
- Parameter application
- Message pattern compliance
- Error handling

Key Requirements:
- Must use MessageBroker for all communication
- Must validate against process.yaml rules
- Must handle async operations
- Must include timestamps

Run with:
    pytest tests/test_parameter_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
import yaml

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.operations.parameters.parameter_manager import ParameterManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator

@pytest.fixture
async def parameter_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator
) -> AsyncGenerator[ParameterManager, None]:
    """Provide a ParameterManager instance."""
    manager = ParameterManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.mark.asyncio
async def test_parameter_manager_load_parameters():
    """Test parameter loading with validation."""
    # Test loading parameters from process.yaml
    pass

@pytest.mark.asyncio
async def test_parameter_manager_save_parameters():
    """Test parameter saving."""
    # Test saving parameters with validation
    pass 