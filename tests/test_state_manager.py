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
from typing import Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
from collections import defaultdict

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
        await asyncio.sleep(0.1)  # Wait for subscription
        
        # Ensure conditions are set correctly
        state_manager._conditions = {
            "hardware.connected": False,
            "config.loaded": True,
            "hardware.enabled": False,
            "sequence.active": False
        }
        
        # Send hardware ready signals
        await state_manager._message_broker.publish(
            "hardware/status/plc",
            {
                "connected": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)  # Wait for first status
        
        await state_manager._message_broker.publish(
            "hardware/status/motion",
            {
                "connected": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.3)  # Wait longer for state transition
        
        # Should transition to READY
        current_state = await state_manager.get_current_state()
        assert current_state == "READY", f"Expected READY state but got {current_state}"
        assert len(changes) >= 1
        assert changes[-1]["state"] == "READY"
        assert "timestamp" in changes[-1]
    
    @pytest.mark.asyncio
    async def test_state_manager_valid_transition(self, state_manager):
        """Test valid state transition from state.yaml."""
        # Track state changes
        changes = []
        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)
        await state_manager._message_broker.subscribe("state/change", collect_changes)
        
        # Reset to INITIALIZING
        state_manager._current_state = "INITIALIZING"
        state_manager._conditions = {
            "hardware.connected": False,
            "config.loaded": True,
            "hardware.enabled": False,
            "sequence.active": False
        }
        
        # Send hardware ready signals
        await state_manager._message_broker.publish(
            "hardware/status/plc",
            {
                "connected": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        await state_manager._message_broker.publish(
            "hardware/status/motion",
            {
                "connected": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Wait for state transition to complete
        await asyncio.sleep(0.2)  # Increased sleep time
        
        # Verify transition to READY
        current_state = await state_manager.get_current_state()
        assert current_state == "READY", f"Expected READY state but got {current_state}"
        assert len(changes) >= 1
        assert changes[-1]["state"] == "READY"
        assert "timestamp" in changes[-1]
    
    @pytest.mark.asyncio
    async def test_state_manager_invalid_transition(self, state_manager):
        """Test invalid state transition."""
        # Track error messages
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
        await state_manager._message_broker.subscribe("error", collect_errors)
        
        # Reset to INITIALIZING
        state_manager._current_state = "INITIALIZING"
        state_manager._hardware_ready = False
        state_manager._motion_ready = False
        
        # Try invalid transition
        await state_manager._message_broker.publish(
            "state/request",
            {
                "requested_state": "SHUTDOWN",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)
        
        # Verify error message
        assert len(errors) > 0
        assert "Invalid state transition" in str(errors[0]["error"])
        assert "timestamp" in errors[0]
        assert errors[0]["topic"] == "state/transition"