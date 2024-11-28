"""Sequence Manager test suite.

Tests sequence management according to operation.yaml:
- Sequence validation using process rules
- Sequence execution and control
- Action orchestration
- Pattern application
- Parameter management

Sequence Rules (from operation.yaml):
- Must validate sequence steps
- Must follow state transitions
- Must handle async operations
- Must include timestamps

Message Patterns:
- Must use "sequence/load" for loading
- Must use "sequence/start" for starting
- Must use "sequence/stop" for stopping
- Must use "sequence/pause" for pausing
- Must use "sequence/resume" for resuming
- Must use "sequence/complete" for completion
- Must use "sequence/error" for errors

Run with:
    pytest tests/test_sequence_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.components.operations.sequences.sequence_manager import SequenceManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.exceptions import OperationError
from tests.conftest import TestOrder

@TestOrder.PROCESS
class TestSequenceManager:
    """Sequence management tests run after action manager."""
    
    @pytest.mark.asyncio
    async def test_sequence_manager_initialization(self, sequence_manager):
        """Test sequence manager initialization."""
        assert sequence_manager._is_initialized
        operation_config = sequence_manager._config_manager.get_config('operation')
        assert 'sequences' in operation_config

@pytest.mark.asyncio
async def test_sequence_manager_validate_sequence(sequence_manager):
    """Test sequence validation using operation.yaml rules."""
    # Create test sequence using real sequence structure
    sequence_data = {
        "metadata": {
            "name": "test_sequence",
            "description": "Test sequence"
        },
        "steps": [
            {
                "name": "prepare_system",  # From operation.yaml
                "hardware_set": "set1",
                "pattern": None,
                "parameters": {}
            },
            {
                "name": "move_to_trough",  # From operation.yaml
                "hardware_set": "set1",
                "pattern": None,
                "parameters": {}
            }
        ]
    }
    
    # Track validation responses
    responses = []
    async def collect_responses(data: Dict[str, Any]) -> None:
        responses.append(data)
    await sequence_manager._message_broker.subscribe(
        "validation/response",
        collect_responses
    )
    
    # Validate sequence
    await sequence_manager.validate_sequence(sequence_data)
    await asyncio.sleep(0.1)
    
    # Verify validation
    assert len(responses) > 0
    assert responses[0]["valid"]
    assert "timestamp" in responses[0]

@pytest.mark.asyncio
async def test_sequence_manager_execute_sequence(sequence_manager):
    """Test sequence execution."""
    # Create test sequence using real actions
    sequence_data = {
        "metadata": {
            "name": "test_sequence",
            "description": "Test sequence"
        },
        "steps": [
            {
                "name": "prepare_system",  # From operation.yaml
                "hardware_set": "set1",
                "pattern": None,
                "parameters": {}
            }
        ]
    }
    
    # Track sequence operations
    operations = []
    async def collect_operations(data: Dict[str, Any]) -> None:
        operations.append(data)
    
    await sequence_manager._message_broker.subscribe("action/execute", collect_operations)
    await sequence_manager._message_broker.subscribe("sequence/status", collect_operations)
    
    # Execute sequence
    await sequence_manager.execute_sequence(sequence_data)
    await asyncio.sleep(0.1)
    
    # Verify operation sequence
    assert len(operations) > 0
    assert any(op.get("type") == "prepare_system" for op in operations)
    assert all("timestamp" in op for op in operations)