"""State Manager test suite.

Tests state management according to state.yaml:
- State transitions
- State validation
- State error handling
- Message pattern compliance

Run with:
    pytest tests/test_state_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
from datetime import datetime
import asyncio

from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.exceptions import StateError
from tests.conftest import TestOrder, order

@order(TestOrder.INFRASTRUCTURE)
class TestStateManager:
    """State Manager tests run with infrastructure."""
    
    @pytest.mark.asyncio
    async def test_state_manager_initialization(self, state_manager):
        """Test state manager initialization."""
        # Should start in INITIALIZING state
        assert await state_manager.get_current_state() == "INITIALIZING"
        assert await state_manager.get_previous_state() == ""
        
        # Track state changes
        changes = []
        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)
        await state_manager._message_broker.subscribe("state/change", collect_changes)
        
        # Set initial conditions
        state_manager._conditions = {
            "hardware.connected": False,
            "config.loaded": True,
            "hardware.enabled": False,
            "sequence.active": False
        }
        
        # Update hardware.connected condition via tag update
        await state_manager._handle_tag_update({
            "tag": "hardware.connected",
            "value": True,
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.1)  # Wait for state transition
        
        # Should transition to READY
        current_state = await state_manager.get_current_state()
        assert current_state == "READY", f"Expected READY state but got {current_state}"
        assert len(changes) == 1
        assert changes[0]["state"] == "READY"
        assert changes[0]["previous"] == "INITIALIZING"
        assert "timestamp" in changes[0]
    
    @pytest.mark.asyncio
    async def test_state_manager_external_request(self, state_manager):
        """Test state change from external request."""
        # Track state changes
        changes = []
        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)
        await state_manager._message_broker.subscribe("state/change", collect_changes)
        
        # Set conditions for READY -> RUNNING transition
        state_manager._current_state = "READY"
        state_manager._conditions = {
            "hardware.connected": True,
            "config.loaded": True,
            "hardware.enabled": True,
            "sequence.active": True
        }
        
        # Request state change via message broker
        await state_manager._message_broker.publish(
            "state/request",
            {
                "state": "RUNNING",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await asyncio.sleep(0.1)
        
        # Verify transition
        assert await state_manager.get_current_state() == "RUNNING"
        assert len(changes) == 1
        assert changes[0]["state"] == "RUNNING"
        assert changes[0]["previous"] == "READY"
    
    @pytest.mark.asyncio
    async def test_state_manager_condition_change(self, state_manager):
        """Test state transition from condition change."""
        # Track state changes
        changes = []
        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)
        await state_manager._message_broker.subscribe("state/change", collect_changes)
        
        # Set initial state and conditions
        state_manager._current_state = "INITIALIZING"
        state_manager._conditions = {
            "hardware.connected": False,
            "config.loaded": True,
            "hardware.enabled": False,
            "sequence.active": False
        }
        
        # Update condition via tag update
        await state_manager._handle_tag_update({
            "tag": "hardware.connected",
            "value": True,
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.1)
        
        # Verify transition
        assert await state_manager.get_current_state() == "READY"
        assert len(changes) == 1
        assert changes[0]["state"] == "READY"
        assert changes[0]["previous"] == "INITIALIZING"
    
    @pytest.mark.asyncio
    async def test_state_manager_invalid_transition(self, state_manager):
        """Test invalid state transition."""
        # Track error messages
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
        await state_manager._message_broker.subscribe("error", collect_errors)
        
        # Try invalid direct state change
        with pytest.raises(StateError):
            await state_manager.set_state("INVALID_STATE")
        
        # Wait for error message to be published and collected
        await asyncio.sleep(0.1)
        
        # Verify error message
        assert len(errors) == 1
        assert "Invalid state transition" in str(errors[0]["error"])
        assert errors[0]["context"] == "state transition"
        assert errors[0]["topic"] == "state/transition"

@pytest.fixture
async def state_manager(message_broker, config_manager):
    """Create state manager with mocked dependencies."""
    # Mock state config
    state_config = {
        "transitions": {
            "INITIALIZING": {
                "conditions": ["hardware.connected", "config.loaded"],
                "next_states": ["READY"]
            },
            "READY": {
                "conditions": ["hardware.connected", "hardware.enabled"],
                "next_states": ["RUNNING", "SHUTDOWN"]
            },
            "RUNNING": {
                "conditions": ["hardware.connected", "hardware.enabled", "sequence.active"],
                "next_states": ["READY", "ERROR"]
            },
            "ERROR": {
                "next_states": ["READY", "SHUTDOWN"]
            },
            "SHUTDOWN": {
                "conditions": ["hardware.safe"],
                "next_states": ["INITIALIZING"]
            }
        }
    }
    
    # Configure mock
    config_manager.get_config.return_value = state_config
    
    # Create state manager
    manager = StateManager(message_broker, config_manager)
    await manager.initialize()
    
    yield manager
    
    # Cleanup
    await manager.shutdown()