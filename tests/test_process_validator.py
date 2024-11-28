"""Process Validator test suite.

Tests validation of process parameters, patterns, and sequences.

Run with:
    pytest tests/test_process_validator.py -v --asyncio-mode=auto
"""

import pytest
import yaml
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from collections import defaultdict

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.exceptions import ValidationError

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a clean MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = defaultdict(set, {
        # Validation topics
        "validation/request": set(),
        "validation/result": set(),
        "validation/error": set(),
        
        # Config topics
        "config/update/*": set(),
        
        # Error topics
        "error": set()
    })
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
def config_manager(message_broker):
    # Load the actual configuration files
    with open('config/process.yaml', 'r') as f:
        process_config = yaml.safe_load(f)
    
    config_manager = ConfigManager(message_broker)
    config_manager._configs = {
        'process': process_config
    }
    return config_manager

@pytest.fixture
def process_validator(message_broker, config_manager):
    return ProcessValidator(message_broker, config_manager)

def test_process_validator_initialization(process_validator):
    assert process_validator is not None
    assert isinstance(process_validator, ProcessValidator)

@pytest.mark.asyncio
async def test_process_validator_validate_parameters(process_validator):
    parameters = {
        "motion": {
            "axis": "x",
            "distance": 10,
            "velocity": 5,
            "acceleration": 2,
            "deceleration": 2
        },
        "process": {
            "temperature": 300,
            "pressure": 50
        }
    }
    result = await process_validator.validate_parameters(parameters)
    assert result["valid"]
    assert len(result["errors"]) == 0

@pytest.mark.asyncio
async def test_process_validator_invalid_parameters(process_validator):
    parameters = {
        "motion": {
            "axis": "x",
            "distance": -1000,  # Invalid distance
            "velocity": 5000,   # Invalid velocity
            "acceleration": -10,  # Invalid acceleration
            "deceleration": -10   # Invalid deceleration
        }
    }
    result = await process_validator.validate_parameters(parameters)
    assert not result["valid"]
    assert len(result["errors"]) > 0

@pytest.mark.asyncio
async def test_process_validator_handle_request(
    process_validator: ProcessValidator,
    message_broker: MessageBroker
) -> None:
    """Test validation request handling."""
    # Track validation results
    results = []
    async def collect_results(data: Dict[str, Any]) -> None:
        results.append(data)
    await message_broker.subscribe("validation/result", collect_results)
    
    # Track errors
    errors = []
    async def collect_errors(data: Dict[str, Any]) -> None:
        errors.append(data)
    await message_broker.subscribe("error", collect_errors)
    
    # Test invalid parameters to trigger error
    await process_validator._handle_validation_request({
        "parameters": {"invalid": "params"},
        "request_id": "test_2"
    })
    await asyncio.sleep(0.1)
    
    assert len(errors) > 0
    assert "error" in errors[0]
    assert "timestamp" in errors[0]
    assert "context" in errors[0]  # Check for error context per rules