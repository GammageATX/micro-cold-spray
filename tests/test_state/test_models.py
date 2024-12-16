"""Tests for state management models."""

from datetime import datetime
from micro_cold_spray.api.state.models import (
    StateCondition,
    StateConfig,
    StateTransition,
    StateRequest,
    StateResponse
)


class TestStateModels:
    """Test state management model classes."""

    def test_state_condition(self):
        """Test StateCondition model."""
        condition = StateCondition(
            tag="test.tag",
            type="equals",
            value=True,
            min_value=0,
            max_value=100
        )
        assert condition.tag == "test.tag"
        assert condition.type == "equals"
        assert condition.value is True
        assert condition.min_value == 0
        assert condition.max_value == 100

        # Test optional fields
        condition = StateCondition(tag="test", type="equals", value=True)
        assert condition.min_value is None
        assert condition.max_value is None

    def test_state_config(self):
        """Test StateConfig model."""
        config = StateConfig(
            name="TEST",
            valid_transitions=["READY", "ERROR"],
            conditions={"connected": StateCondition(tag="hw.connected", type="equals", value=True)},
            description="Test state"
        )
        assert config.name == "TEST"
        assert "READY" in config.valid_transitions
        assert "ERROR" in config.valid_transitions
        assert "connected" in config.conditions
        assert config.description == "Test state"

        # Test optional description
        config = StateConfig(
            name="TEST",
            valid_transitions=[],
            conditions={}
        )
        assert config.description is None

    def test_state_transition(self):
        """Test StateTransition model."""
        timestamp = datetime.now()
        transition = StateTransition(
            old_state="INIT",
            new_state="READY",
            timestamp=timestamp,
            reason="Test transition",
            conditions_met={"hardware.connected": True}
        )
        assert transition.old_state == "INIT"
        assert transition.new_state == "READY"
        assert transition.timestamp == timestamp
        assert transition.reason == "Test transition"
        assert transition.conditions_met["hardware.connected"] is True

    def test_state_request(self):
        """Test StateRequest model."""
        request = StateRequest(
            target_state="READY",
            reason="Test transition",
            force=True
        )
        assert request.target_state == "READY"
        assert request.reason == "Test transition"
        assert request.force is True

        # Test optional fields
        request = StateRequest(target_state="READY")
        assert request.reason is None
        assert request.force is False

    def test_state_response(self):
        """Test StateResponse model."""
        timestamp = datetime.now()
        response = StateResponse(
            success=True,
            old_state="INIT",
            new_state="READY",
            error=None,
            failed_conditions=None,
            timestamp=timestamp
        )
        assert response.success is True
        assert response.old_state == "INIT"
        assert response.new_state == "READY"
        assert response.error is None
        assert response.failed_conditions is None
        assert response.timestamp == timestamp

        # Test error response
        response = StateResponse(
            success=False,
            old_state="INIT",
            new_state=None,
            error="Transition failed",
            failed_conditions=["hardware.connected"],
            timestamp=timestamp
        )
        assert response.success is False
        assert response.old_state == "INIT"
        assert response.new_state is None
        assert response.error == "Transition failed"
        assert "hardware.connected" in response.failed_conditions
        assert response.timestamp == timestamp
