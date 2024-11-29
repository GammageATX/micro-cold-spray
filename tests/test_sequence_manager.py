"""Sequence Manager test suite.

Tests sequence management according to process.yaml:
- Sequence validation using process rules
- Sequence execution and control
- Action orchestration
- Pattern application
- Parameter management

Sequence Rules (from process.yaml):
- Must validate sequence steps
- Must follow state transitions
- Must handle async operations
- Must include timestamps

Message Patterns:
- Must use "sequence/load" for loading
- Must use "sequence/start" for starting
- Must use "sequence/complete" for completion
- Must use "sequence/error" for errors

Run with:
    pytest tests/test_sequence_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime
from pathlib import Path
import yaml
from tests.conftest import TestOrder, order

@pytest.fixture
async def sequence_manager(
    message_broker,
    config_manager,
    process_validator,
    action_manager
):
    """Provide SequenceManager instance."""
    from micro_cold_spray.core.components.operations.sequences.sequence_manager import SequenceManager
    
    manager = SequenceManager(
        message_broker=message_broker,
        config_manager=config_manager,
        sequence_path=Path("data/sequences/library")
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@order(TestOrder.PROCESS)
class TestSequenceManager:
    """Sequence management tests."""
    
    @pytest.mark.asyncio
    async def test_load_sequence(self, sequence_manager, tmp_path):
        """Test sequence loading and validation."""
        # Create test sequence file
        sequence_data = {
            "sequence": {
                "metadata": {
                    "name": "test_sequence",
                    "description": "Test sequence"
                },
                "steps": [
                    {
                        "name": "prepare_system",
                        "hardware_set": "set1",
                        "pattern": None,
                        "parameters": {}
                    },
                    {
                        "name": "move_to_trough",
                        "hardware_set": "set1",
                        "pattern": None,
                        "parameters": {}
                    }
                ]
            }
        }
        
        sequence_file = tmp_path / "test_sequence.yaml"
        with open(sequence_file, 'w') as f:
            yaml.safe_dump(sequence_data, f)
            
        # Track sequence messages
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
        await sequence_manager._message_broker.subscribe(
            "sequence/loaded",
            collect_messages
        )
        await asyncio.sleep(0.1)  # Wait for subscription
        
        # Load sequence
        loaded_sequence = await sequence_manager.load_sequence(str(sequence_file))
        await asyncio.sleep(0.1)  # Wait for message
        
        # Verify sequence structure and messages
        assert loaded_sequence == sequence_data
        assert len(messages) > 0
        assert "sequence" in messages[0]
        assert "timestamp" in messages[0]

    @pytest.mark.asyncio
    async def test_execute_sequence(self, sequence_manager):
        """Test sequence execution with state transitions."""
        # Create test sequence
        sequence_data = {
            "sequence": {
                "metadata": {
                    "name": "test_sequence",
                    "description": "Test sequence"
                },
                "steps": [
                    {
                        "name": "ready_system",
                        "hardware_set": "set1",
                        "pattern": None,
                        "parameters": {}
                    }
                ]
            }
        }
        
        # Track sequence operations
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        
        await sequence_manager._message_broker.subscribe(
            "action/execute",
            collect_operations
        )
        await sequence_manager._message_broker.subscribe(
            "sequence/status",
            collect_operations
        )
        
        # Execute sequence
        await sequence_manager.execute_sequence(sequence_data)
        await asyncio.sleep(0.1)
        
        # Verify operation sequence
        assert len(operations) > 0
        assert any(op.get("type") == "ready_system" for op in operations)
        assert all("timestamp" in op for op in operations)

    @pytest.mark.asyncio
    async def test_sequence_state_control(self, sequence_manager):
        """Test sequence state control operations."""
        # Create test sequence with multiple steps to ensure it runs long enough
        sequence_data = {
            "sequence": {
                "metadata": {
                    "name": "test_sequence",
                    "description": "Test sequence"
                },
                "steps": [
                    {
                        "name": "ready_system",
                        "hardware_set": "set1",
                        "pattern": None,
                        "parameters": {}
                    },
                    {
                        "name": "ready_system",  # Add second step to make sequence longer
                        "hardware_set": "set1",
                        "pattern": None,
                        "parameters": {}
                    }
                ]
            }
        }
        
        # Track state changes
        states = []
        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)
            
        await sequence_manager._message_broker.subscribe(
            "sequence/status",
            collect_states
        )
        await asyncio.sleep(0.1)  # Wait for subscription
        
        # Execute sequence control operations
        sequence_manager._is_running = True  # Set running state
        sequence_task = asyncio.create_task(sequence_manager.execute_sequence(sequence_data))
        await asyncio.sleep(0.2)  # Wait for sequence to start
        
        await sequence_manager.pause_sequence()
        await asyncio.sleep(0.1)  # Wait for pause
        
        await sequence_manager.resume_sequence()
        await asyncio.sleep(0.1)  # Wait for resume
        
        await sequence_manager.stop_sequence()
        await asyncio.sleep(0.1)  # Wait for stop
        
        await sequence_task  # Wait for sequence to complete
        
        # Verify state transitions
        assert len(states) >= 4
        state_sequence = [s.get("state") for s in states]
        assert "RUNNING" in state_sequence
        assert "PAUSED" in state_sequence
        assert "STOPPED" in state_sequence

    @pytest.mark.asyncio
    async def test_sequence_visualization(self, sequence_manager):
        """Test sequence visualization data generation."""
        # Create test sequence with pattern
        sequence_data = {
            "sequence": {
                "metadata": {
                    "name": "test_sequence",
                    "description": "Test sequence"
                },
                "steps": [
                    {
                        "name": "execute_pattern",
                        "hardware_set": "set1",
                        "pattern": {
                            "type": "serpentine",
                            "file": "test_pattern.yaml",
                            "parameters": {
                                "origin": [100.0, 100.0],
                                "passes": 1
                            }
                        }
                    }
                ]
            }
        }
        
        # Generate visualization data
        viz_data = sequence_manager._generate_visualization_data(sequence_data)
        
        # Verify visualization structure
        assert len(viz_data) > 0
        assert "type" in viz_data[0]
        assert "origin" in viz_data[0]
        assert "pattern_file" in viz_data[0]

    @pytest.mark.asyncio
    async def test_sequence_error_handling(self, sequence_manager):
        """Test sequence error handling."""
        # Create invalid sequence
        sequence_data = {
            "sequence": {
                "metadata": {
                    "name": "test_sequence",
                    "description": "Test sequence"
                },
                "steps": [
                    {
                        "name": "invalid_action",
                        "hardware_set": "set1",
                        "pattern": None,
                        "parameters": {}
                    }
                ]
            }
        }
        
        # Track error messages
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
            
        await sequence_manager._message_broker.subscribe(
            "sequence/error",
            collect_errors
        )
        await asyncio.sleep(0.1)  # Wait for subscription
        
        # Execute invalid sequence
        with pytest.raises(Exception):
            await sequence_manager.execute_sequence(sequence_data)
        await asyncio.sleep(0.1)  # Wait for error message
        
        # Verify error handling
        assert len(errors) > 0
        assert "error" in errors[0]
        assert "timestamp" in errors[0]