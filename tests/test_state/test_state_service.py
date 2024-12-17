"""Tests for state management service."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from micro_cold_spray.api.state.service import StateService
from micro_cold_spray.api.state.models import (
    StateRequest,
    StateResponse
)
from micro_cold_spray.api.state.exceptions import (
    StateError,
    StateTransitionError,
    InvalidStateError,
    ConditionError
)


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    service.get_config = AsyncMock(return_value=Mock(data={
        "initial_state": "INIT",
        "transitions": {
            "INIT": {
                "next_states": ["READY"],
                "conditions": {
                    "hardware.connected": {
                        "tag": "hardware.connected",
                        "type": "equals",
                        "value": True
                    }
                },
                "description": "Initial state"
            },
            "READY": {
                "next_states": ["RUNNING", "ERROR"],
                "conditions": {
                    "hardware.enabled": {
                        "tag": "hardware.enabled",
                        "type": "equals",
                        "value": True
                    },
                    "hardware.safe": {
                        "tag": "hardware.safe",
                        "type": "equals",
                        "value": True
                    }
                },
                "description": "System ready"
            },
            "RUNNING": {
                "next_states": ["READY", "ERROR"],
                "conditions": {
                    "hardware.enabled": {
                        "tag": "hardware.enabled",
                        "type": "equals",
                        "value": True
                    },
                    "sequence.active": {
                        "tag": "sequence.active",
                        "type": "equals",
                        "value": True
                    }
                },
                "description": "System running"
            },
            "ERROR": {
                "next_states": ["INIT"],
                "conditions": {},
                "description": "Error state"
            }
        }
    }))
    return service


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    broker = AsyncMock()
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    
    async def mock_request(topic: str, data: dict) -> dict:
        if topic == "hardware/state":
            if data["query"] == "connection":
                return {"connected": True}
            elif data["query"] == "enabled":
                return {"enabled": True}
            elif data["query"] == "safety":
                return {"safe": True}
        elif topic == "sequence/state":
            return {"active": True}
        elif topic == "tag/request":
            return {"value": True}
        return {"value": True}
        
    broker.request = AsyncMock(side_effect=mock_request)
    return broker


@pytest.fixture
def mock_communication_service():
    """Create mock communication service."""
    service = AsyncMock()
    service.is_running = True
    return service


@pytest.fixture
async def state_service(mock_config_service, mock_message_broker, mock_communication_service):
    """Create state service instance."""
    service = StateService(
        config_service=mock_config_service,
        message_broker=mock_message_broker,
        communication_service=mock_communication_service
    )
    await service.start()
    yield service
    await service.stop()


class TestStateService:
    """Test state service functionality."""

    @pytest.mark.asyncio
    async def test_init_and_start(self, state_service):
        """Test service initialization and startup."""
        assert state_service.is_running
        assert state_service.current_state == "INIT"
        assert len(state_service._state_machine) == 4

    @pytest.mark.asyncio
    async def test_start_error(self, mock_config_service, mock_message_broker, mock_communication_service):
        """Test service startup error handling."""
        mock_config_service.get_config.side_effect = Exception("Config error")
        service = StateService(
            config_service=mock_config_service,
            message_broker=mock_message_broker,
            communication_service=mock_communication_service
        )
        with pytest.raises(StateError):
            await service.start()

    @pytest.mark.asyncio
    async def test_valid_transition(self, state_service, mock_message_broker):
        """Test valid state transition."""
        response = await state_service.transition_to(StateRequest(
            target_state="READY",
            reason="Test transition"
        ))
        assert response.success
        assert response.old_state == "INIT"
        assert response.new_state == "READY"

    @pytest.mark.asyncio
    async def test_invalid_transition(self, state_service):
        """Test invalid state transition."""
        with pytest.raises(StateTransitionError):
            await state_service.transition_to(StateRequest(
                target_state="RUNNING",
                reason="Invalid transition"
            ))

    @pytest.mark.asyncio
    async def test_invalid_state(self, state_service):
        """Test transition to invalid state."""
        with pytest.raises(InvalidStateError):
            await state_service.transition_to(StateRequest(
                target_state="INVALID",
                reason="Invalid state"
            ))

    @pytest.mark.asyncio
    async def test_force_transition(self, state_service, mock_message_broker):
        """Test forced state transition."""
        response = await state_service.transition_to(StateRequest(
            target_state="READY",
            reason="Forced transition",
            force=True
        ))
        assert response.success
        assert response.old_state == "INIT"
        assert response.new_state == "READY"

    @pytest.mark.asyncio
    async def test_condition_check(self, state_service, mock_message_broker):
        """Test condition checking."""
        conditions = await state_service.get_conditions("READY")
        assert isinstance(conditions, dict)
        assert "hardware.enabled" in conditions
        assert "hardware.safe" in conditions
        assert all(conditions.values()), "All conditions should be met"

    @pytest.mark.asyncio
    async def test_condition_error(self, state_service, mock_message_broker):
        """Test condition check error handling."""
        mock_message_broker.request.side_effect = Exception("Request failed")
        with pytest.raises(ConditionError):
            await state_service.transition_to(StateRequest(
                target_state="READY",
                reason="Test transition"
            ))

    @pytest.mark.asyncio
    async def test_state_history(self, state_service, mock_message_broker):
        """Test state history tracking."""
        await state_service.transition_to(StateRequest(
            target_state="READY",
            reason="Test transition",
            force=True
        ))
        
        history = state_service.get_state_history()
        assert len(history) > 0
        assert history[-1].old_state == "INIT"
        assert history[-1].new_state == "READY"

    @pytest.mark.asyncio
    async def test_valid_transitions(self, state_service):
        """Test getting valid transitions."""
        transitions = state_service.get_valid_transitions()
        assert isinstance(transitions, dict)
        assert transitions["INIT"] == ["READY"]
        assert set(transitions["READY"]) == {"RUNNING", "ERROR"}

    @pytest.mark.asyncio
    async def test_health_check(self, state_service):
        """Test service health check."""
        health = await state_service.check_health()
        assert isinstance(health, dict)
        assert "status" in health
        assert "dependencies" in health
        assert "details" in health

    @pytest.mark.asyncio
    async def test_service_info(self, state_service):
        """Test service info retrieval."""
        info = state_service.service_info
        assert isinstance(info, dict)
        assert info["name"] == "state"
        assert info["running"] is True
        assert "current_state" in info
        assert "states_configured" in info

    @pytest.mark.asyncio
    async def test_message_handling(self, state_service, mock_message_broker):
        """Test message broker request handling."""
        await state_service._handle_state_request({
            "state": "READY",
            "reason": "Test request",
            "force": True
        })
        assert state_service.current_state == "READY"

    @pytest.mark.asyncio
    async def test_check_conditions(self, state_service, mock_message_broker):
        """Test checking conditions for a state."""
        conditions = await state_service.check_conditions("READY")
        assert isinstance(conditions, dict)
        assert all(conditions.values()), "All conditions should be met"

    @pytest.mark.asyncio
    async def test_history_limit(self, state_service):
        """Test history size limiting."""
        # Add more entries than the limit
        for i in range(StateService.MAX_HISTORY_SIZE + 10):
            state_service._add_history_entry(
                StateResponse(
                    success=True,
                    old_state="INIT",
                    new_state="READY",
                    timestamp=datetime.now()
                )
            )
            
        history = state_service.get_state_history()
        assert len(history) <= StateService.MAX_HISTORY_SIZE
